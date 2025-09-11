#!/usr/bin/env python3
"""
PII Masking Script for PDF Documents

This         self.pii_entities = {
            # Direct & Universal Identifiers
            "PERSON",                    # Personal Identification: Full names
            "US_SSN",                    # Social Security Numbers
            "SSN",                       # Social Security Numbers (alternative)
            "US_DRIVER_LICENSE",         # Driver's license numbers
            "US_PASSPORT",               # Passport numbers
            "IN_AADHAAR",               # Indian Aadhaar card numbers
            "IN_PAN",                   # Indian PAN card numbers
            
            # Contact Information
            "EMAIL_ADDRESS",             # Email addresses
            "PHONE_NUMBER",              # Telephone/fax numbers
            "LOCATION",                  # Full addresses and geographic locations
            "US_ZIP_CODE",              # ZIP codes (quasi-identifier)
            
            # Financial Information
            "CREDIT_CARD",               # Credit card numbers
            "US_BANK_NUMBER",           # Bank account numbers
            "IBAN_CODE",                # International bank account numbers
            
            # Quasi-Identifiers & Linkable Data
            "DATE_TIME",                 # Full dates of birth and other dates
            "AGE",                      # Age information
            
            # Regulatory-Specific Data
            "MEDICAL_LICENSE",           # Medical and other professional licenses
            "AU_TFN",                   # Tax file numbers (extensible)
            "AU_ABN",                   # Business numbers (extensible)
            
            # Additional Indian identifiers for DPDPA compliance
            "IN_VEHICLE_REGISTRATION",  # Indian vehicle registration
            "IN_VOTER_ID",              # Indian voter ID (if available)
        } detects and masks Personally Identifiable Information (PII) in PDF documents
while preserving the original layout and formatting. It uses open source tools for
contextually aware PII detection and redaction.

Dependencies:
- PyMuPDF (fitz): PDF processing
- spaCy: Named Entity Recognition
- presidio-analyzer: Advanced PII detection
- re: Regular expressions for pattern matching

Usage:
    python pii_masker.py input.pdf output.pdf
"""

import sys
import os
import re
import logging
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz  
    import spacy
    from spacy import displacy
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install required packages:")
    print("pip install PyMuPDF spacy presidio-analyzer")
    print("python -m spacy download en_core_web_sm")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PIIMatch:
    """Represents a detected PII entity."""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float
    page_num: int
    rect: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)

