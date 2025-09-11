#!/usr/bin/env python3
"""
BERT-based PII Masker with Configurable Strategies

This script uses BERT NER model for PII detection and applies different masking strategies
based on input parameters. It preserves the original PDF layout while applying the 
specified masking strategy for each PII entity.

Input Format: PII:Type:Strategy
- PII: The actual text to be masked
- Type: The type of PII (PERSON, EMAIL, PHONE, etc.)
- Strategy: The masking strategy (redact, mask, pseudo)
- Coordinates: rectangle coordinates (x0, y0, x1, y1)

Usage:
    python bert_pii_masker.py input.pdf output.pdf pii_config.txt
    python bert_pii_masker.py input.pdf output.pdf --interactive
"""

import sys
import os
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not found. Please install: pip install PyMuPDF")
    sys.exit(1)

@dataclass
class PIIConfig:
    """Configuration for PII masking with coordinates."""
    text: str
    pii_type: str
    strategy: str
    page_num: int = 0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    replacement: Optional[str] = None

class BERTPIIMasker:
    """
    BERT-based PII masker with configurable strategies.
    """
    
    def __init__(self):
        self.ner_pipeline = None
        self.pseudo_data = self._initialize_pseudo_data()
        self.used_mappings = {}  
        self._initialize_bert_model()
    
    def _initialize_bert_model(self):
        """Initialize BERT NER model."""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
            
            model_name = "dslim/bert-base-NER"
            logger.info(f"Loading BERT model: {model_name}")
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            self.ner_pipeline = pipeline("ner", 
                                        model=model, 
                                        tokenizer=tokenizer,
                                        aggregation_strategy="simple")
            logger.info("✓ BERT model loaded successfully")
            
        except ImportError:
            logger.error("Transformers not installed. Please run: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            raise
    
    def _initialize_pseudo_data(self) -> Dict[str, List[str]]:
        """Initialize pseudo data for different PII types."""
        return {
            "PERSON": [
                "Alex Johnson", "Jordan Smith", "Taylor Brown", "Morgan Davis",
                "Casey Wilson", "Riley Miller", "Avery Garcia", "Sage Anderson",
                "Drew Martinez", "Blake Thompson", "River Jones", "Phoenix Lee",
                "Kai Rodriguez", "Skylar White", "Quinn Harris", "Parker Clark"
            ],
            "ORG": [
                "TechCorp Solutions", "Global Industries Inc", "Innovation Labs",
                "DataFlow Systems", "NextGen Technologies", "CloudFirst Corp",
                "SmartBridge LLC", "Digital Dynamics", "FutureTech Group",
                "MetaVision Inc", "Quantum Networks", "CyberEdge Solutions"
            ],
            "LOC": [
                "Springfield", "Riverside", "Fairview", "Georgetown", "Madison",
                "Franklin", "Greenwood", "Oakville", "Hillcrest", "Brookfield",
                "Centerville", "Westfield", "Northbrook", "Southgate"
            ],
            "EMAIL": [
                "user1@example.com", "contact@samplecorp.com", "info@testdomain.org",
                "admin@placeholder.net", "support@demosite.com", "sales@mockcompany.biz"
            ],
            "PHONE": [
                "(555) 100-0001", "(555) 200-0002", "(555) 300-0003", 
                "(555) 400-0004", "(555) 500-0005", "(555) 600-0006"
            ],
            "SSN": [
                "XXX-XX-1001", "XXX-XX-2002", "XXX-XX-3003", 
                "XXX-XX-4004", "XXX-XX-5005", "XXX-XX-6006"
            ],
            "ADDRESS": [
                "123 Main Street", "456 Oak Avenue", "789 Pine Road",
                "321 Elm Drive", "654 Maple Lane", "987 Cedar Boulevard"
            ],
            "CREDIT_CARD": [
                "XXXX-XXXX-XXXX-1234", "XXXX-XXXX-XXXX-5678",
                "XXXX-XXXX-XXXX-9012", "XXXX-XXXX-XXXX-3456"
            ],
            "BANK_ACCOUNT": [
                "XXXXXXXX1001", "XXXXXXXX2002", "XXXXXXXX3003",
                "XXXXXXXX4004", "XXXXXXXX5005", "XXXXXXXX6006"
            ],
            "DATE": [
                "01/01/1990", "02/15/1985", "03/22/1992", "04/30/1988",
                "05/18/1995", "06/12/1987", "07/25/1991", "08/14/1989"
            ]
        }
    
    def _get_pseudo_replacement(self, pii_type: str, original_text: str) -> str:
        """Get a consistent pseudo replacement for the given PII."""
        # Check if we already have a mapping for this exact text
        if original_text in self.used_mappings:
            return self.used_mappings[original_text]
        
        # Get pseudo data for this PII type
        if pii_type in self.pseudo_data:
            replacement = random.choice(self.pseudo_data[pii_type])
        else:
            # Fallback for unknown PII types
            replacement = f"[MASKED_{pii_type}]"
        
        # Store the mapping for consistency
        self.used_mappings[original_text] = replacement
        return replacement
    
    def _generate_mask_replacement(self, text: str, strategy: str) -> str:
        """Generate replacement text based on masking strategy."""
        if strategy.lower() == "mask":
            return "*" * len(text)
        elif strategy.lower() == "redact":
            return "[REDACTED]"
        else:
            return text  # Default fallback
    
    def detect_pii_with_bert(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using BERT NER model."""
        if not self.ner_pipeline:
            logger.warning("BERT model not available")
            return []
        
        try:
            entities = self.ner_pipeline(text)
            
            # Filter out false positives
            filtered_entities = []
            for entity in entities:
                if self._is_valid_pii_entity(entity):
                    filtered_entities.append(entity)
            
            return filtered_entities
            
        except Exception as e:
            logger.error(f"Error in BERT PII detection: {e}")
            return []
    
    def _is_valid_pii_entity(self, entity: Dict[str, Any]) -> bool:
        """Filter out false positives and non-PII entities."""
        word = entity['word'].strip()
        entity_type = entity['entity_group']
        score = entity['score']
        
        # Skip BERT tokenizer artifacts
        if word.startswith('##'):
            return False
        
        # Skip very short words
        if len(word) <= 2:
            return False
        
        # Skip low confidence detections
        if score < 0.7:
            return False
        
        # Skip common non-PII terms
        non_pii_terms = {
            'we', 'in', 'ad', 'co', 'or', 'a', 'e', 'x', 'c', 'h', 'z',
            'management', 'investment', 'service', 'product', 'products',
            'advisor', 'custom', 'level', 'face', 'pan', 'act', 'boom'
        }
        
        if word.lower() in non_pii_terms:
            return False
        
        # Allow specific PII types
        allowed_pii_types = {'PER', 'EMAIL', 'PHONE', 'SSN', 'ORG', 'LOC', 'MISC'}
        return entity_type in allowed_pii_types
    
    def parse_pii_config(self, config_input: str) -> List[PIIConfig]:
        """
        Parse PII configuration from input string or file.
        
        Format: PII:Type:Strategy or PII:Type:Strategy:Page:X0:Y0:X1:Y1
        Example: John Doe:PERSON:pseudo:0:100.5:200.3:180.7:220.1
                user@email.com:EMAIL:mask
                123-45-6789:SSN:redact
        """
        configs = []
        
        if os.path.isfile(config_input):
            # Read from file
            with open(config_input, 'r') as f:
                lines = f.readlines()
        else:
            # Parse as string input
            lines = config_input.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                parts = line.split(':')
                if len(parts) >= 3:
                    pii_text = parts[0].strip()
                    pii_type = parts[1].strip().upper()
                    strategy = parts[2].strip().lower()
                    
                    # Initialize default values
                    page_num = 0
                    x0 = y0 = x1 = y1 = 0.0
                    replacement = None
                    
                    # Check if we have coordinate format (8 parts) or old format (3-4 parts)
                    if len(parts) == 8:
                        # New format: PII:Type:Strategy:Page:X0:Y0:X1:Y1
                        try:
                            page_num = int(parts[3].strip())
                            x0 = float(parts[4].strip())
                            y0 = float(parts[5].strip())
                            x1 = float(parts[6].strip())
                            y1 = float(parts[7].strip())
                        except ValueError as e:
                            logger.warning(f"Invalid coordinate values in line: {line} - {e}")
                            # Continue with default coordinates
                    elif len(parts) == 4:
                        # Old format with replacement: PII:Type:Strategy:Replacement
                        replacement = parts[3].strip()
                    elif len(parts) > 8:
                        # Extended format with replacement: PII:Type:Strategy:Page:X0:Y0:X1:Y1:Replacement
                        try:
                            page_num = int(parts[3].strip())
                            x0 = float(parts[4].strip())
                            y0 = float(parts[5].strip())
                            x1 = float(parts[6].strip())
                            y1 = float(parts[7].strip())
                            if len(parts) > 8:
                                replacement = parts[8].strip()
                        except ValueError as e:
                            logger.warning(f"Invalid coordinate values in line: {line} - {e}")
                    
                    config = PIIConfig(
                        text=pii_text,
                        pii_type=pii_type,
                        strategy=strategy,
                        page_num=page_num,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        replacement=replacement
                    )
                    configs.append(config)
                    
            except Exception as e:
                logger.warning(f"Invalid config line: {line} - {e}")
        
        return configs
    
    def find_text_instances_in_page(self, page, text: str) -> List[Tuple]:
        """Find all instances of text in a PDF page and return their rectangles."""
        try:
            text_instances = page.search_for(text)
            return text_instances
        except Exception as e:
            logger.warning(f"Could not search for text '{text}': {e}")
            return []
    
    def apply_masking_strategy(self, page, rect: Tuple, pii_config: PIIConfig) -> bool:
        """
        Apply the specified masking strategy to a text rectangle in the PDF.
        
        Args:
            page: PDF page object
            rect: Rectangle coordinates (x0, y0, x1, y1) - can be None if using config coordinates
            pii_config: PII configuration with strategy and coordinates
        
        Returns:
            True if masking was successful, False otherwise
        """
        try:
            strategy = pii_config.strategy.lower()
            
            # Use coordinates from config if available, otherwise use provided rect
            if pii_config.x0 != 0.0 or pii_config.y0 != 0.0 or pii_config.x1 != 0.0 or pii_config.y1 != 0.0:
                # Use coordinates from configuration
                target_rect = (pii_config.x0, pii_config.y0, pii_config.x1, pii_config.y1)
                logger.debug(f"Using config coordinates: {target_rect}")
            elif rect:
                # Use provided rectangle
                target_rect = rect
                logger.debug(f"Using provided rectangle: {target_rect}")
            else:
                logger.error("No coordinates available for masking")
                return False
            
            if strategy == "redact":
                # Complete redaction - black box only
                redact_annot = page.add_redact_annot(target_rect)
                redact_annot.update()
                
            elif strategy in ["mask", "pseudo"]:
                # Replace with asterisks, custom text, or pseudo data
                if strategy == "mask":
                    if pii_config.replacement:
                        replacement_text = pii_config.replacement
                    else:
                        replacement_text = "*" * len(pii_config.text)
                else:  # pseudo
                    if pii_config.replacement:
                        replacement_text = pii_config.replacement
                    else:
                        replacement_text = self._get_pseudo_replacement(
                            pii_config.pii_type, pii_config.text
                        )
                
                # Use the improved text replacement method with precise coordinates
                success = self._replace_text_with_proper_formatting(page, target_rect, pii_config.text, replacement_text)
                
                if not success:
                    logger.warning(f"Text replacement failed for '{pii_config.text}', using fallback redaction")
                    # Fallback: just redact without replacement
                    redact_annot = page.add_redact_annot(target_rect)
                    redact_annot.update()
                    return False
                    redact_annot = page.add_redact_annot(rect)
                    redact_annot.update()
                    return False
                
            else:
                logger.warning(f"Unknown masking strategy: {strategy}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying masking strategy: {e}")
            return False

    def _replace_text_with_proper_formatting(self, page, rect: Tuple, original_text: str, replacement_text: str) -> bool:
        """
        Replace text in a rectangle with proper font matching and positioning.
        
        Args:
            page: PDF page object
            rect: Rectangle coordinates (x0, y0, x1, y1)
            original_text: Original text being replaced
            replacement_text: New text to insert
            
        Returns:
            True if replacement was successful, False otherwise
        """
        try:
            # Get detailed text information from the rectangle
            text_dict = page.get_text("dict", clip=rect)
            
            if not text_dict or 'blocks' not in text_dict:
                logger.debug("Could not extract text information from rectangle")
                return self._fallback_text_replacement(page, rect, replacement_text)
            
            # Find the exact text span that matches our original text
            target_span = None
            target_line = None
            
            for block in text_dict['blocks']:
                if 'lines' not in block:
                    continue
                    
                for line in block['lines']:
                    if 'spans' not in line:
                        continue
                        
                    for span in line['spans']:
                        span_text = span.get('text', '').strip()
                        # Check for exact match or if span contains our text
                        if span_text == original_text.strip() or original_text.strip() in span_text:
                            target_span = span
                            target_line = line
                            break
                    if target_span:
                        break
                if target_span:
                    break
            
            if not target_span:
                logger.debug(f"Could not find exact text span for '{original_text}'")
                return self._fallback_text_replacement(page, rect, replacement_text)
            
            # Extract font properties with better defaults
            font_size = max(target_span.get('size', 11), 8)  # Minimum font size
            font_name = target_span.get('font', 'helvetica')
            font_flags = target_span.get('flags', 0)
            text_color = target_span.get('color', 0)
            
            # Convert color from integer to RGB tuple
            if isinstance(text_color, int):
                r = (text_color >> 16) & 255
                g = (text_color >> 8) & 255
                b = text_color & 255
                color_rgb = (r/255.0, g/255.0, b/255.0)
            else:
                color_rgb = (0, 0, 0)  # default black
            
            # Use line bbox for better alignment if available
            if target_line and 'bbox' in target_line:
                line_bbox = target_line['bbox']
                x0, y0, x1, y1 = line_bbox
            else:
                # Use span bbox
                span_bbox = target_span.get('bbox', rect)
                x0, y0, x1, y1 = span_bbox
            
            # Calculate text dimensions to properly size the cover rectangle
            text_width = x1 - x0
            text_height = y1 - y0
            
            # Create a precisely sized white rectangle to cover the original text
            # Add small padding to ensure complete coverage
            padding = 1
            cover_rect = fitz.Rect(x0 - padding, y0 - padding, 
                                 x0 + text_width + padding, y1 + padding)
            
            # Draw white rectangle to cover original text
            page.draw_rect(cover_rect, color=None, fill=(1, 1, 1), width=0)
            
            # Calculate proper baseline position
            # The baseline is typically at about 20-25% from the bottom of the text height
            baseline_offset = font_size * 0.22
            baseline_y = y1 - baseline_offset
            
            # Position text at the left edge with small offset
            insert_x = x0 + 0.5  # Small offset from left edge
            insert_point = fitz.Point(insert_x, baseline_y)
            
            # Get proper font name based on flags
            fontname = self._get_proper_fontname(font_name, font_flags)
            
            # Insert the replacement text with exact formatting
            try:
                page.insert_text(
                    insert_point,
                    replacement_text,
                    fontsize=font_size,
                    fontname=fontname,
                    color=color_rgb,
                    render_mode=0  # fill text
                )
                
                logger.debug(f"Successfully replaced '{original_text}' with '{replacement_text}' "
                           f"using font: {fontname}, size: {font_size}, at position: ({insert_x:.1f}, {baseline_y:.1f})")
                
                return True
                
            except Exception as e:
                logger.debug(f"Text insertion failed: {e}, trying with default font")
                # Try with default font
                page.insert_text(
                    insert_point,
                    replacement_text,
                    fontsize=font_size,
                    fontname="helvetica",
                    color=color_rgb
                )
                return True
            
        except Exception as e:
            logger.debug(f"Detailed text replacement failed: {e}")
            return self._fallback_text_replacement(page, rect, replacement_text)
    
    def _fallback_text_replacement(self, page, rect: Tuple, replacement_text: str) -> bool:
        """
        Fallback method for text replacement when detailed analysis fails.
        Uses simpler but more reliable approach.
        """
        try:
            # Get basic font properties
            font_size, font_name = self._get_font_properties(page, rect)
            
            x0, y0, x1, y1 = rect
            text_width = x1 - x0
            text_height = y1 - y0
            
            # Create a properly sized white rectangle to cover original text
            # Use the exact rectangle dimensions with minimal padding
            padding = 0.5
            cover_rect = fitz.Rect(x0 - padding, y0 - padding, x1 + padding, y1 + padding)
            page.draw_rect(cover_rect, color=None, fill=(1, 1, 1), width=0)
            
            # Calculate proper text positioning
            # Use a more accurate baseline calculation
            if font_size > 0:
                baseline_offset = font_size * 0.23  # More accurate baseline ratio
            else:
                baseline_offset = text_height * 0.25  # Fallback based on rect height
            
            # Position text slightly inward from the left edge
            insert_x = x0 + 0.5
            insert_y = y1 - baseline_offset
            
            insert_point = fitz.Point(insert_x, insert_y)
            
            # Use a reliable font name
            safe_font_name = "helvetica"  # Always available in PyMuPDF
            if font_name and font_name.lower() in ['times', 'courier']:
                safe_font_name = font_name.lower()
            
            # Insert replacement text with conservative settings
            page.insert_text(
                insert_point,
                replacement_text,
                fontsize=max(font_size, 9),  # Minimum readable size
                fontname=safe_font_name,
                color=(0, 0, 0),  # Always black for readability
                render_mode=0
            )
            
            logger.debug(f"Applied fallback text replacement: '{replacement_text}' "
                        f"at ({insert_x:.1f}, {insert_y:.1f}) with font: {safe_font_name}, size: {font_size}")
            return True
            
        except Exception as e:
            logger.error(f"Fallback text replacement failed: {e}")
            return False
    
    def _get_proper_fontname(self, original_font: str, font_flags: int) -> str:
        """
        Convert original font name to a proper PyMuPDF font name based on flags.
        
        Args:
            original_font: Original font name from PDF
            font_flags: Font flags indicating style (bold, italic, etc.)
        
        Returns:
            Proper font name for PyMuPDF
        """
        # Font flags meanings:
        # 16 = bold
        # 2 = italic
        # 18 = bold + italic
        
        is_bold = bool(font_flags & 16)
        is_italic = bool(font_flags & 2)
        
        # Map common fonts to PyMuPDF equivalents
        font_lower = original_font.lower()
        
        if 'helvetica' in font_lower or 'arial' in font_lower:
            if is_bold and is_italic:
                return "helv-boldoblique"
            elif is_bold:
                return "helv-bold"
            elif is_italic:
                return "helv-oblique"
            else:
                return "helvetica"
        
        elif 'times' in font_lower:
            if is_bold and is_italic:
                return "times-bolditalic"
            elif is_bold:
                return "times-bold"
            elif is_italic:
                return "times-italic"
            else:
                return "times-roman"
        
        elif 'courier' in font_lower:
            if is_bold and is_italic:
                return "cour-boldoblique"
            elif is_bold:
                return "cour-bold"
            elif is_italic:
                return "cour-oblique"
            else:
                return "courier"
        
        else:
            # Default to helvetica variants
            if is_bold and is_italic:
                return "helv-boldoblique"
            elif is_bold:
                return "helv-bold"
            elif is_italic:
                return "helv-oblique"
            else:
                return "helvetica"
    
    def _get_font_properties(self, page, rect: Tuple) -> Tuple[float, str]:
        """Extract font properties from the text in the given rectangle."""
        try:
            # Get text dictionary for the rectangle area
            text_dict = page.get_text("dict", clip=rect)
            
            font_size = 11.0  # default
            font_name = "helvetica"  # default
            
            if text_dict and 'blocks' in text_dict:
                for block in text_dict['blocks']:
                    if 'lines' in block:
                        for line in block['lines']:
                            if 'spans' in line:
                                for span in line['spans']:
                                    if 'size' in span and span['size'] > 0:
                                        font_size = span['size']
                                    if 'font' in span and span['font']:
                                        # Get proper font name
                                        original_font = span['font']
                                        font_flags = span.get('flags', 0)
                                        font_name = self._get_proper_fontname(original_font, font_flags)
                                    # Use the first valid font properties found
                                    if font_size > 0:
                                        return font_size, font_name
            
            return font_size, font_name
            
        except Exception as e:
            logger.debug(f"Could not extract font properties: {e}")
            return 11.0, "helvetica"  # fallback defaults
    
    def mask_pdf_with_config(self, input_pdf_path: str, output_pdf_path: str, 
                           pii_configs: List[PIIConfig]) -> Dict[str, Any]:
        """
        Process a PDF file and mask PII according to the provided configuration.
        
        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path to output masked PDF file
            pii_configs: List of PII configurations
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "total_pages": 0,
            "total_pii_masked": 0,
            "strategies_used": {},
            "pages_processed": 0,
            "failed_maskings": 0
        }
        
        try:
            # Open the PDF
            doc = fitz.open(input_pdf_path)
            stats["total_pages"] = len(doc)
            
            logger.info(f"Processing PDF: {input_pdf_path} ({stats['total_pages']} pages)")
            logger.info(f"PII configurations to apply: {len(pii_configs)}")
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                if not page_text.strip():
                    logger.debug(f"Page {page_num + 1}: No text found, skipping")
                    continue
                
                page_masked_count = 0
                
                # Apply each PII configuration
                for pii_config in pii_configs:
                    # Skip if this PII is not on the current page
                    if pii_config.page_num != page_num:
                        continue
                    
                    # Check if we have coordinates in the config
                    if (pii_config.x0 != 0.0 or pii_config.y0 != 0.0 or 
                        pii_config.x1 != 0.0 or pii_config.y1 != 0.0):
                        # Use coordinates from config - no need to search
                        success = self.apply_masking_strategy(page, None, pii_config)
                        
                        if success:
                            page_masked_count += 1
                            stats["total_pii_masked"] += 1
                            
                            # Update strategy statistics
                            strategy = pii_config.strategy
                            if strategy not in stats["strategies_used"]:
                                stats["strategies_used"][strategy] = 0
                            stats["strategies_used"][strategy] += 1
                            
                            logger.info(f"Page {page_num + 1}: Masked '{pii_config.text}' "
                                      f"({pii_config.pii_type}) at coordinates ({pii_config.x0:.1f}, {pii_config.y0:.1f}) "
                                      f"with {strategy} strategy")
                        else:
                            stats["failed_maskings"] += 1
                    else:
                        # Fallback: search for text instances (old method)
                        text_instances = self.find_text_instances_in_page(page, pii_config.text)
                        
                        if not text_instances:
                            logger.warning(f"PII '{pii_config.text}' not found on page {page_num + 1}")
                            continue
                        
                        # Apply masking strategy to each instance
                        for rect in text_instances:
                            success = self.apply_masking_strategy(page, rect, pii_config)
                            
                            if success:
                                page_masked_count += 1
                                stats["total_pii_masked"] += 1
                                
                                # Update strategy statistics
                                strategy = pii_config.strategy
                                if strategy not in stats["strategies_used"]:
                                    stats["strategies_used"][strategy] = 0
                                stats["strategies_used"][strategy] += 1
                                
                                logger.info(f"Page {page_num + 1}: Masked '{pii_config.text}' "
                                          f"({pii_config.pii_type}) with {strategy} strategy")
                            else:
                                stats["failed_maskings"] += 1
                
                if page_masked_count > 0:
                    # Apply redactions only for 'redact' strategy, others are already processed
                    try:
                        page.apply_redactions()
                        stats["pages_processed"] += 1
                        logger.info(f"Page {page_num + 1}: Applied {page_masked_count} maskings")
                    except Exception as e:
                        logger.warning(f"Error applying redactions on page {page_num + 1}: {e}")
                        stats["pages_processed"] += 1  # Still count as processed
            
            # Save the masked PDF
            doc.save(output_pdf_path)
            doc.close()
            
            logger.info(f"✓ Masked PDF saved to: {output_pdf_path}")
            logger.info(f"✓ Statistics: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def generate_masking_report(self, stats: Dict[str, Any], pii_configs: List[PIIConfig], 
                              output_path: Optional[str] = None) -> str:
        """Generate a detailed report of the PII masking process."""
        report_lines = [
            "BERT PII Masking Report",
            "=" * 50,
            f"Total pages processed: {stats['pages_processed']}/{stats['total_pages']}",
            f"Total PII instances masked: {stats['total_pii_masked']}",
            f"Failed maskings: {stats['failed_maskings']}",
            f"PII configurations applied: {len(pii_configs)}",
            "",
            "Masking Strategies Used:",
            "-" * 30
        ]
        
        for strategy, count in stats["strategies_used"].items():
            report_lines.append(f"{strategy}: {count} instances")
        
        report_lines.extend([
            "",
            "PII Configurations Applied:",
            "-" * 40
        ])
        
        for config in pii_configs:
            replacement_info = f" -> {config.replacement}" if config.replacement else ""
            report_lines.append(f"'{config.text}' ({config.pii_type}) : {config.strategy}{replacement_info}")
        
        if self.used_mappings:
            report_lines.extend([
                "",
                "Pseudo Replacements Generated:",
                "-" * 40
            ])
            for original, replacement in self.used_mappings.items():
                report_lines.append(f"'{original}' -> '{replacement}'")
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_path}")
        
        return report
    
    def interactive_mode(self, input_pdf_path: str) -> List[PIIConfig]:
        """
        Interactive mode to configure PII masking strategies.
        
        Args:
            input_pdf_path: Path to input PDF for PII detection
            
        Returns:
            List of PII configurations
        """
        print("\n" + "="*60)
        print("INTERACTIVE PII MASKING CONFIGURATION")
        print("="*60)
        
        # First, detect PII using BERT
        try:
            doc = fitz.open(input_pdf_path)
            all_text = ""
            for page_num in range(len(doc)):
                page_text = doc[page_num].get_text()
                all_text += page_text + "\n"
            doc.close()
            
            print("Detecting PII using BERT model...")
            detected_entities = self.detect_pii_with_bert(all_text)
            
            if not detected_entities:
                print("No PII detected in the document.")
                return []
            
            print(f"\nDetected {len(detected_entities)} PII entities:")
            print("-" * 50)
            
            configs = []
            
            for i, entity in enumerate(detected_entities, 1):
                print(f"\n{i}. Text: '{entity['word']}'")
                print(f"   Type: {entity['entity_group']}")
                print(f"   Confidence: {entity['score']:.2f}")
                
                # Ask user for masking strategy
                print("   Masking strategies:")
                print("   1. redact - Complete redaction (black box)")
                print("   2. mask - Replace with asterisks")
                print("   3. pseudo - Replace with pseudo data")
                print("   4. skip - Don't mask this PII")
                
                while True:
                    choice = input("   Choose strategy (1-4): ").strip()
                    if choice == "1":
                        strategy = "redact"
                        break
                    elif choice == "2":
                        strategy = "mask"
                        break
                    elif choice == "3":
                        strategy = "pseudo"
                        break
                    elif choice == "4":
                        print("   Skipping this PII...")
                        strategy = None
                        break
                    else:
                        print("   Invalid choice. Please enter 1, 2, 3, or 4.")
                
                if strategy:
                    # Ask for custom replacement if needed
                    replacement = None
                    if strategy in ["mask", "pseudo"]:
                        custom = input("   Custom replacement (press Enter for default): ").strip()
                        if custom:
                            replacement = custom
                    
                    config = PIIConfig(
                        text=entity['word'],
                        pii_type=entity['entity_group'],
                        strategy=strategy,
                        replacement=replacement
                    )
                    configs.append(config)
            
            print(f"\nConfigured {len(configs)} PII entities for masking.")
            return configs
            
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            return []

