#!/usr/bin/env python3
"""
PII Detection and Configuration Generator

This script detects PII in PDF documents and generates configuration files
that can be used with bert_pii_masker.py for applying masking strategies.

The script uses BERT NER model and regex patterns to detect various types of PII
and outputs them in the format: PII_TEXT:TYPE:STRATEGY

Usage:
    python pii_detector_config_generator.py input.pdf [output_config.txt]
    python pii_detector_config_generator.py input.pdf --interactive
"""

import sys
import os
import re
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
class DetectedPII:
    """Represents a detected PII entity with coordinates."""
    text: str
    pii_type: str
    confidence: float
    start: int
    end: int
    page_num: int
    suggested_strategy: str = "redact"
    # PDF coordinates (x0, y0, x1, y1)
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0

class PIIDetectorConfigGenerator:
    """
    PII detection system that generates configuration files for bert_pii_masker.py
    """
    
    def __init__(self):
        self.ner_pipeline = None
        self.custom_patterns = self._get_custom_patterns()
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
            logger.warning("Transformers not installed. Using regex patterns only.")
            logger.warning("For better detection, install: pip install transformers torch")
            self.ner_pipeline = None
        except Exception as e:
            logger.warning(f"Failed to load BERT model: {e}")
            logger.warning("Falling back to regex patterns only")
            self.ner_pipeline = None
    
    def _get_custom_patterns(self) -> Dict[str, List[str]]:
        """Define custom regex patterns for PII detection."""
        return {
            "SSN": [
                r"\b\d{3}-\d{2}-\d{4}\b",          # XXX-XX-XXXX
                r"\b\d{3}\s\d{2}\s\d{4}\b",        # XXX XX XXXX
                r"\b\d{9}\b"                        # XXXXXXXXX (context dependent)
            ],
            "PHONE": [
                r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                r"\b\d{3}-\d{3}-\d{4}\b",
                r"\(\d{3}\)\s?\d{3}-\d{4}",
                r"\+91[-.\s]?\d{10}\b",             # Indian phone numbers
                r"\b[6-9]\d{9}\b"                   # Indian mobile numbers
            ],
            "EMAIL": [
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            ],
            "CREDIT_CARD": [
                r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
            ],
            "BANK_ACCOUNT": [
                r"\b\d{9,18}\b",                    # General bank account patterns
                r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b"  # IBAN format
            ],
            "AADHAAR": [
                r"\b\d{4}\s\d{4}\s\d{4}\b",       # XXXX XXXX XXXX format
                r"\b\d{12}\b"                      # 12 consecutive digits (context dependent)
            ],
            "PAN": [
                r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"      # ABCDE1234F format
            ],
            "INDIAN_VOTER_ID": [
                r"\b[A-Z]{3}\d{7}\b",             # ABC1234567 format
                r"\b[A-Z]{2}\d{8}\b"              # AB12345678 format
            ],
            "ZIP_CODE": [
                r"\b\d{5}(?:-\d{4})?\b",          # US ZIP codes
                r"\b\d{6}\b"                       # Indian PIN codes (context dependent)
            ],
            "DATE_OF_BIRTH": [
                r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",  # MM/DD/YYYY
                r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b",  # DD/MM/YYYY
                r"\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b",  # YYYY/MM/DD
            ],
            "ADDRESS": [
                r"\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b",
                r"\b\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}\b"  # Full address format
            ]
        }
    
    def _suggest_masking_strategy(self, pii_type: str, text: str) -> str:
        """Suggest an appropriate masking strategy based on PII type and context."""
        # High-sensitivity PII - recommend redaction
        if pii_type in ["SSN", "CREDIT_CARD", "BANK_ACCOUNT", "AADHAAR"]:
            return "redact"
        
        # Names and organizations - recommend pseudo replacement
        elif pii_type in ["PERSON", "ORG"]:
            return "pseudo"
        
        # Contact information - recommend masking
        elif pii_type in ["EMAIL", "PHONE"]:
            return "mask"
        
        # Addresses and locations - recommend pseudo replacement
        elif pii_type in ["ADDRESS", "LOC"]:
            return "pseudo"
        
        # Dates - recommend masking to preserve format
        elif pii_type in ["DATE_OF_BIRTH", "DATE"]:
            return "mask"
        
        # Default to redaction for unknown types
        else:
            return "redact"
    
    def detect_pii_with_bert(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using BERT NER model."""
        if not self.ner_pipeline:
            return []
        
        try:
            entities = self.ner_pipeline(text)
            
            # Filter and process entities
            filtered_entities = []
            for entity in entities:
                if self._is_valid_bert_entity(entity):
                    # Map BERT entity types to our PII types
                    pii_type = self._map_bert_entity_type(entity['entity_group'])
                    
                    filtered_entities.append({
                        "text": entity['word'],
                        "pii_type": pii_type,
                        "start": entity['start'],
                        "end": entity['end'],
                        "confidence": entity['score'],
                        "source": "BERT"
                    })
            
            return filtered_entities
            
        except Exception as e:
            logger.error(f"Error in BERT PII detection: {e}")
            return []
    
    def _is_valid_bert_entity(self, entity: Dict[str, Any]) -> bool:
        """Filter out false positives from BERT detection."""
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
            'advisor', 'custom', 'level', 'face', 'pan', 'act', 'boom',
            'us', 'new', 'state', 'american', 'america'
        }
        
        if word.lower() in non_pii_terms:
            return False
        
        # Only allow relevant entity types
        allowed_types = {'PER', 'ORG', 'LOC', 'MISC'}
        return entity_type in allowed_types
    
    def _map_bert_entity_type(self, bert_type: str) -> str:
        """Map BERT entity types to our PII types."""
        mapping = {
            'PER': 'PERSON',
            'ORG': 'ORG',
            'LOC': 'LOC',
            'MISC': 'MISC'
        }
        return mapping.get(bert_type, bert_type)
    
    def detect_pii_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using regex patterns."""
        entities = []
        
        for pii_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Additional validation for context-dependent patterns
                    if self._validate_regex_match(match.group(), pii_type, text, match.start()):
                        entities.append({
                            "text": match.group(),
                            "pii_type": pii_type,
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": 0.9,
                            "source": "REGEX"
                        })
        
        return entities
    
    def _validate_regex_match(self, text: str, pii_type: str, full_text: str, position: int) -> bool:
        """Validate regex matches using context."""
        # For 9-digit numbers, check if they might be SSNs
        if pii_type == "SSN" and len(text) == 9 and text.isdigit():
            # Look for SSN context keywords nearby
            context_window = 50
            start = max(0, position - context_window)
            end = min(len(full_text), position + len(text) + context_window)
            context = full_text[start:end].lower()
            
            ssn_keywords = ['ssn', 'social security', 'social security number', 'tax id']
            return any(keyword in context for keyword in ssn_keywords)
        
        # For 12-digit numbers, check if they might be Aadhaar
        elif pii_type == "AADHAAR" and len(text) == 12 and text.isdigit():
            context_window = 50
            start = max(0, position - context_window)
            end = min(len(full_text), position + len(text) + context_window)
            context = full_text[start:end].lower()
            
            aadhaar_keywords = ['aadhaar', 'aadhar', 'uid', 'unique id']
            return any(keyword in context for keyword in aadhaar_keywords)
        
        # For 6-digit numbers, check if they might be PIN codes
        elif pii_type == "ZIP_CODE" and len(text) == 6 and text.isdigit():
            context_window = 30
            start = max(0, position - context_window)
            end = min(len(full_text), position + len(text) + context_window)
            context = full_text[start:end].lower()
            
            pin_keywords = ['pin', 'pincode', 'postal code', 'zip']
            return any(keyword in context for keyword in pin_keywords)
        
        return True
    
    def merge_and_deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge overlapping entities and remove duplicates."""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: x["start"])
        merged = []
        
        for current in sorted_entities:
            # Check if this entity overlaps with any existing entity
            merged_with_existing = False
            
            for i, existing in enumerate(merged):
                # Check for overlap
                if (current["start"] < existing["end"] and current["end"] > existing["start"]):
                    # Entities overlap - keep the one with higher confidence or more specific type
                    if (current["confidence"] > existing["confidence"] or 
                        self._is_more_specific_type(current["pii_type"], existing["pii_type"])):
                        # Replace existing with current
                        merged[i] = current
                    merged_with_existing = True
                    break
            
            if not merged_with_existing:
                merged.append(current)
        
        return merged
    
    def _is_more_specific_type(self, type1: str, type2: str) -> bool:
        """Determine if type1 is more specific than type2."""
        # Regex-detected specific types are generally more accurate than BERT's general types
        specific_types = {"SSN", "EMAIL", "PHONE", "CREDIT_CARD", "AADHAAR", "PAN"}
        general_types = {"PERSON", "ORG", "LOC", "MISC"}
        
        return type1 in specific_types and type2 in general_types
    
    def detect_all_pii(self, text: str, page_num: int = 0, doc: fitz.Document = None) -> List[DetectedPII]:
        """Detect all PII using both BERT and regex methods, including coordinates."""
        all_entities = []
        
        # Detect with BERT
        if self.ner_pipeline:
            bert_entities = self.detect_pii_with_bert(text)
            all_entities.extend(bert_entities)
            logger.debug(f"BERT detected {len(bert_entities)} entities on page {page_num + 1}")
        
        # Detect with regex
        regex_entities = self.detect_pii_with_regex(text)
        all_entities.extend(regex_entities)
        logger.debug(f"Regex detected {len(regex_entities)} entities on page {page_num + 1}")
        
        # Merge and deduplicate
        merged_entities = self.merge_and_deduplicate_entities(all_entities)
        
        # Convert to DetectedPII objects with coordinates
        detected_pii = []
        for entity in merged_entities:
            # Find coordinates if document is provided
            x0, y0, x1, y1 = 0.0, 0.0, 0.0, 0.0
            if doc:
                x0, y0, x1, y1 = self.find_text_coordinates(
                    doc, page_num, entity["text"], 
                    entity["start"], entity["end"]
                )
            
            pii = DetectedPII(
                text=entity["text"],
                pii_type=entity["pii_type"],
                confidence=entity["confidence"],
                start=entity["start"],
                end=entity["end"],
                page_num=page_num,
                suggested_strategy=self._suggest_masking_strategy(entity["pii_type"], entity["text"]),
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1
            )
            detected_pii.append(pii)
        
        logger.info(f"Page {page_num + 1}: Found {len(detected_pii)} unique PII entities with coordinates")
        return detected_pii
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Tuple[str, int]]:
        """Extract text from PDF pages."""
        try:
            doc = fitz.open(pdf_path)
            pages_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                pages_text.append((page_text, page_num))
            
            doc.close()
            return pages_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def extract_text_with_coordinates(self, pdf_path: str) -> List[Tuple[str, int, fitz.Document]]:
        """
        Extract text from PDF pages while keeping the document open for coordinate lookup.
        Returns: List of (page_text, page_num, document)
        """
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                pages_data.append((page_text, page_num, doc))
            
            return pages_data
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def find_text_coordinates(self, doc: fitz.Document, page_num: int, text: str, start_char: int, end_char: int) -> Tuple[float, float, float, float]:
        """
        Find the exact coordinates of text on a PDF page.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-indexed)
            text: Text to find
            start_char: Character start position in page text
            end_char: Character end position in page text
            
        Returns:
            Tuple of (x0, y0, x1, y1) coordinates
        """
        try:
            page = doc[page_num]
            
            # Method 1: Direct text search
            text_instances = page.search_for(text)
            if text_instances:
                # Return the first match (most likely correct)
                rect = text_instances[0]
                return (rect.x0, rect.y0, rect.x1, rect.y1)
            
            # Method 2: Use text blocks to find approximate position
            blocks = page.get_text("dict")
            
            current_char = 0
            target_start = start_char
            target_end = end_char
            
            for block in blocks.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    line_spans = []
                    
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        line_text += span_text
                        line_spans.append((span, current_char, current_char + len(span_text)))
                        current_char += len(span_text)
                    
                    # Add newline character
                    current_char += 1
                    
                    # Check if our target text falls within this line
                    if target_start < current_char and target_end <= current_char:
                        # Find the specific span(s) containing our text
                        for span, span_start, span_end in line_spans:
                            if (target_start >= span_start and target_start < span_end) or \
                               (target_end > span_start and target_end <= span_end):
                                # Found the span containing our text
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                return (bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Method 3: Fallback - return approximate coordinates based on page size
            logger.warning(f"Could not find exact coordinates for text: '{text}'")
            page_rect = page.rect
            return (50, 50, page_rect.width - 50, 80)  # Default rectangle
            
        except Exception as e:
            logger.warning(f"Error finding coordinates for text '{text}': {e}")
            # Return safe default coordinates
            return (50, 50, 200, 80)
    
    def generate_config_file(self, detected_pii: List[DetectedPII], output_path: str, 
                           interactive: bool = False) -> Dict[str, Any]:
        """Generate configuration file for bert_pii_masker.py"""
        
        if interactive:
            detected_pii = self._interactive_strategy_selection(detected_pii)
        
        # Remove duplicates while preserving order
        unique_pii = []
        seen_texts = set()
        
        for pii in detected_pii:
            if pii.text not in seen_texts:
                unique_pii.append(pii)
                seen_texts.add(pii.text)
        
        config_lines = [
            "# PII Masking Configuration File with Coordinates",
            "# Generated by PII Detector Config Generator",
            "# Format: PII_TEXT:TYPE:STRATEGY:PAGE:X0:Y0:X1:Y1",
            "#",
            "# Where:",
            "#   PII_TEXT - The detected PII text",
            "#   TYPE - Type of PII (PERSON, EMAIL, etc.)",
            "#   STRATEGY - Masking strategy (redact, mask, pseudo)",
            "#   PAGE - Page number (0-indexed)",
            "#   X0,Y0,X1,Y1 - Bounding box coordinates",
            "#",
            "# Strategies:",
            "#   redact - Complete redaction (black box)",
            "#   mask - Replace with asterisks or patterns",
            "#   pseudo - Replace with realistic fake data",
            "#",
            ""
        ]
        
        stats = {
            "total_pii": len(unique_pii),
            "strategies": {},
            "types": {}
        }
        
        for pii in unique_pii:
            # Format: PII_TEXT:TYPE:STRATEGY:PAGE:X0:Y0:X1:Y1
            config_line = f"{pii.text}:{pii.pii_type}:{pii.suggested_strategy}:{pii.page_num}:{pii.x0:.2f}:{pii.y0:.2f}:{pii.x1:.2f}:{pii.y1:.2f}"
            config_lines.append(config_line)
            
            # Update statistics
            if pii.suggested_strategy not in stats["strategies"]:
                stats["strategies"][pii.suggested_strategy] = 0
            stats["strategies"][pii.suggested_strategy] += 1
            
            if pii.pii_type not in stats["types"]:
                stats["types"][pii.pii_type] = 0
            stats["types"][pii.pii_type] += 1
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(config_lines))
        
        logger.info(f"Configuration file saved to: {output_path}")
        return stats
    
    def _interactive_strategy_selection(self, detected_pii: List[DetectedPII]) -> List[DetectedPII]:
        """Allow user to interactively select masking strategies."""
        print("\n" + "="*60)
        print("INTERACTIVE STRATEGY SELECTION")
        print("="*60)
        print("Review detected PII and choose masking strategies:")
        print()
        
        updated_pii = []
        
        for i, pii in enumerate(detected_pii, 1):
            print(f"{i}. Text: '{pii.text}'")
            print(f"   Type: {pii.pii_type}")
            print(f"   Page: {pii.page_num + 1}")
            print(f"   Confidence: {pii.confidence:.2f}")
            print(f"   Coordinates: ({pii.x0:.1f}, {pii.y0:.1f}) to ({pii.x1:.1f}, {pii.y1:.1f})")
            print(f"   Suggested Strategy: {pii.suggested_strategy}")
            print()
            print("   Available strategies:")
            print("   1. redact - Complete redaction (black box)")
            print("   2. mask - Replace with asterisks/patterns")
            print("   3. pseudo - Replace with realistic fake data")
            print("   4. skip - Don't mask this PII")
            print()
            
            while True:
                choice = input(f"   Choose strategy for '{pii.text}' (1-4, or Enter for suggested): ").strip()
                
                if choice == "" or choice == "1":
                    if choice == "":
                        strategy = pii.suggested_strategy
                    else:
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
                    print("   Invalid choice. Please enter 1, 2, 3, 4, or press Enter.")
            
            if strategy:
                pii.suggested_strategy = strategy
                updated_pii.append(pii)
            
            print("-" * 60)
        
        print(f"\nSelected {len(updated_pii)} PII entities for masking.")
        return updated_pii
    
    def process_pdf(self, pdf_path: str, output_config_path: str, interactive: bool = False) -> Dict[str, Any]:
        """Process PDF and generate configuration file with coordinates."""
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text from PDF with coordinate capability
        pages_data = self.extract_text_with_coordinates(pdf_path)
        
        # Detect PII in all pages with coordinates
        all_detected_pii = []
        doc = None
        
        try:
            for page_text, page_num, document in pages_data:
                doc = document  # Keep reference to document for coordinate lookup
                if page_text.strip():
                    page_pii = self.detect_all_pii(page_text, page_num, doc)
                    all_detected_pii.extend(page_pii)
            
            if not all_detected_pii:
                logger.warning("No PII detected in the document")
                return {"total_pii": 0, "strategies": {}, "types": {}}
            
            # Generate configuration file with coordinates
            stats = self.generate_config_file(all_detected_pii, output_config_path, interactive)
            
            return stats
            
        finally:
            # Close the document
            if doc:
                doc.close()
    
    def generate_detection_report(self, stats: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate a detailed report of PII detection."""
        report_lines = [
            "PII Detection Report",
            "=" * 40,
            f"Total PII entities detected: {stats['total_pii']}",
            "",
            "PII Types Found:",
            "-" * 20
        ]
        
        for pii_type, count in stats["types"].items():
            report_lines.append(f"{pii_type}: {count}")
        
        report_lines.extend([
            "",
            "Suggested Strategies:",
            "-" * 20
        ])
        
        for strategy, count in stats["strategies"].items():
            report_lines.append(f"{strategy}: {count}")
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Detection report saved to: {output_path}")
        
        return report

