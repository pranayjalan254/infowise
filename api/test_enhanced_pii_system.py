#!/usr/bin/env python3
"""
Test script for Enhanced PII Detection and Masking System

This script tests the comprehensive PII detection and masking system using the 
provided fictional test document. It demonstrates:

1. Multi-method PII detection (BERT + Presidio + Regex + LLM verification)
2. Coordinate overlap resolution
3. Strategic masking with layout preservation
4. Comprehensive reporting

Usage:
    python test_enhanced_pii_system.py
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    logger.error("PyMuPDF not found. Please install: pip install PyMuPDF")
    sys.exit(1)

# Add API directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_pii_detector import EnhancedPIIDetector
from enhanced_pii_masker import EnhancedPIIMasker

def create_test_pdf(text_content: str, output_path: str):
    """Create a test PDF with the given text content."""
    try:
        doc = fitz.open()  # Create new PDF
        page = doc.new_page()
        
        # Insert text with proper formatting
        text_rect = fitz.Rect(50, 50, 550, 750)  # Margins for text
        page.insert_text(
            (50, 70),
            text_content,
            fontsize=11,
            fontname="helv",
            color=(0, 0, 0)
        )
        
        doc.save(output_path)
        doc.close()
        
        logger.info(f"Test PDF created: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create test PDF: {e}")
        return False

def test_enhanced_pii_detection(pdf_path: str, google_api_key: str = None):
    """Test enhanced PII detection on the test PDF."""
    logger.info("Testing Enhanced PII Detection...")
    logger.info("=" * 60)
    
    try:
        # Initialize enhanced detector
        detector = EnhancedPIIDetector(google_api_key=google_api_key)
        
        # Extract text and detect PII
        pages_data = detector.extract_text_with_coordinates(pdf_path)
        all_detected_pii = []
        
        for page_text, page_num, doc in pages_data:
            if page_text.strip():
                page = doc[page_num]
                page_pii = detector.detect_all_pii(page_text, page_num, page)
                all_detected_pii.extend(page_pii)
        
        # Close document
        if pages_data:
            pages_data[0][2].close()
        
        # Generate detection report
        detection_report = detector.generate_detection_report(all_detected_pii)
        
        # Display results
        logger.info(f"Total PII entities detected: {len(all_detected_pii)}")
        logger.info("\nDetected PII Entities:")
        logger.info("-" * 40)
        
        for i, entity in enumerate(all_detected_pii, 1):
            logger.info(f"{i:2d}. '{entity.text}' [{entity.pii_type}]")
            logger.info(f"     Source: {entity.source} | Confidence: {entity.confidence:.3f}")
            logger.info(f"     Strategy: {entity.suggested_strategy} | Severity: {entity.severity}")
            logger.info(f"     Coordinates: ({entity.x0:.1f}, {entity.y0:.1f}, {entity.x1:.1f}, {entity.y1:.1f})")
            if entity.verified_by_llm:
                logger.info(f"     ✓ LLM Verified")
            logger.info("")
        
        logger.info("\nDetection Statistics:")
        logger.info("-" * 40)
        logger.info(f"Total entities: {detection_report['total_entities']}")
        
        logger.info("\nBy PII Type:")
        for pii_type, count in detection_report['by_type'].items():
            logger.info(f"  {pii_type}: {count}")
        
        logger.info("\nBy Detection Source:")
        for source, count in detection_report['by_source'].items():
            logger.info(f"  {source}: {count}")
        
        logger.info("\nBy Severity:")
        for severity, count in detection_report['by_severity'].items():
            logger.info(f"  {severity}: {count}")
        
        verification_stats = detection_report['verification_stats']
        if verification_stats['llm_verified'] > 0:
            logger.info(f"\nLLM Verification:")
            logger.info(f"  Verified: {verification_stats['llm_verified']}")
            logger.info(f"  False positives found: {verification_stats['false_positives_found']}")
        
        return all_detected_pii
        
    except Exception as e:
        logger.error(f"Error in PII detection: {e}")
        return []

def test_enhanced_pii_masking(pdf_path: str, output_path: str, google_api_key: str = None):
    """Test enhanced PII masking with coordinate overlap resolution."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Enhanced PII Masking...")
    logger.info("=" * 60)
    
    try:
        # Initialize enhanced masker
        masker = EnhancedPIIMasker()
        
        # Apply enhanced masking
        masking_stats = masker.mask_pdf_with_enhanced_detection(
            pdf_path, output_path, google_api_key
        )
        
        # Generate comprehensive report
        report = masker.generate_comprehensive_report(masking_stats)
        
        logger.info("\nMasking Results:")
        logger.info("-" * 40)
        logger.info(f"Quality Score: {masking_stats.get('quality_score', 0):.1f}%")
        logger.info(f"Pages Processed: {masking_stats.get('pages_processed', 0)}")
        logger.info(f"Total PII Detected: {masking_stats.get('total_pii_detected', 0)}")
        logger.info(f"Overlaps Resolved: {masking_stats.get('overlaps_resolved', 0)}")
        logger.info(f"Regions Processed: {masking_stats.get('total_regions_processed', 0)}")
        logger.info(f"Failed Maskings: {masking_stats.get('failed_maskings', 0)}")
        
        strategies_used = masking_stats.get('strategies_used', {})
        if strategies_used:
            logger.info("\nStrategies Used:")
            for strategy, count in strategies_used.items():
                logger.info(f"  {strategy.upper()}: {count} instances")
        
        logger.info(f"\nMasked PDF created: {output_path}")
        
        # Save detailed report
        report_path = output_path.replace('.pdf', '_report.txt')
        masker.generate_comprehensive_report(masking_stats, report_path)
        logger.info(f"Detailed report saved: {report_path}")
        
        return masking_stats
        
    except Exception as e:
        logger.error(f"Error in PII masking: {e}")
        return {}