def create_sample_config_file():
    """Create a sample configuration file for reference."""
    sample_config = """# PII Masking Configuration File
# Format: PII_TEXT:TYPE:STRATEGY[:CUSTOM_REPLACEMENT]
# 
# Strategies:
#   redact - Complete redaction (black box)
#   mask - Replace with asterisks
#   pseudo - Replace with pseudo data
#
# Examples:
John Doe:PERSON:pseudo
jane.smith@email.com:EMAIL:mask
555-123-4567:PHONE:redact
123-45-6789:SSN:mask:XXX-XX-XXXX
"""
    
    config_path = "sample_pii_config.txt"
    with open(config_path, 'w') as f:
        f.write(sample_config)
    
    logger.info(f"Sample configuration file created: {config_path}")
    return config_path

def main():
    """Main function for command-line usage."""
    print("BERT PII Masker with Configurable Strategies")
    print("=" * 60)
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python bert_pii_masker.py <input.pdf> <output.pdf> <config_file>")
        print("  python bert_pii_masker.py <input.pdf> <output.pdf> --interactive")
        print("  python bert_pii_masker.py --sample-config")
        print("")
        print("Examples:")
        print("  python bert_pii_masker.py document.pdf masked.pdf pii_config.txt")
        print("  python bert_pii_masker.py document.pdf masked.pdf --interactive")
        return 1
    
    if sys.argv[1] == "--sample-config":
        create_sample_config_file()
        return 0
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    
    if not os.path.exists(input_pdf):
        print(f"Error: Input file '{input_pdf}' not found")
        return 1
    
    if not input_pdf.lower().endswith('.pdf'):
        print(f"Error: Input file must be a PDF")
        return 1
    
    try:
        # Initialize the masker
        masker = BERTPIIMasker()
        
        # Get PII configurations
        if len(sys.argv) > 3 and sys.argv[3] == "--interactive":
            # Interactive mode
            pii_configs = masker.interactive_mode(input_pdf)
        elif len(sys.argv) > 3:
            # Configuration file mode
            config_input = sys.argv[3]
            pii_configs = masker.parse_pii_config(config_input)
        else:
            print("Error: Please provide configuration file or use --interactive mode")
            return 1
        
        if not pii_configs:
            print("No PII configurations found. Exiting.")
            return 1
        
        # Process the PDF
        print(f"\nProcessing PDF with {len(pii_configs)} PII configurations...")
        stats = masker.mask_pdf_with_config(input_pdf, output_pdf, pii_configs)
        
        # Generate and save report
        report_path = output_pdf.replace('.pdf', '_masking_report.txt')
        report = masker.generate_masking_report(stats, pii_configs, report_path)
        
        # Display summary
        print("\n" + "="*60)
        print("PII MASKING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Input PDF: {input_pdf}")
        print(f"Output PDF: {output_pdf}")
        print(f"Report: {report_path}")
        print("\nSummary:")
        print(f"  • Pages processed: {stats['pages_processed']}/{stats['total_pages']}")
        print(f"  • PII instances masked: {stats['total_pii_masked']}")
        print(f"  • Failed maskings: {stats['failed_maskings']}")
        
        if stats['strategies_used']:
            print("\nStrategies Used:")
            for strategy, count in stats['strategies_used'].items():
                print(f"  • {strategy}: {count} instances")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
