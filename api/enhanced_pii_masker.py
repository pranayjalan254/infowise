#!/usr/bin/env python3
"""
Enhanced PII Masking System with Coordinate Overlap Resolution

This module provides comprehensive PII masking with:
1. Coordinate overlap detection and resolution
2. Multiple masking strategies (redact, mask, pseudo)
3. Smart font and layout preservation  
4. Conflict resolution for overlapping coordinates
5. Quality assurance and validation

Features:
- Handles overlapping coordinate rectangles intelligently
- Preserves document layout and formatting
- Provides detailed masking statistics and reports
- Supports batch processing with error recovery
"""

import os
import sys
import logging
import tempfile
import random
import threading
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import random
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    logger.error("PyMuPDF not found. Please install: pip install PyMuPDF")
    sys.exit(1)

from enhanced_pii_detector import EnhancedPIIDetector, PIIEntity

@dataclass
class MaskingConfig:
    """Configuration for PII masking operations."""
    text: str
    pii_type: str
    strategy: str
    page_num: int = 0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    replacement: Optional[str] = None
    priority: int = 1  # Higher numbers = higher priority for overlap resolution

@dataclass
class CoordinateRegion:
    """Represents a coordinate region with conflict resolution."""
    x0: float
    y0: float
    x1: float
    y1: float
    configs: List[MaskingConfig]
    page_num: int
    
    def overlaps_with(self, other: 'CoordinateRegion') -> bool:
        """Check if this region overlaps with another."""
        return not (self.x1 < other.x0 or other.x1 < self.x0 or 
                   self.y1 < other.y0 or other.y1 < self.y0)
    
    def merge_with(self, other: 'CoordinateRegion') -> 'CoordinateRegion':
        """Merge two overlapping regions."""
        return CoordinateRegion(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
            configs=self.configs + other.configs,
            page_num=self.page_num
        )
    
    def get_dominant_strategy(self) -> str:
        """Get the dominant masking strategy for merged regions."""
        if not self.configs:
            logger.warning("No configs available for getting dominant strategy")
            return "redact"
        
        # Priority order: redact > mask > pseudo
        strategies = [config.strategy for config in self.configs]
        logger.debug(f"Available strategies in region: {strategies}")
        
        if "redact" in strategies:
            return "redact"
        elif "mask" in strategies:
            return "mask"
        else:
            return "pseudo"