def main():
    """Main test function."""
    # Test document with comprehensive PII types
    test_document = """Fictional PII Test Document
Fictional test document — all data below is made-up and intended for PII masking tests.
My name is Aaron Mehta. I was born on 12/07/1989 and I grew up on 221B Meadow Lane, Flat
4A, Greenfield Towers, Newtown, NY 10001. People call me Aaron or A. Mehta. My passport
number is X1234567, and my driver's license reads DL-NY-0987654321. At home my phone
rings on +1 (212) 555-0198 and my mobile is +91 98765 43210. My work email is
aaron.mehta@example-test.com and my personal email is a.mehta89@mailtest.co.
Last week I received a bank notice about account 012345678901 at First National Bank, routing
number 021000021, and IBAN GB29 NWBK 6016 1331 9268 19 (sample). My credit card on file
ends with 1111 (Card: 4111-XXXX-XXXX-1111). The temporary OTP I used was 482915. My
social security number on the form was 123-45-6789. For tax purposes I used PAN:
PMTAR1234Q and Aadhaar-like ID 9999 8888 7777 (both fictional).
The day I moved to the city, the moving truck (plate: KA-05-MQ-2025) stopped outside 78,
Sunrise Apartments, Lavender Street, Block C, Sector 21. My emergency contact is Priya
Kapoor, sister, reachable at +91-91234-56789 or priya.kapoor-home@testmail.in; her office is at
18B Commerce Plaza, 7th Floor, Mumbai 400001. My company ID badge shows EmployeeID:
EMP-2024-0456 and my manager, Mr. Jonathan Clarke, listed his corporate phone as +44 20
7946 0958.
I once booked a medical appointment and their form captured my insurance policy number:
INS-GB-556677-8899 and policyholder DOB 03/03/1965. My medical record number (MRN) at
Cedar Clinic was MRN-778899. The clinic stored an emergency contact address: 9, Old Bridge
Road, Apt 2, Elm County, CT 06701.
For a parcel delivery I used courier tracking TRK-9876543210 and gave the GPS drop-off
coordinates 40.712776, -74.005974. My laptop was registered with MAC: 00:1A:2B:3C:4D:5E
and IP 192.168.1.42 (local) / 203.0.113.45 (public sample). My LinkedIn is
linkedin.com/in/aaron-mehta-test and GitHub at github.com/amehta-sample.
I remember the interview where I gave my university details: Meadowbrook Institute, StudentID
2010002233, email aaron.student@meadowbrook.edu. My vaccine batch recorded lot no.
VAX-7788-2022 and barcode 890123456789012345. The shelter I volunteered at listed me
under VolunteerCode VOL-21-334 and recorded my emergency donation receipt
RN-2024-990077.
This short narrative intentionally includes multiple PII types — full names, nicknames, dates of
birth, postal addresses, phone numbers, emails, passport and license numbers, bank and
routing numbers, national IDs, insurance IDs, device identifiers, IP/MAC addresses, employee
and student IDs, tracking numbers, and vehicle registration — all fictional. Use this page to
validate redaction and masking behavior."""

    logger.info("Enhanced PII Detection and Masking Test")
    logger.info("=" * 60)
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as input_temp:
        input_pdf = input_temp.name
    
    output_pdf = tempfile.mktemp(suffix='_masked.pdf')
    
    try:
        # Create test PDF
        if not create_test_pdf(test_document, input_pdf):
            return 1
        
        # Get Google API key if available
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            logger.info("✓ Google API key found - Gemini LLM verification will be enabled")
        else:
            logger.warning("⚠ No Google API key found - LLM verification will be disabled")
            logger.warning("  Set GOOGLE_API_KEY environment variable for full functionality")
        
        # Test enhanced PII detection
        detected_pii = test_enhanced_pii_detection(input_pdf, google_api_key)
        
        if not detected_pii:
            logger.error("No PII detected - cannot test masking")
            return 1
        
        # Test enhanced PII masking
        masking_stats = test_enhanced_pii_masking(input_pdf, output_pdf, google_api_key)
        
        if not masking_stats:
            logger.error("Masking failed")
            return 1
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"Input PDF: {input_pdf}")
        logger.info(f"Masked PDF: {output_pdf}")
        logger.info(f"Overall Quality Score: {masking_stats.get('quality_score', 0):.1f}%")
        
        # Display key statistics
        total_detected = masking_stats.get('total_pii_detected', 0)
        overlaps_resolved = masking_stats.get('overlaps_resolved', 0)
        failed_maskings = masking_stats.get('failed_maskings', 0)
        
        logger.info(f"Total PII Entities: {total_detected}")
        if overlaps_resolved > 0:
            logger.info(f"Coordinate Overlaps Resolved: {overlaps_resolved}")
        if failed_maskings > 0:
            logger.warning(f"Failed Maskings: {failed_maskings}")
        
        logger.info("\nFiles created for manual inspection:")
        logger.info(f"  Original: {input_pdf}")
        logger.info(f"  Masked: {output_pdf}")
        logger.info(f"  Report: {output_pdf.replace('.pdf', '_report.txt')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return 1
    
    finally:
        # Note: We're not deleting temp files so they can be inspected
        # In production, you'd want to clean them up
        pass

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
