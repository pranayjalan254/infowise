#!/usr/bin/env python3
"""
Test script to verify the enhanced PII workflow:
1. Detection with enhanced detector
2. Strategy configuration
3. Masking with pre-configured strategies
"""

import tempfile
import os
from enhanced_pii_detector import EnhancedPIIDetector
from enhanced_pii_masker import EnhancedPIIMasker, MaskingConfig


def create_test_pdf(text_content: str) -> str:
    """Create a test PDF with the given text content."""
    try:
        import fitz
        
        # Create a temporary PDF
        temp_pdf = tempfile.mktemp(suffix='.pdf')
        doc = fitz.open()  # Create new PDF
        page = doc.new_page()
        
        # Add text to the page
        text_rect = fitz.Rect(50, 50, 500, 700)
        page.insert_textbox(text_rect, text_content, fontsize=12, fontname="helv")
        
        # Save the PDF
        doc.save(temp_pdf)
        doc.close()
        
        return temp_pdf
    except Exception as e:
        print(f"Error creating test PDF: {e}")
        raise


def test_enhanced_workflow():
    """Test the complete enhanced PII workflow."""
    print("=" * 60)
    print("Testing Enhanced PII Detection and Masking Workflow")
    print("=" * 60)
    
    # Sample text with various PII types
    test_text = """Sample Document with PII
    
Name: John Doe
Email: john.doe@example.com  
Phone: (555) 123-4567
SSN: 123-45-6789
Address: 123 Main Street, Springfield, NY 10001
Credit Card: 4111-1111-1111-1111

This document contains fictional PII for testing purposes."""
    
    # Step 1: Create test PDF
    print("\n1. Creating test PDF...")
    temp_pdf_path = create_test_pdf(test_text)
    print(f"   Created: {temp_pdf_path}")
    
    try:
        # Step 2: Enhanced PII Detection
        print("\n2. Running Enhanced PII Detection...")
        detector = EnhancedPIIDetector()
        
        # Extract text and detect PII
        pages_data = detector.extract_text_with_coordinates(temp_pdf_path)
        all_detected_pii = []
        
        for page_text, page_num, doc in pages_data:
            if page_text.strip():
                page_obj = doc[page_num] if doc else None
                page_pii = detector.detect_all_pii(page_text, page_num, page_obj)
                all_detected_pii.extend(page_pii)
        
        if pages_data and len(pages_data) > 0:
            pages_data[0][2].close()
        
        print(f"   Detected {len(all_detected_pii)} PII entities:")
        for i, pii in enumerate(all_detected_pii[:5]):  # Show first 5
            print(f"   [{i+1}] {pii.pii_type}: '{pii.text}' (confidence: {pii.confidence:.2f}, source: {pii.source})")
        if len(all_detected_pii) > 5:
            print(f"   ... and {len(all_detected_pii) - 5} more")
        
        # Step 3: Generate Masking Configurations
        print("\n3. Generating Masking Configurations...")
        masking_configs = []
        
        # Create different strategies for different PII types
        strategy_map = {
            'PERSON': 'pseudo',
            'EMAIL': 'mask', 
            'PHONE': 'mask',
            'SSN': 'redact',
            'CREDIT_CARD': 'redact',
            'ADDRESS': 'pseudo'
        }
        
        for pii in all_detected_pii:
            strategy = strategy_map.get(pii.pii_type, 'redact')
            config = MaskingConfig(
                text=pii.text,
                pii_type=pii.pii_type,
                strategy=strategy,
                page_num=pii.page_num,
                x0=pii.x0,
                y0=pii.y0,
                x1=pii.x1,
                y1=pii.y1,
                priority=3 if strategy == 'redact' else 2 if strategy == 'mask' else 1
            )
            masking_configs.append(config)
        
        print(f"   Generated {len(masking_configs)} masking configurations")
        for strategy in strategy_map.values():
            count = sum(1 for cfg in masking_configs if cfg.strategy == strategy)
            if count > 0:
                print(f"   - {strategy}: {count} items")
        
        # Step 4: Apply Masking with Pre-configured Strategies
        print("\n4. Applying Enhanced Masking...")
        masker = EnhancedPIIMasker()
        masked_pdf_path = tempfile.mktemp(suffix='_masked.pdf')
        
        # Use the new method that accepts pre-configured strategies
        masking_stats = masker.mask_pdf_with_preconfigured_strategies(
            temp_pdf_path, masked_pdf_path, masking_configs
        )
        
        print(f"   Masking completed successfully!")
        print(f"   - Total regions processed: {masking_stats.get('total_regions_processed', 0)}")
        print(f"   - Successful maskings: {masking_stats.get('successful_maskings', 0)}")  
        print(f"   - Failed maskings: {masking_stats.get('failed_maskings', 0)}")
        print(f"   - Overlaps resolved: {masking_stats.get('overlaps_resolved', 0)}")
        print(f"   - Quality score: {masking_stats.get('quality_score', 0):.1f}%")
        print(f"   - Strategies used: {masking_stats.get('strategies_used', {})}")
        
        # Step 5: Verify Output
        print("\n5. Verifying Output...")
        if os.path.exists(masked_pdf_path):
            file_size = os.path.getsize(masked_pdf_path)
            print(f"   ✓ Masked PDF created: {masked_pdf_path} ({file_size} bytes)")
            
            # Quick text extraction to verify masking
            try:
                import fitz
                masked_doc = fitz.open(masked_pdf_path)
                masked_text = ""
                for page in masked_doc:
                    masked_text += page.get_text()
                masked_doc.close()
                
                print(f"   ✓ Masked document text length: {len(masked_text)} characters")
                if masked_text:
                    print(f"   First 200 chars: {repr(masked_text[:200])}")
            except Exception as e:
                print(f"   Warning: Could not extract text from masked PDF: {e}")
        else:
            print(f"   ✗ Masked PDF was not created")
        
        print("\n" + "=" * 60)
        print("Enhanced PII Workflow Test COMPLETED")
        print("=" * 60)
        
        # Clean up
        try:
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            if os.path.exists(masked_pdf_path):
                # Don't delete - keep for inspection
                print(f"\nMasked PDF available for inspection: {masked_pdf_path}")
        except Exception as e:
            print(f"Cleanup warning: {e}")
            
        return True
        
    except Exception as e:
        print(f"\nError during workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up original PDF
        try:
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        except Exception:
            pass


if __name__ == "__main__":
    success = test_enhanced_workflow()
    exit(0 if success else 1)