class EnhancedPIIMasker:
    """
    Enhanced PII masking system with coordinate overlap resolution.
    """
    
    def __init__(self):
        """Initialize the enhanced PII masker."""
        self.pseudo_data = self._initialize_pseudo_data()
        self.used_mappings = {}  # For consistency in pseudo replacements
        self.masking_stats = {
            "total_regions_processed": 0,
            "overlaps_resolved": 0,
            "strategies_used": {},
            "pages_processed": 0,
            "failed_maskings": 0,
            "quality_score": 0.0
        }
    
    def _initialize_pseudo_data(self) -> Dict[str, List[str]]:
        """Initialize pseudo data for different PII types."""
        return {
            "PERSON": [
                "Alex Johnson", "Jordan Smith", "Taylor Brown", "Morgan Davis",
                "Casey Wilson", "Riley Miller", "Avery Garcia", "Sage Anderson",
                "Drew Martinez", "Blake Thompson", "River Jones", "Phoenix Lee",
                "Kai Rodriguez", "Skylar White", "Quinn Harris", "Parker Clark",
                "Sage Chen", "Dakota Williams", "Cameron Lee", "Finley Moore"
            ],
            "ORGANIZATION": [
                "TechCorp Solutions", "Global Industries Inc", "Innovation Labs",
                "DataFlow Systems", "NextGen Technologies", "CloudFirst Corp",
                "SmartBridge LLC", "Digital Dynamics", "FutureTech Group",
                "MetaVision Inc", "Quantum Networks", "CyberEdge Solutions",
                "Alpha Dynamics", "Beta Systems", "Gamma Technologies"
            ],
            "LOCATION": [
                "Springfield", "Riverside", "Fairview", "Georgetown", "Madison",
                "Franklin", "Greenwood", "Oakville", "Hillcrest", "Brookfield",
                "Centerville", "Westfield", "Northbrook", "Southgate",
                "Maple Street", "Oak Avenue", "Pine Road", "Cedar Lane"
            ],
            "EMAIL": [
                "user1@example.com", "contact@samplecorp.com", "info@testdomain.org",
                "admin@placeholder.net", "support@demosite.com", "sales@mockcompany.biz",
                "hello@genericmail.org", "team@templatedomain.com"
            ],
            "PHONE": [
                "(555) 100-0001", "(555) 200-0002", "(555) 300-0003", 
                "(555) 400-0004", "(555) 500-0005", "(555) 600-0006",
                "(555) 700-0007", "(555) 800-0008", "(555) 900-0009"
            ],
            "ADDRESS": [
                "123 Main Street", "456 Oak Avenue", "789 Pine Road",
                "321 Elm Drive", "654 Maple Lane", "987 Cedar Boulevard",
                "147 Birch Way", "258 Spruce Circle", "369 Willow Court"
            ]
        }
    
    def detect_coordinate_overlaps(self, configs: List[MaskingConfig]) -> List[CoordinateRegion]:
        """
        Detect and resolve coordinate overlaps in masking configurations.
        
        Args:
            configs: List of masking configurations
            
        Returns:
            List of non-overlapping coordinate regions
        """
        if not configs:
            return []
        
        # Group configs by page
        pages = {}
        for config in configs:
            page_num = config.page_num
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(config)
        
        all_regions = []
        
        for page_num, page_configs in pages.items():
            # Create initial regions
            regions = []
            for config in page_configs:
                region = CoordinateRegion(
                    x0=config.x0,
                    y0=config.y0,
                    x1=config.x1,
                    y1=config.y1,
                    configs=[config],
                    page_num=page_num
                )
                regions.append(region)
            
            # Resolve overlaps
            resolved_regions = self._resolve_overlapping_regions(regions)
            all_regions.extend(resolved_regions)
        
        return all_regions
    
    def _resolve_overlapping_regions(self, regions: List[CoordinateRegion]) -> List[CoordinateRegion]:
        """Resolve overlapping coordinate regions."""
        if not regions:
            return []
        
        # Sort regions by position (top-left to bottom-right)
        regions.sort(key=lambda r: (r.y0, r.x0))
        
        resolved = []
        overlaps_found = 0
        
        for current in regions:
            merged = False
            
            # Check for overlaps with existing resolved regions
            for i, existing in enumerate(resolved):
                if current.overlaps_with(existing):
                    # Merge the regions
                    merged_region = existing.merge_with(current)
                    resolved[i] = merged_region
                    merged = True
                    overlaps_found += 1
                    logger.debug(f"Merged overlapping regions on page {current.page_num}")
                    break
            
            if not merged:
                resolved.append(current)
        
        # Update statistics
        self.masking_stats["overlaps_resolved"] += overlaps_found
        
        # Second pass to handle chain overlaps
        if overlaps_found > 0:
            return self._resolve_overlapping_regions(resolved)
        
        return resolved
    
    def generate_replacement_text(self, region: CoordinateRegion) -> str:
        """Generate appropriate replacement text for a coordinate region."""
        if not region.configs:
            logger.warning("No configs in region, using default [REDACTED]")
            return "[REDACTED]"
        
        strategy = region.get_dominant_strategy()
        logger.info(f"Generating replacement text with strategy: {strategy}")
        
        if strategy == "redact":
            return "[REDACTED]"
        
        elif strategy == "mask":
            # Use the longest text for masking length
            max_length = max(len(config.text) for config in region.configs)
            return "*" * max_length
        
        elif strategy == "pseudo":
            # Use the first config's type for pseudo replacement
            first_config = region.configs[0]
            logger.info(f"Generating pseudo replacement for type: {first_config.pii_type}, text: '{first_config.text}'")
            replacement = self._get_pseudo_replacement(first_config.pii_type, first_config.text)
            logger.info(f"Generated pseudo replacement: '{replacement}'")
            return replacement
        
        else:
            logger.warning(f"Unknown strategy: {strategy}, using [MASKED]")
            return "[MASKED]"
    
    def _get_pseudo_replacement(self, pii_type: str, original_text: str) -> str:
        """Get consistent pseudo replacement for PII."""
        logger.debug(f"Getting pseudo replacement for type: '{pii_type}', text: '{original_text}'")
        
        # Check existing mappings for consistency
        if original_text in self.used_mappings:
            cached_replacement = self.used_mappings[original_text]
            logger.debug(f"Using cached replacement: '{cached_replacement}'")
            return cached_replacement
        
        # Map PII type to pseudo data category
        type_mapping = {
            "PERSON": "PERSON",
            "PER": "PERSON",
            "ORGANIZATION": "ORGANIZATION", 
            "ORG": "ORGANIZATION",
            "EMAIL": "EMAIL",
            "EMAIL_ADDRESS": "EMAIL",
            "PHONE": "PHONE",
            "PHONE_NUMBER": "PHONE",
            "LOCATION": "LOCATION",
            "LOC": "LOCATION",
            "ADDRESS": "ADDRESS"
        }
        
        pseudo_category = type_mapping.get(pii_type.upper(), "PERSON")
        logger.debug(f"Mapped PII type '{pii_type}' to pseudo category: '{pseudo_category}'")
        
        if pseudo_category in self.pseudo_data:
            replacement = random.choice(self.pseudo_data[pseudo_category])
            logger.debug(f"Selected pseudo replacement from {pseudo_category}: '{replacement}'")
        else:
            replacement = f"[MASKED_{pii_type}]"
            logger.debug(f"No pseudo data for category '{pseudo_category}', using fallback: '{replacement}'")
        
        # Store mapping for consistency
        self.used_mappings[original_text] = replacement
        return replacement
    
    def apply_masking_to_page(self, page, regions: List[CoordinateRegion]) -> Dict[str, Any]:
        """
        Apply masking to a PDF page using resolved coordinate regions.
        
        Args:
            page: PDF page object
            regions: List of resolved coordinate regions
            
        Returns:
            Dictionary with masking statistics for this page
        """
        page_stats = {
            "regions_processed": 0,
            "successful_maskings": 0,
            "failed_maskings": 0,
            "strategies_used": {}
        }
        
        for region in regions:
            if region.page_num != page.number:
                continue
            
            try:
                # Generate replacement text
                replacement_text = self.generate_replacement_text(region)
                strategy = region.get_dominant_strategy()
                
                logger.info(f"Processing region on page {page.number}: strategy={strategy}, text='{replacement_text[:30]}...', coords=({region.x0:.1f},{region.y0:.1f},{region.x1:.1f},{region.y1:.1f})")
                
                # Apply the masking
                success = self._apply_masking_strategy(page, region, replacement_text, strategy)
                
                if success:
                    page_stats["successful_maskings"] += 1
                    page_stats["strategies_used"][strategy] = page_stats["strategies_used"].get(strategy, 0) + 1
                    logger.debug(f"Successfully applied {strategy} masking")
                else:
                    page_stats["failed_maskings"] += 1
                    logger.warning(f"Failed to apply {strategy} masking")
                
                page_stats["regions_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error masking region on page {page.number}: {e}")
                page_stats["failed_maskings"] += 1
        
        return page_stats
    
    def _apply_masking_strategy(self, page, region: CoordinateRegion, replacement_text: str, strategy: str) -> bool:
        """
        Apply masking strategy to a specific coordinate region.
        
        Args:
            page: PDF page object
            region: Coordinate region to mask
            replacement_text: Text to use as replacement
            strategy: Masking strategy to apply
            
        Returns:
            True if masking was successful, False otherwise
        """
        try:
            rect = fitz.Rect(region.x0, region.y0, region.x1, region.y1)
            
            if strategy == "redact":
                # Use proper redaction annotation to completely remove underlying text
                redact_annot = page.add_redact_annot(rect, text="[REDACTED]")
                redact_annot.set_info(content="[REDACTED]")
                redact_annot.update()
                return True
            
            elif strategy in ["mask", "pseudo"]:
                # Use redaction annotation with replacement text to properly remove original text
                redact_annot = page.add_redact_annot(rect, text=replacement_text)
                redact_annot.set_info(content=replacement_text)
                redact_annot.update()
                return True
            
            else:
                logger.warning(f"Unknown masking strategy: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying {strategy} masking: {e}")
            return False
    
    def _replace_text_with_formatting(self, page, rect: fitz.Rect, replacement_text: str) -> bool:
        """
        Replace text in rectangle with proper font matching.
        
        Args:
            page: PDF page object
            rect: Rectangle to replace text in
            replacement_text: New text to insert
            
        Returns:
            True if replacement was successful
        """
        try:
            # Get text information from the rectangle
            text_dict = page.get_text("dict", clip=rect)
            
            if not text_dict or 'blocks' not in text_dict:
                return self._fallback_text_replacement(page, rect, replacement_text)
            
            # Find text properties from original text
            font_size = 11
            font_name = "helvetica"
            text_color = (0, 0, 0)  # Default black
            baseline_y = rect.y1 - 2  # Default baseline
            
            for block in text_dict['blocks']:
                if block.get('type') == 0 and 'lines' in block:  # Text block
                    for line in block['lines']:
                        if 'spans' in line:
                            for span in line['spans']:
                                if span.get('size', 0) > 0:
                                    font_size = span['size']
                                    font_name = span.get('font', 'helvetica')
                                    
                                    # Correct color extraction from integer
                                    if 'color' in span:
                                        color_int = span['color']
                                        # Convert from BGR integer to RGB float tuple (0-1)
                                        text_color = (
                                            ((color_int >> 16) & 0xFF) / 255.0,
                                            ((color_int >> 8) & 0xFF) / 255.0,
                                            (color_int & 0xFF) / 255.0
                                        )
                                    
                                    # Better baseline calculation
                                    if 'bbox' in span:
                                        baseline_y = span['bbox'][3] - (span['bbox'][3] - span['bbox'][1]) * 0.2
                                    break
            
            # Clear the original text area more precisely
            # Instead of drawing a white rectangle, we'll use a more precise approach
            # First, try to find the exact text bounds
            actual_text_areas = []
            for block in text_dict['blocks']:
                if block.get('type') == 0 and 'lines' in block:
                    for line in block['lines']:
                        if 'spans' in line:
                            for span in line['spans']:
                                if span.get('text', '').strip() and 'bbox' in span:
                                    actual_text_areas.append(fitz.Rect(span['bbox']))
            
            # Clear only the actual text areas instead of the entire rectangle
            if actual_text_areas:
                for text_area in actual_text_areas:
                    # Make slightly larger to ensure coverage
                    cover_area = fitz.Rect(text_area.x0 - 0.5, text_area.y0 - 0.5, 
                                         text_area.x1 + 0.5, text_area.y1 + 0.5)
                    page.draw_rect(cover_area, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            else:
                # Fallback: clear the entire rectangle but make it smaller
                smaller_rect = fitz.Rect(rect.x0 + 0.5, rect.y0 + 0.5, 
                                       rect.x1 - 0.5, rect.y1 - 0.5)
                page.draw_rect(smaller_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            
            # Get proper font name for PyMuPDF
            font_name = self._get_proper_fontname(font_name, 0)
            
            # Adjust font size if replacement text is longer than original
            available_width = rect.width - 4  # 2px padding on each side
            if available_width > 0 and len(replacement_text) > 0:
                # Estimate character width (approximation)
                char_width = font_size * 0.6  # Typical character width ratio
                needed_width = len(replacement_text) * char_width
                
                if needed_width > available_width:
                    font_size = font_size * (available_width / needed_width)
                    font_size = max(font_size, 8)  # Minimum readable size
            
            # Insert replacement text with proper positioning
            insertion_point = (
                rect.x0 + 2,  # Small left padding
                baseline_y if baseline_y > rect.y0 else rect.y1 - 3
            )
            
            result = page.insert_text(
                insertion_point,
                replacement_text,
                fontsize=font_size,
                fontname=font_name,
                color=text_color
            )
            
            if result < 0:
                logger.warning(f"Text insertion failed, using fallback method")
                return self._fallback_text_replacement(page, rect, replacement_text)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in text replacement: {e}")
            return self._fallback_text_replacement(page, rect, replacement_text)
    
    def _fallback_text_replacement(self, page, rect: fitz.Rect, replacement_text: str) -> bool:
        """Fallback method for text replacement when detailed font info isn't available."""
        try:
            # Clear the area with white background
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            
            # Calculate appropriate font size based on rectangle height
            font_size = min(rect.height * 0.7, 12)  # 70% of height, max 12pt
            font_size = max(font_size, 8)  # Minimum 8pt
            
            # Calculate text position (center vertically, small left margin)
            text_x = rect.x0 + 2
            text_y = rect.y0 + rect.height * 0.75  # Position text properly in rectangle
            
            # Use a standard font
            result = page.insert_text(
                (text_x, text_y),
                replacement_text,
                fontsize=font_size,
                fontname="helv",  # Helvetica
                color=(0, 0, 0)  # Black
            )
            
            return result >= 0
            
        except Exception as e:
            logger.error(f"Fallback text replacement failed: {e}")
            # Last resort: just draw a rectangle
            try:
                page.draw_rect(rect, color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8), width=0)
                return True
            except:
                return False
    
    def _get_proper_fontname(self, original_font: str, font_flags: int) -> str:
        """Convert font name to PyMuPDF format with better font mapping."""
        if not original_font:
            return "helv"
            
        font_lower = original_font.lower()
        
        # Handle common font families with better mapping
        if 'helvetica' in font_lower or 'arial' in font_lower:
            return "helv"
        elif 'times' in font_lower:
            return "tiro"  # Times Roman
        elif 'courier' in font_lower:
            return "cour"  # Courier
        else:
            return "helv"  # Default fallback
    
    def mask_pdf_with_preconfigured_strategies(self, input_pdf_path: str, output_pdf_path: str, 
                                             masking_configs: List[MaskingConfig]) -> Dict[str, Any]:
        """
        Mask PII in PDF using pre-configured masking strategies and coordinates.
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path to output PDF
            masking_configs: Pre-configured list of MaskingConfig objects with coordinates and strategies
            
        Returns:
            Comprehensive masking statistics
        """
        try:
            logger.info(f"Starting PDF masking with {len(masking_configs)} pre-configured strategies")
            
            # Resolve coordinate overlaps
            resolved_regions = self.detect_coordinate_overlaps(masking_configs)
            logger.info(f"Resolved to {len(resolved_regions)} non-overlapping regions")
            
            # Apply masking
            doc = fitz.open(input_pdf_path)
            
            total_stats = {
                "total_regions_processed": 0,
                "successful_maskings": 0,
                "failed_maskings": 0,
                "strategies_used": {},
                "pages_processed": 0,
                "overlaps_resolved": self.masking_stats.get("overlaps_resolved", 0),
                "quality_score": 0.0
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_regions = [r for r in resolved_regions if r.page_num == page_num]
                
                if page_regions:
                    page_stats = self.apply_masking_to_page(page, page_regions)
                    
                    # Apply all redaction annotations to actually remove underlying text
                    page.apply_redactions()
                    
                    # Update overall statistics
                    total_stats["total_regions_processed"] += page_stats.get("regions_processed", 0)
                    total_stats["successful_maskings"] += page_stats.get("successful_maskings", 0)
                    total_stats["failed_maskings"] += page_stats.get("failed_maskings", 0)
                    
                    # Merge strategy statistics
                    for strategy, count in page_stats.get("strategies_used", {}).items():
                        total_stats["strategies_used"][strategy] = total_stats["strategies_used"].get(strategy, 0) + count
                    
                    total_stats["pages_processed"] += 1
            
            # Calculate quality score
            total_attempted = total_stats["successful_maskings"] + total_stats["failed_maskings"]
            total_stats["quality_score"] = (total_stats["successful_maskings"] / total_attempted * 100) if total_attempted > 0 else 100.0
            
            # Save the masked PDF
            doc.save(output_pdf_path)
            doc.close()
            
            logger.info(f"PDF masking completed successfully")
            logger.info(f"Quality Score: {total_stats['quality_score']:.1f}%")
            
            return total_stats
            
        except Exception as e:
            logger.error(f"Error in PDF masking with preconfigured strategies: {str(e)}")
            raise
    
    def mask_pdf_with_enhanced_detection(self, input_pdf_path: str, output_pdf_path: str, 
                                       google_api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Mask PII in PDF using enhanced detection and coordinate overlap resolution.
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path to output PDF  
            google_api_key: Google API key for Gemini LLM verification
            
        Returns:
            Comprehensive masking statistics
        """
        try:
            # Initialize enhanced detector
            detector = EnhancedPIIDetector(google_api_key=google_api_key)
            
            # Extract text and detect PII
            pages_data = detector.extract_text_with_coordinates(input_pdf_path)
            all_detected_pii = []
            
            for page_text, page_num, doc in pages_data:
                if page_text.strip():
                    page = doc[page_num]
                    page_pii = detector.detect_all_pii(page_text, page_num, page)
                    all_detected_pii.extend(page_pii)
            
            # Convert PIIEntity objects to MaskingConfig objects
            masking_configs = []
            for pii in all_detected_pii:
                config = MaskingConfig(
                    text=pii.text,
                    pii_type=pii.pii_type,
                    strategy=pii.suggested_strategy,
                    page_num=pii.page_num,
                    x0=pii.x0,
                    y0=pii.y0, 
                    x1=pii.x1,
                    y1=pii.y1,
                    priority=self._get_strategy_priority(pii.suggested_strategy)
                )
                masking_configs.append(config)
            
            # Resolve coordinate overlaps
            resolved_regions = self.detect_coordinate_overlaps(masking_configs)
            
            # Apply masking
            doc = fitz.open(input_pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_regions = [r for r in resolved_regions if r.page_num == page_num]
                
                page_stats = self.apply_masking_to_page(page, page_regions)
                
                # Apply all redaction annotations to actually remove underlying text
                if page_regions:  # Only apply if there were regions to mask
                    page.apply_redactions()
                
                # Update overall statistics
                self.masking_stats["pages_processed"] += 1
                self.masking_stats["total_regions_processed"] += page_stats["regions_processed"] 
                self.masking_stats["failed_maskings"] += page_stats["failed_maskings"]
                
                for strategy, count in page_stats["strategies_used"].items():
                    self.masking_stats["strategies_used"][strategy] = (
                        self.masking_stats["strategies_used"].get(strategy, 0) + count
                    )
            
            # Save masked PDF
            doc.save(output_pdf_path)
            doc.close()
            
            # Close original document
            if pages_data:
                pages_data[0][2].close()
            
            # Calculate quality score
            total_attempts = self.masking_stats["total_regions_processed"] 
            successful = total_attempts - self.masking_stats["failed_maskings"]
            self.masking_stats["quality_score"] = (successful / total_attempts * 100) if total_attempts > 0 else 0
            
            # Add detection statistics
            detection_report = detector.generate_detection_report(all_detected_pii)
            
            final_stats = {
                **self.masking_stats,
                "detection_stats": detection_report,
                "total_pii_detected": len(all_detected_pii),
                "total_configs_generated": len(masking_configs),
                "total_regions_after_merge": len(resolved_regions)
            }
            
            logger.info(f"Enhanced PII masking completed successfully")
            logger.info(f"Quality Score: {final_stats['quality_score']:.1f}%")
            
            return final_stats
            
        except Exception as e:
            logger.error(f"Error in enhanced PII masking: {e}")
            raise
    
    def _get_strategy_priority(self, strategy: str) -> int:
        """Get priority level for masking strategy."""
        priorities = {
            "redact": 3,    # Highest priority
            "mask": 2,
            "pseudo": 1     # Lowest priority
        }
        return priorities.get(strategy, 1)
    
    def generate_comprehensive_report(self, stats: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate comprehensive masking report."""
        report_lines = [
            "Enhanced PII Masking Report",
            "=" * 50,
            f"Overall Quality Score: {stats.get('quality_score', 0):.1f}%",
            f"Pages Processed: {stats.get('pages_processed', 0)}",
            f"Total PII Detected: {stats.get('total_pii_detected', 0)}",
            f"Coordinate Overlaps Resolved: {stats.get('overlaps_resolved', 0)}",
            f"Total Regions Processed: {stats.get('total_regions_processed', 0)}",
            f"Failed Maskings: {stats.get('failed_maskings', 0)}",
            "",
            "Masking Strategies Used:",
            "-" * 30
        ]
        
        for strategy, count in stats.get("strategies_used", {}).items():
            report_lines.append(f"{strategy.upper()}: {count} instances")
        
        detection_stats = stats.get("detection_stats", {})
        if detection_stats:
            report_lines.extend([
                "",
                "Detection Statistics:",
                "-" * 30,
                f"Total Entities: {detection_stats.get('total_entities', 0)}"
            ])
            
            for pii_type, count in detection_stats.get("by_type", {}).items():
                report_lines.append(f"  {pii_type}: {count}")
            
            report_lines.extend([
                "",
                "Detection Sources:",
                "-" * 20
            ])
            
            for source, count in detection_stats.get("by_source", {}).items():
                report_lines.append(f"  {source}: {count}")
            
            verification = detection_stats.get("verification_stats", {})
            if verification:
                report_lines.extend([
                    "",
                    "LLM Verification:",
                    "-" * 20,
                    f"  Verified by LLM: {verification.get('llm_verified', 0)}",
                    f"  False Positives Found: {verification.get('false_positives_found', 0)}"
                ])
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Comprehensive report saved to: {output_path}")
        
        return report

def test_enhanced_masker():
    """Test the enhanced masker with sample data."""
    # Create test PDF with sample text
    test_text = """Fictional PII Test Document
My name is Aaron Mehta. I was born on 12/07/1989 and I grew up on 221B Meadow Lane, Flat
4A, Greenfield Towers, Newtown, NY 10001. People call me Aaron or A. Mehta. My passport
number is X1234567, and my driver's license reads DL-NY-0987654321. At home my phone
rings on +1 (212) 555-0198 and my mobile is +91 98765 43210. My work email is
aaron.mehta@example-test.com and my personal email is a.mehta89@mailtest.co."""
    
    # Create temporary PDF for testing
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_input:
        doc = fitz.open()  # Create new PDF
        page = doc.new_page()
        page.insert_text((50, 50), test_text, fontsize=12)
        doc.save(temp_input.name)
        doc.close()
        
        input_path = temp_input.name
    
    output_path = tempfile.mktemp(suffix='_masked.pdf')
    
    try:
        # Initialize enhanced masker
        masker = EnhancedPIIMasker()
        
        # Apply enhanced masking
        stats = masker.mask_pdf_with_enhanced_detection(input_path, output_path)
        
        # Generate report
        report = masker.generate_comprehensive_report(stats)
        
        print("Enhanced PII Masking Test Results:")
        print("=" * 50)
        print(report)
        
        print(f"\nMasked PDF created: {output_path}")
        
    finally:
        # Cleanup
        for path in [input_path, output_path]:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

if __name__ == "__main__":
    test_enhanced_masker()