def main():
    """Main function for command-line usage."""
    print("PII Detection and Configuration Generator")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python pii_detector_config_generator.py <input.pdf> [output_config.txt]")
        print("  python pii_detector_config_generator.py <input.pdf> --interactive")
        print("")
        print("Examples:")
        print("  python pii_detector_config_generator.py document.pdf config.txt")
        print("  python pii_detector_config_generator.py document.pdf --interactive")
        return 1
    
    input_pdf = sys.argv[1]
    
    if not os.path.exists(input_pdf):
        print(f"Error: Input file '{input_pdf}' not found")
        return 1
    
    if not input_pdf.lower().endswith('.pdf'):
        print(f"Error: Input file must be a PDF")
        return 1
    
    # Determine output configuration file
    interactive_mode = False
    if len(sys.argv) > 2:
        if sys.argv[2] == "--interactive":
            interactive_mode = True
            output_config = input_pdf.replace('.pdf', '_pii_config.txt')
        else:
            output_config = sys.argv[2]
    else:
        output_config = input_pdf.replace('.pdf', '_pii_config.txt')
    
    try:
        # Initialize detector
        detector = PIIDetectorConfigGenerator()
        
        # Process PDF
        stats = detector.process_pdf(input_pdf, output_config, interactive_mode)
        
        if stats["total_pii"] == 0:
            print("\n✓ No PII detected in the document.")
            return 0
        
        # Generate detection report
        report_path = output_config.replace('.txt', '_detection_report.txt')
        report = detector.generate_detection_report(stats, report_path)
        
        # Display summary
        print("\n" + "="*50)
        print("PII DETECTION COMPLETED!")
        print("="*50)
        print(f"Input PDF: {input_pdf}")
        print(f"Configuration file: {output_config}")
        print(f"Detection report: {report_path}")
        print("\nSummary:")
        print(f"  • Total PII detected: {stats['total_pii']}")
        
        if stats['types']:
            print("\nPII Types Found:")
            for pii_type, count in stats['types'].items():
                print(f"  • {pii_type}: {count}")
        
        if stats['strategies']:
            print("\nSuggested Strategies:")
            for strategy, count in stats['strategies'].items():
                print(f"  • {strategy}: {count}")
        
        print(f"\nNext step:")
        print(f"python bert_pii_masker.py {input_pdf} masked_output.pdf {output_config}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
