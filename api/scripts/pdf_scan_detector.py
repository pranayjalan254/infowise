"""
PDF Scanner Detection Utility

This module provides functionality to detect if a PDF is scanned (image-based)
or text-based by analyzing the text content density and characteristics.
"""

import logging
import fitz  # PyMuPDF
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFScanDetector:
    """Detects if a PDF is scanned (image-based) or text-based."""
    
    # Configuration thresholds
    MIN_TEXT_DENSITY = 0.1  # Minimum characters per page area (characters per square inch)
    MIN_CHAR_COUNT = 50     # Minimum total characters to consider as text-based
    MIN_WORDS_PER_PAGE = 10 # Minimum words per page average
    MAX_CHAR_TO_IMAGE_RATIO = 0.05  # Max ratio of text chars to image area
    
    def __init__(self, 
                 min_text_density: float = MIN_TEXT_DENSITY,
                 min_char_count: int = MIN_CHAR_COUNT,
                 min_words_per_page: int = MIN_WORDS_PER_PAGE):
        """
        Initialize PDF scan detector with customizable thresholds.
        
        Args:
            min_text_density: Minimum text density to consider as text-based
            min_char_count: Minimum total characters to consider as text-based  
            min_words_per_page: Minimum average words per page
        """
        self.min_text_density = min_text_density
        self.min_char_count = min_char_count
        self.min_words_per_page = min_words_per_page
    
    def analyze_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF to determine if it's scanned or text-based.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict containing analysis results:
            - is_scanned: bool - True if PDF appears to be scanned
            - confidence: float - Confidence score (0-1)
            - total_chars: int - Total character count
            - total_pages: int - Total page count  
            - avg_chars_per_page: float - Average characters per page
            - avg_words_per_page: float - Average words per page
            - text_density: float - Text density score
            - has_images: bool - Whether PDF contains images
            - analysis_details: str - Human-readable analysis
        """
        try:
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            total_chars = 0
            total_words = 0
            total_pages = len(doc)
            has_images = False
            page_areas = []
            
            # Analyze each page
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Extract text and count characters/words
                page_text = page.get_text().strip()
                page_chars = len(page_text)
                page_words = len(page_text.split()) if page_text else 0
                
                total_chars += page_chars
                total_words += page_words
                
                # Get page dimensions for density calculation
                rect = page.rect
                page_area = rect.width * rect.height
                page_areas.append(page_area)
                
                # Check for images
                if not has_images:
                    image_list = page.get_images()
                    if image_list:
                        has_images = True
                        logger.debug(f"Found {len(image_list)} images on page {page_num + 1}")
            
            doc.close()
            
            # Calculate metrics
            avg_chars_per_page = total_chars / total_pages if total_pages > 0 else 0
            avg_words_per_page = total_words / total_pages if total_pages > 0 else 0
            avg_page_area = sum(page_areas) / len(page_areas) if page_areas else 1
            text_density = total_chars / avg_page_area if avg_page_area > 0 else 0
            
            # Determine if scanned based on multiple criteria
            is_scanned_criteria = []
            confidence_factors = []
            
            # Criterion 1: Very low character count
            if total_chars < self.min_char_count:
                is_scanned_criteria.append(True)
                confidence_factors.append(0.8)
                logger.debug(f"Low character count: {total_chars} < {self.min_char_count}")
            else:
                is_scanned_criteria.append(False)
                confidence_factors.append(0.2)
            
            # Criterion 2: Low text density  
            if text_density < self.min_text_density:
                is_scanned_criteria.append(True)
                confidence_factors.append(0.7)
                logger.debug(f"Low text density: {text_density:.4f} < {self.min_text_density}")
            else:
                is_scanned_criteria.append(False)
                confidence_factors.append(0.1)
            
            # Criterion 3: Low words per page
            if avg_words_per_page < self.min_words_per_page:
                is_scanned_criteria.append(True)
                confidence_factors.append(0.6)
                logger.debug(f"Low words per page: {avg_words_per_page:.1f} < {self.min_words_per_page}")
            else:
                is_scanned_criteria.append(False)
                confidence_factors.append(0.1)
            
            # Criterion 4: Has images but very little text (common in scanned docs)
            if has_images and avg_chars_per_page < 100:
                is_scanned_criteria.append(True)
                confidence_factors.append(0.5)
                logger.debug("Has images with very little text")
            else:
                is_scanned_criteria.append(False)
                confidence_factors.append(0.1)
            
            # Final decision: consider it scanned if majority of criteria suggest so
            scanned_votes = sum(is_scanned_criteria)
            is_scanned = scanned_votes >= 2  # At least 2 out of 4 criteria
            
            # Calculate confidence based on how many criteria agree
            if is_scanned:
                confidence = sum(confidence_factors[i] for i, is_scan in enumerate(is_scanned_criteria) if is_scan) / scanned_votes
            else:
                non_scanned_votes = len(is_scanned_criteria) - scanned_votes
                confidence = sum(confidence_factors[i] for i, is_scan in enumerate(is_scanned_criteria) if not is_scan) / max(non_scanned_votes, 1)
            
            # Generate analysis details
            analysis_details = self._generate_analysis_details(
                total_chars, total_pages, avg_chars_per_page, avg_words_per_page, 
                text_density, has_images, is_scanned, confidence
            )
            
            result = {
                'is_scanned': is_scanned,
                'confidence': round(confidence, 3),
                'total_chars': total_chars,
                'total_pages': total_pages,
                'avg_chars_per_page': round(avg_chars_per_page, 1),
                'avg_words_per_page': round(avg_words_per_page, 1),
                'text_density': round(text_density, 6),
                'has_images': has_images,
                'analysis_details': analysis_details
            }
            
            logger.info(f"PDF analysis complete: {pdf_path} -> {'SCANNED' if is_scanned else 'TEXT-BASED'} (confidence: {confidence:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {e}")
            raise
    
    def _generate_analysis_details(self, total_chars: int, total_pages: int, 
                                 avg_chars_per_page: float, avg_words_per_page: float,
                                 text_density: float, has_images: bool, 
                                 is_scanned: bool, confidence: float) -> str:
        """Generate human-readable analysis details."""
        
        details = []
        details.append(f"Total characters: {total_chars}")
        details.append(f"Total pages: {total_pages}")
        details.append(f"Average characters per page: {avg_chars_per_page:.1f}")
        details.append(f"Average words per page: {avg_words_per_page:.1f}")
        details.append(f"Text density: {text_density:.6f}")
        details.append(f"Contains images: {'Yes' if has_images else 'No'}")
        
        if is_scanned:
            details.append("CONCLUSION: PDF appears to be SCANNED/IMAGE-BASED")
            details.append("Reason: Low text content suggests images or scanned pages")
        else:
            details.append("CONCLUSION: PDF appears to be TEXT-BASED")
            details.append("Reason: Sufficient extractable text content found")
        
        details.append(f"Confidence: {confidence:.1%}")
        
        return " | ".join(details)
    
    def is_pdf_scanned(self, pdf_path: str, return_details: bool = False) -> bool | Dict[str, Any]:
        """
        Simple method to check if PDF is scanned.
        
        Args:
            pdf_path: Path to PDF file
            return_details: If True, return full analysis dict, else just boolean
            
        Returns:
            bool or dict: Whether PDF is scanned (or full analysis if return_details=True)
        """
        analysis = self.analyze_pdf(pdf_path)
        
        if return_details:
            return analysis
        else:
            return analysis['is_scanned']


# Convenience function for simple usage
def is_pdf_scanned(pdf_path: str, return_details: bool = False) -> bool | Dict[str, Any]:
    """
    Check if a PDF is scanned using default settings.
    
    Args:
        pdf_path: Path to PDF file
        return_details: If True, return analysis details
        
    Returns:
        bool or dict: Whether PDF is scanned
    """
    detector = PDFScanDetector()
    return detector.is_pdf_scanned(pdf_path, return_details)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python pdf_scan_detector.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        detector = PDFScanDetector()
        analysis = detector.analyze_pdf(pdf_path)
        
        print("=== PDF SCAN DETECTION ANALYSIS ===")
        print(f"File: {pdf_path}")
        print(f"Is Scanned: {'YES' if analysis['is_scanned'] else 'NO'}")
        print(f"Confidence: {analysis['confidence']:.1%}")
        print(f"Total Characters: {analysis['total_chars']}")
        print(f"Total Pages: {analysis['total_pages']}")
        print(f"Avg Characters/Page: {analysis['avg_chars_per_page']:.1f}")
        print(f"Avg Words/Page: {analysis['avg_words_per_page']:.1f}")
        print(f"Text Density: {analysis['text_density']:.6f}")
        print(f"Has Images: {'Yes' if analysis['has_images'] else 'No'}")
        print(f"Analysis: {analysis['analysis_details']}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)