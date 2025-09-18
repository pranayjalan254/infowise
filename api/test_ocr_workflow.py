#!/usr/bin/env python3
"""
Test script to verify the OCR and PII detection workflow.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.getcwd())

def test_pdf_scan_detection():
    """Test PDF scan detection functionality."""
    print("=== Testing PDF Scan Detection ===")
    
    from scripts.pdf_scan_detector import PDFScanDetector
    
    detector = PDFScanDetector()
    
    # Test with available PDFs
    test_files = [
        "scan-sample.pdf",
        "input.pdf", 
        "input1.pdf",
        "fake_pii_test_document.pdf"
    ]
    
    for pdf_file in test_files:
        if Path(pdf_file).exists():
            print(f"\nAnalyzing: {pdf_file}")
            try:
                analysis = detector.analyze_pdf(pdf_file)
                print(f"  Result: {'SCANNED' if analysis['is_scanned'] else 'TEXT-BASED'}")
                print(f"  Confidence: {analysis['confidence']:.1%}")
                print(f"  Total chars: {analysis['total_chars']}")
                print(f"  Avg chars/page: {analysis['avg_chars_per_page']:.1f}")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print(f"File not found: {pdf_file}")

def test_ocr_text_extraction():
    """Test OCR text extraction."""
    print("\n=== Testing OCR Text Extraction ===")
    
    # Test with scan-sample.pdf if it exists
    input_pdf = "scan-sample.pdf"
    output_text = "test_ocr_output.txt"
    
    if Path(input_pdf).exists():
        print(f"Processing: {input_pdf}")
        try:
            # Import from scripts directory
            sys.path.append("scripts")
            from ocr import process_pdf
            
            success = process_pdf(input_pdf, output_text)
            
            if success and Path(output_text).exists():
                print(f"✅ OCR extraction successful: {output_text}")
                
                # Show first few lines of output
                with open(output_text, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]  # First 10 lines
                    print("First 10 lines of extracted text:")
                    for i, line in enumerate(lines, 1):
                        print(f"  {i}: {line.strip()}")
                        
                # Clean up test file
                Path(output_text).unlink()
                print(f"Cleaned up: {output_text}")
            else:
                print("❌ OCR extraction failed")
                
        except Exception as e:
            print(f"Error during OCR: {e}")
    else:
        print(f"Test PDF not found: {input_pdf}")

def test_simple_workflow():
    """Test a simplified workflow without full API."""
    print("\n=== Testing Simplified Workflow ===")
    
    test_files = ["scan-sample.pdf", "input.pdf"]
    
    for test_file in test_files:
        if not Path(test_file).exists():
            continue
            
        print(f"\n--- Processing {test_file} ---")
        
        # Step 1: Detect if scanned
        try:
            from pdf_scan_detector import PDFScanDetector
            detector = PDFScanDetector()
            analysis = detector.analyze_pdf(test_file)
            
            print(f"PDF Type: {'SCANNED' if analysis['is_scanned'] else 'TEXT-BASED'}")
            print(f"Confidence: {analysis['confidence']:.1%}")
            
            # Step 2: If scanned, process with OCR
            if analysis['is_scanned']:
                print("Processing with OCR...")
                
                sys.path.append("scripts")
                from ocr import process_pdf
                
                output_text = f"temp_{Path(test_file).stem}_ocr.txt"
                success = process_pdf(test_file, output_text)
                
                if success and Path(output_text).exists():
                    print(f"✅ OCR completed: {output_text}")
                    
                    # Check file size
                    file_size = Path(output_text).stat().st_size
                    print(f"Text file size: {file_size} bytes")
                    
                    # Clean up
                    Path(output_text).unlink()
                    print("Cleaned up temporary file")
                else:
                    print("❌ OCR failed")
            else:
                print("No OCR needed - text-based PDF")
                
        except Exception as e:
            print(f"Error processing {test_file}: {e}")

if __name__ == "__main__":
    print("InfoWise OCR Workflow Test")
    print("=" * 40)
    
    # Test individual components
    test_pdf_scan_detection()
    test_ocr_text_extraction() 
    test_simple_workflow()
    
    print("\n=== Test Complete ===")