class PIIMasker:
    """
    A comprehensive PII masking system for PDF documents.
    
    Features:
    - Contextually aware PII detection
    - Multiple detection engines (spaCy, Presidio, regex patterns)
    - Layout-preserving redaction
    - Configurable masking strategies
    """
    
    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """Initialize the PII masker with required models."""
        self.spacy_model = spacy_model
        self.nlp: Optional[Any] = None
        self.analyzer: Optional[Any] = None
        self.custom_patterns = self._get_custom_patterns()
        self.pii_entities = {
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD", "AADHAR CARD", "PAN CARD"
            "IBAN_CODE", "IP_ADDRESS", "DATE_TIME", "LOCATION", "URL",
            "US_DRIVER_LICENSE", "US_PASSPORT", "MEDICAL_LICENSE",
            "US_BANK_NUMBER", "CRYPTO", "GPE", "ORG"
        }
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models and PII detection engines."""
        try:
            # Load spaCy model
            logger.info(f"Loading spaCy model: {self.spacy_model}")
            self.nlp = spacy.load(self.spacy_model)
            
            # Initialize Presidio analyzer with default configuration
            logger.info("Initializing Presidio analyzer")
            self.analyzer = AnalyzerEngine()
            
            logger.info("PII detection models initialized successfully")
            
        except OSError as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.error("Please install the model with: python -m spacy download en_core_web_sm")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PII detection models: {e}")
            raise
    
    def _get_custom_patterns(self) -> Dict[str, List[str]]:
        """Define custom regex patterns for specific PII detection requirements."""
        return {
            # Direct & Universal Identifiers
            "SSN": [
                r"\b\d{3}-\d{2}-\d{4}\b",          # XXX-XX-XXXX
                r"\b\d{3}\s\d{2}\s\d{4}\b",        # XXX XX XXXX
                r"\b\d{9}\b"                        # XXXXXXXXX
            ],
            "US_DRIVER_LICENSE": [
                r"\b[A-Z]{1,2}\d{6,8}\b",          # State format variations
                r"\b\d{8,9}\b",                     # Numeric only formats
                r"\b[A-Z]\d{7,8}\b"                 # Letter + numbers
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
            
            # Indian-Specific Identifiers (DPDPA Compliance)
            "AADHAAR": [
                r"\b\d{4}\s\d{4}\s\d{4}\b",       # XXXX XXXX XXXX format
                r"\b\d{12}\b"                      # 12 consecutive digits
            ],
            "PAN": [
                r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"      # ABCDE1234F format
            ],
            "INDIAN_VOTER_ID": [
                r"\b[A-Z]{3}\d{7}\b",             # ABC1234567 format
                r"\b[A-Z]{2}\d{8}\b"              # AB12345678 format
            ],
            "INDIAN_DRIVING_LICENSE": [
                r"\b[A-Z]{2}\d{2}\s\d{11}\b",     # State code + year + 11 digits
                r"\b[A-Z]{2}-\d{13}\b"            # Alternative format
            ],
            
            # Quasi-Identifiers
            "ZIP_CODE": [
                r"\b\d{5}(?:-\d{4})?\b",          # US ZIP codes
                r"\b\d{6}\b"                       # Indian PIN codes
            ],
            "DATE_OF_BIRTH": [
                r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",  # MM/DD/YYYY
                r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b",  # DD/MM/YYYY
                r"\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b",  # YYYY/MM/DD
                r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+(?:19|20)\d{2}\b"  # Month DD, YYYY
            ],
            "AGE": [
                r"\bage\s*:?\s*\d{1,3}\b",        # Age: XX or age XX
                r"\b\d{1,3}\s*years?\s*old\b"     # XX years old
            ],
            
            # Financial Information (Non-public Personal Information under GLBA)
            "LOAN_AMOUNT": [
                r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b",  # Currency amounts
                r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b"
            ],
            "INCOME": [
                r"\bincome\s*:?\s*\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b",
                r"\bsalary\s*:?\s*\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b"
            ],
            
            # License and Certificate Numbers
            "LICENSE_NUMBER": [
                r"\blicense\s*#?\s*:?\s*[A-Z0-9]{6,12}\b",
                r"\bcertificate\s*#?\s*:?\s*[A-Z0-9]{6,12}\b"
            ]
        }
    
    def detect_pii_with_spacy(self, text: str) -> List[Dict]:
        """Detect PII using spaCy NER."""
        if self.nlp is None:
            raise RuntimeError("spaCy model not initialized")
            
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            if ent.label_ in self.pii_entities:
                entities.append({
                    "text": ent.text,
                    "entity_type": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 0.8  # spaCy doesn't provide confidence scores
                })
        
        return entities
    
    def detect_pii_with_presidio(self, text: str) -> List[Dict]:
        """Detect PII using Presidio analyzer."""
        if self.analyzer is None:
            raise RuntimeError("Presidio analyzer not initialized")
            
        results = self.analyzer.analyze(text=text, language="en")
        
        entities = []
        for result in results:
            entities.append({
                "text": text[result.start:result.end],
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "confidence": result.score
            })
        
        return entities
    
    def detect_pii_with_regex(self, text: str) -> List[Dict]:
        """Detect PII using custom regex patterns."""
        entities = []
        
        for entity_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "text": match.group(),
                        "entity_type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9
                    })
        
        return entities
    
    def merge_overlapping_entities(self, entities: List[Dict]) -> List[Dict]:
        """Merge overlapping PII entities and remove duplicates."""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: x["start"])
        merged = [sorted_entities[0]]
        
        for current in sorted_entities[1:]:
            last = merged[-1]
            
            # Check for overlap
            if current["start"] <= last["end"]:
                # Merge entities - keep the one with higher confidence
                if current["confidence"] > last["confidence"]:
                    merged[-1] = {
                        "text": current["text"],
                        "entity_type": current["entity_type"],
                        "start": min(last["start"], current["start"]),
                        "end": max(last["end"], current["end"]),
                        "confidence": current["confidence"]
                    }
                else:
                    merged[-1]["end"] = max(last["end"], current["end"])
            else:
                merged.append(current)
        
        return merged
    
    def detect_all_pii(self, text: str, page_num: int = 0) -> List[PIIMatch]:
        """
        Detect PII using all available methods and merge results.
        
        Implements contextual, policy-driven approach that considers:
        - Direct & Universal Identifiers (high priority)
        - Quasi-Identifiers & Linkable Data (combinatorial risk assessment)
        - Regulatory-Specific Data Categories
        """
        all_entities = []
        
        try:
            # Detect with spaCy
            spacy_entities = self.detect_pii_with_spacy(text)
            all_entities.extend(spacy_entities)
            logger.debug(f"spaCy detected {len(spacy_entities)} entities")
            
            # Detect with Presidio
            presidio_entities = self.detect_pii_with_presidio(text)
            all_entities.extend(presidio_entities)
            logger.debug(f"Presidio detected {len(presidio_entities)} entities")
            
            # Detect with regex
            regex_entities = self.detect_pii_with_regex(text)
            all_entities.extend(regex_entities)
            logger.debug(f"Regex detected {len(regex_entities)} entities")
            
        except Exception as e:
            logger.warning(f"Error during PII detection: {e}")
        
        # Filter entities based on your specific requirements
        filtered_entities = self._filter_entities_by_policy(all_entities)
        
        # Merge overlapping entities
        merged_entities = self.merge_overlapping_entities(filtered_entities)
        
        # Apply linkability principle for quasi-identifiers
        risk_assessed_entities = self._assess_reidentification_risk(merged_entities, text)
        
        # Convert to PIIMatch objects
        pii_matches = []
        for entity in risk_assessed_entities:
            pii_match = PIIMatch(
                text=entity["text"],
                entity_type=entity["entity_type"],
                start=entity["start"],
                end=entity["end"],
                confidence=entity["confidence"],
                page_num=page_num
            )
            pii_matches.append(pii_match)
        
        logger.info(f"Page {page_num}: Found {len(pii_matches)} PII entities")
        return pii_matches
    
    def _filter_entities_by_policy(self, entities: List[Dict]) -> List[Dict]:
        """Filter entities based on specific PII policy requirements."""
        filtered = []
        
        for entity in entities:
            entity_type = entity["entity_type"]
            
            # Direct & Universal Identifiers - always include
            if entity_type in ["PERSON", "US_SSN", "SSN", "US_DRIVER_LICENSE", "US_PASSPORT", 
                              "IN_AADHAAR", "IN_PAN", "EMAIL_ADDRESS", "PHONE_NUMBER", 
                              "CREDIT_CARD", "US_BANK_NUMBER", "IBAN_CODE"]:
                entity["priority"] = "direct_identifier"
                filtered.append(entity)
            
            # Quasi-Identifiers - include with special handling
            elif entity_type in ["DATE_TIME", "LOCATION", "US_ZIP_CODE", "AGE"]:
                entity["priority"] = "quasi_identifier"
                filtered.append(entity)
            
            # Regulatory-Specific Data
            elif entity_type in ["MEDICAL_LICENSE", "IN_VEHICLE_REGISTRATION"]:
                entity["priority"] = "regulatory_specific"
                filtered.append(entity)
            
            # Custom patterns from regex
            elif entity_type in ["AADHAAR", "PAN", "PHONE", "EMAIL", "BANK_ACCOUNT", 
                                "ZIP_CODE", "DATE_OF_BIRTH", "LOAN_AMOUNT", "INCOME", 
                                "LICENSE_NUMBER", "INDIAN_VOTER_ID", "INDIAN_DRIVING_LICENSE"]:
                entity["priority"] = "custom_pattern"
                filtered.append(entity)
            
            # Skip entities not in our policy (like IP_ADDRESS, URL, ORG, etc.)
            else:
                logger.debug(f"Skipping entity type '{entity_type}' - not in policy")
        
        return filtered
    
    def _assess_reidentification_risk(self, entities: List[Dict], text: str) -> List[Dict]:
        """
        Assess re-identification risk using the linkability principle.
        
        Combination of quasi-identifiers increases identification risk:
        - ZIP code + race + gender + birth date can uniquely identify majority of citizens
        """
        quasi_identifiers = []
        direct_identifiers = []
        
        for entity in entities:
            if entity.get("priority") == "quasi_identifier":
                quasi_identifiers.append(entity)
            else:
                direct_identifiers.append(entity)
        
        # If we have multiple quasi-identifiers, increase their confidence
        if len(quasi_identifiers) >= 2:
            for entity in quasi_identifiers:
                # Increase confidence due to combinatorial risk
                entity["confidence"] = min(0.95, entity["confidence"] + 0.2)
                entity["risk_note"] = "High re-identification risk due to quasi-identifier combination"
                logger.info(f"Elevated risk for quasi-identifier: {entity['text']}")
        
        # Look for specific high-risk combinations
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ["loan application", "depositor", "financial", "bank"]):
            # GLBA - Non-public Personal Information context
            for entity in entities:
                if entity["entity_type"] in ["LOAN_AMOUNT", "INCOME", "BANK_ACCOUNT"]:
                    entity["confidence"] = min(0.98, entity["confidence"] + 0.15)
                    entity["regulatory_context"] = "GLBA_NPI"
        
        return direct_identifiers + quasi_identifiers
    
    def find_text_instances_in_page(self, page, text: str) -> List[Tuple]:
        """Find all instances of text in a PDF page and return their rectangles."""
        text_instances = page.search_for(text)
        return text_instances
    
    def mask_pii_in_pdf(self, input_path: str, output_path: str, mask_strategy: str = "redact") -> Dict[str, Any]:
        """
        Mask PII in a PDF document while preserving layout.
        
        Args:
            input_path: Path to input PDF
            output_path: Path to output PDF
            mask_strategy: Strategy for masking ("redact", "replace", "blur")
        
        Returns:
            Dictionary with masking statistics
        """
        stats = {
            "total_pages": 0,
            "total_pii_found": 0,
            "entities_by_type": {},
            "pages_processed": 0
        }
        
        try:
            # Open the PDF
            doc = fitz.open(input_path)
            stats["total_pages"] = len(doc)
            
            logger.info(f"Processing PDF: {input_path} ({stats['total_pages']} pages)")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text from the page
                page_text = page.get_text()
                
                if not page_text.strip():
                    logger.debug(f"Page {page_num + 1}: No text found, skipping")
                    continue
                
                # Detect PII in the page text
                pii_matches = self.detect_all_pii(page_text, page_num)
                
                if not pii_matches:
                    logger.debug(f"Page {page_num + 1}: No PII found")
                    continue
                
                # Process each PII match
                for pii_match in pii_matches:
                    # Find text instances in the page
                    text_instances = self.find_text_instances_in_page(page, pii_match.text)
                    
                    if not text_instances:
                        logger.warning(f"Could not locate text '{pii_match.text}' in page {page_num + 1}")
                        continue
                    
                    # Apply masking strategy
                    for rect in text_instances:
                        if mask_strategy == "redact":
                            # Create a redaction annotation
                            redact_annot = page.add_redact_annot(rect)
                            redact_annot.update()
                        elif mask_strategy == "replace":
                            # Replace with asterisks
                            replacement = "*" * len(pii_match.text)
                            page.add_redact_annot(rect, text=replacement)
                        elif mask_strategy == "blur":
                            # Add a semi-transparent rectangle using annotations
                            annot = page.add_rect_annot(rect)
                            annot.set_colors(fill=(0.5, 0.5, 0.5))  # Gray fill
                            annot.set_opacity(0.7)
                            annot.update()
                    
                    # Update statistics
                    stats["total_pii_found"] += 1
                    entity_type = pii_match.entity_type
                    if entity_type not in stats["entities_by_type"]:
                        stats["entities_by_type"][entity_type] = 0
                    stats["entities_by_type"][entity_type] += 1
                    
                    logger.info(f"Page {page_num + 1}: Masked {pii_match.entity_type}: '{pii_match.text}'")
                
                # Apply redactions
                page.apply_redactions()
                stats["pages_processed"] += 1
            
            # Save the modified PDF
            doc.save(output_path)
            doc.close()
            
            logger.info(f"PII masking completed. Output saved to: {output_path}")
            logger.info(f"Statistics: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def generate_report(self, stats: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate a detailed report of the PII masking process."""
        report_lines = [
            "PII Masking Report",
            "=" * 50,
            f"Total pages processed: {stats['pages_processed']}/{stats['total_pages']}",
            f"Total PII entities found: {stats['total_pii_found']}",
            "",
            "PII Entities by Type:",
            "-" * 30
        ]
        
        for entity_type, count in stats["entities_by_type"].items():
            report_lines.append(f"{entity_type}: {count}")
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_path}")
        
        return report

def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: python pii_masker.py <input_pdf> <output_pdf> [mask_strategy]")
        print("Mask strategies: redact (default), replace, blur")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    mask_strategy = sys.argv[3] if len(sys.argv) > 3 else "redact"
    
    if not os.path.exists(input_pdf):
        print(f"Error: Input file '{input_pdf}' not found")
        sys.exit(1)
    
    if mask_strategy not in ["redact", "replace", "blur"]:
        print(f"Error: Invalid mask strategy '{mask_strategy}'")
        print("Valid strategies: redact, replace, blur")
        sys.exit(1)
    
    try:
        # Initialize the PII masker
        masker = PIIMasker()
        
        # Process the PDF
        stats = masker.mask_pii_in_pdf(input_pdf, output_pdf, mask_strategy)
        
        # Generate and display report
        report = masker.generate_report(stats)
        print("\n" + report)
        
        # Save report to file
        report_path = output_pdf.replace('.pdf', '_report.txt')
        masker.generate_report(stats, report_path)
        
    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
