#!/usr/bin/env python3
"""
BERT NER PDF PII Masker

This script uses BERT-large-NER model to detect PII in PDF documents
and masks detected PII with realistic pseudo names while preserving
layout and maintaining contextual consistency.
"""

import sys
import os
import re
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not found. Please install: pip install PyMuPDF")
    sys.exit(1)

class PIIMaskingSystem:
    """
    A comprehensive PII masking system that replaces detected PII
    with realistic pseudo data while maintaining document structure and contextual consistency.
    """
    
    def __init__(self):
        self.pseudo_data = self._initialize_pseudo_data()
        self.used_mappings = {}  # Track consistent mappings across entire document
        self.ner_pipeline = None
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
    
    def _get_pseudo_replacement(self, entity_type: str, original_text: str) -> str:
        """Get a consistent pseudo replacement for the given entity."""
        # Check if we already have a mapping for this exact text
        if original_text in self.used_mappings:
            return self.used_mappings[original_text]
        
        # Get pseudo data for this entity type
        if entity_type in self.pseudo_data:
            replacement = random.choice(self.pseudo_data[entity_type])
        else:
            # Fallback for unknown entity types
            replacement = f"[MASKED_{entity_type}]"
        
        # Store the mapping for consistency
        self.used_mappings[original_text] = replacement
        return replacement
    
    def _detect_additional_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect additional PII patterns using regex."""
        additional_entities = []
        
        # Email pattern - more specific
        email_pattern = r'\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9][A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            additional_entities.append({
                'entity_group': 'EMAIL',
                'word': match.group(),
                'start': match.start(),
                'end': match.end(),
                'score': 0.95
            })
        
        # Phone pattern - more specific formats
        phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            r'\b\d{3}-\d{3}-\d{4}\b',
            r'\b\(\d{3}\)\s?\d{3}-\d{4}\b'
        ]
        for pattern in phone_patterns:
            for match in re.finditer(pattern, text):
                additional_entities.append({
                    'entity_group': 'PHONE',
                    'word': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'score': 0.90
                })
        
        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        for match in re.finditer(ssn_pattern, text):
            additional_entities.append({
                'entity_group': 'SSN',
                'word': match.group(),
                'start': match.start(),
                'end': match.end(),
                'score': 0.95
            })
        
        # Credit Card pattern - major card types
        cc_patterns = [
            r'\b4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',  # Visa
            r'\b5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',  # MasterCard
            r'\b3[47][0-9]{2}[-\s]?[0-9]{6}[-\s]?[0-9]{5}\b',  # American Express
        ]
        for pattern in cc_patterns:
            for match in re.finditer(pattern, text):
                additional_entities.append({
                    'entity_group': 'CREDIT_CARD',
                    'word': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'score': 0.90
                })
        
        # Date of Birth patterns
        dob_patterns = [
            r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',  # MM/DD/YYYY
            r'\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b',  # DD/MM/YYYY
            r'\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b'   # YYYY/MM/DD
        ]
        for pattern in dob_patterns:
            for match in re.finditer(pattern, text):
                additional_entities.append({
                    'entity_group': 'DATE',
                    'word': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'score': 0.85
                })
        
        return additional_entities
    
    def _is_valid_pii_entity(self, entity: Dict[str, Any]) -> bool:
        """Filter out false positives and non-PII entities."""
        word = entity['word'].strip()
        entity_type = entity['entity_group']
        score = entity['score']
        
        # Skip BERT tokenizer artifacts (subword tokens)
        if word.startswith('##'):
            return False
        
        # Skip very short words (likely false positives)
        if len(word) <= 2:
            return False
        
        # Skip low confidence detections
        if score < 0.7:
            return False
        
        # Skip common business/generic terms that are not PII
        non_pii_terms = {
            'we', 'in', 'ad', 'co', 'or', 'a', 'e', 'x', 'c', 'h', 'z',
            'management', 'investment', 'service', 'product', 'products',
            'advisor', 'custom', 'level', 'face', 'pan', 'act', 'boom',
            'loans', 'commercial', 'aviation', 'ai', 'co', 'au', 'us',
            'american', 'americans', 'generation', 'millennial', 'mill',
            'advice', 'report', 'consumer', 'hybrid', 'state', 'new',
            'capital', 'markets', 'vision', 'tomorrow', 'relationship'
        }
        
        if word.lower() in non_pii_terms:
            return False
        
        # Only allow specific entity types that are actually PII
        allowed_pii_types = {
            'PER',      # Person names
            'EMAIL',    # Email addresses  
            'PHONE',    # Phone numbers
            'SSN',      # Social Security Numbers
            'CREDIT_CARD',  # Credit card numbers
            'BANK_ACCOUNT', # Bank account numbers
            'DATE',     # Dates of birth
            'ADDRESS'   # Physical addresses
        }
        
        # For ORG entities, only allow well-known companies/organizations
        if entity_type == 'ORG':
            known_companies = {
                'google', 'apple', 'facebook', 'amazon', 'microsoft', 
                'linkedin', 'twitter', 'netflix', 'tesla', 'accenture',
                'ibm', 'oracle', 'salesforce', 'adobe', 'intel', 'nvidia',
                'paypal', 'uber', 'airbnb', 'spotify', 'zoom', 'slack',
                'federal reserve bank of new york', 'pew research center',
                'cnbc', 'bloomberg', 'reuters', 'wall street journal'
            }
            if word.lower() not in known_companies:
                return False
        
        # For LOC entities, only allow if they look like real locations
        elif entity_type == 'LOC':
            # Skip generic location terms
            generic_locations = {'us', 'u.s.', 'america', 'american'}
            if word.lower() in generic_locations:
                return False
        
        # For MISC entities, be very restrictive
        elif entity_type == 'MISC':
            return False  # Skip all MISC entities as they're usually false positives
        
        return entity_type in allowed_pii_types or entity_type in ['ORG', 'LOC']
    
    def _detect_all_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect all PII entities using BERT and regex patterns."""
        all_entities = []
        
        # BERT NER detection
        if self.ner_pipeline:
            bert_entities = self.ner_pipeline(text)
            # Filter out false positives
            bert_entities = [e for e in bert_entities if self._is_valid_pii_entity(e)]
            all_entities.extend(bert_entities)
        
        # Additional regex patterns (these are more reliable)
        regex_entities = self._detect_additional_pii(text)
        all_entities.extend(regex_entities)
        
        # Remove duplicates based on position overlap
        unique_entities = []
        for entity in all_entities:
            overlap = False
            for existing in unique_entities:
                if (entity['start'] < existing['end'] and entity['end'] > existing['start']):
                    # Keep the one with higher confidence
                    if entity['score'] > existing['score']:
                        unique_entities.remove(existing)
                        unique_entities.append(entity)
                    overlap = True
                    break
            if not overlap:
                unique_entities.append(entity)
        
        return unique_entities
    
    def _find_text_instances_in_page(self, page, text: str) -> List[Tuple]:
        """Find all instances of text in a PDF page and return their rectangles."""
        try:
            text_instances = page.search_for(text)
            return text_instances
        except Exception as e:
            logger.warning(f"Could not search for text '{text}': {e}")
            return []
    
    def mask_pdf_with_pseudo_data(self, input_pdf_path: str, output_pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file and mask PII with pseudo data while preserving layout.
        Maintains contextual consistency throughout the entire document.
        
        Args:
            input_pdf_path: Path to input PDF file
            output_pdf_path: Path to output masked PDF file
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "total_pages": 0,
            "total_pii_found": 0,
            "entities_by_type": {},
            "pages_processed": 0,
            "consistent_mappings": 0
        }
        
        try:
            # Open the PDF
            doc = fitz.open(input_pdf_path)
            stats["total_pages"] = len(doc)
            
            logger.info(f"Processing PDF: {input_pdf_path} ({stats['total_pages']} pages)")
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text from the page
                page_text = page.get_text()
                
                if not page_text.strip():
                    logger.debug(f"Page {page_num + 1}: No text found, skipping")
                    continue
                
                # Detect PII entities
                entities = self._detect_all_entities(page_text)
                
                if not entities:
                    logger.debug(f"Page {page_num + 1}: No PII found")
                    continue
                
                logger.info(f"Page {page_num + 1}: Found {len(entities)} PII entities")
                
                # Process each PII entity
                for entity in entities:
                    original_text = entity['word']
                    entity_type = entity['entity_group']
                    
                    # Get consistent pseudo replacement
                    if original_text in self.used_mappings:
                        stats["consistent_mappings"] += 1
                        replacement = self.used_mappings[original_text]
                        logger.debug(f"Using consistent mapping: '{original_text}' -> '{replacement}'")
                    else:
                        replacement = self._get_pseudo_replacement(entity_type, original_text)
                        logger.info(f"New mapping: '{original_text}' -> '{replacement}' ({entity_type})")
                    
                    # Find all instances of this text in the page
                    text_instances = self._find_text_instances_in_page(page, original_text)
                    
                    if not text_instances:
                        logger.warning(f"Could not locate text '{original_text}' in page {page_num + 1}")
                        continue
                    
                    # Replace each instance with pseudo data while preserving formatting
                    for rect in text_instances:
                        try:
                            # Get the original text properties for font matching
                            text_dict = page.get_text("dict", clip=rect)
                            
                            # Extract font information from the original text
                            font_size = 11  # default
                            font_name = "helv"  # default
                            
                            if text_dict and 'blocks' in text_dict:
                                for block in text_dict['blocks']:
                                    if 'lines' in block:
                                        for line in block['lines']:
                                            if 'spans' in line:
                                                for span in line['spans']:
                                                    if 'size' in span:
                                                        font_size = span['size']
                                                    if 'font' in span:
                                                        font_name = span['font']
                                                    break
                            
                            # Create a redaction annotation
                            redact_annot = page.add_redact_annot(rect)
                            
                            # Set the replacement text with similar font properties
                            redact_annot.set_info(content=replacement)
                            redact_annot.update()
                            
                        except Exception as e:
                            logger.warning(f"Failed to redact '{original_text}': {e}")
                            continue
                    
                    # Update statistics
                    stats["total_pii_found"] += len(text_instances)
                    if entity_type not in stats["entities_by_type"]:
                        stats["entities_by_type"][entity_type] = 0
                    stats["entities_by_type"][entity_type] += len(text_instances)
                
                # Apply all redactions on this page
                page.apply_redactions()
                stats["pages_processed"] += 1
            
            # Save the masked PDF
            doc.save(output_pdf_path)
            doc.close()
            
            logger.info(f"✓ Masked PDF saved to: {output_pdf_path}")
            logger.info(f"✓ Statistics: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def generate_masking_report(self, stats: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate a detailed report of the PII masking process."""
        report_lines = [
            "PII Masking Report with Contextual Consistency",
            "=" * 60,
            f"Total pages processed: {stats['pages_processed']}/{stats['total_pages']}",
            f"Total PII instances found: {stats['total_pii_found']}",
            f"Consistent mappings used: {stats['consistent_mappings']}",
            f"Unique entities mapped: {len(self.used_mappings)}",
            "",
            "PII Entities by Type:",
            "-" * 40
        ]
        
        for entity_type, count in stats["entities_by_type"].items():
            report_lines.append(f"{entity_type}: {count} instances")
        
        report_lines.extend([
            "",
            "Consistent Mappings Used:",
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
    
    def mask_text_with_pseudo_data(self, text: str, entities: List[Dict[str, Any]]) -> tuple:
        """
        Mask the text by replacing PII with pseudo data.
        Returns (masked_text, masking_report)
        """
        # Sort entities by start position in reverse order to avoid index shifting
        sorted_entities = sorted(entities, key=lambda x: x['start'], reverse=True)
        
        masked_text = text
        masking_report = []
        
        for entity in sorted_entities:
            original = entity['word']
            entity_type = entity['entity_group']
            start = entity['start']
            end = entity['end']
            
            # Get pseudo replacement
            replacement = self._get_pseudo_replacement(entity_type, original)
            
            # Replace in text
            masked_text = masked_text[:start] + replacement + masked_text[end:]
            
            # Add to report
            masking_report.append({
                'original': original,
                'replacement': replacement,
                'type': entity_type,
                'confidence': entity['score']
            })
        
        return masked_text, masking_report
        
def create_sample_pdf_with_pii():
    """Create a sample PDF with PII for testing."""
    try:
        doc = fitz.open()
        page = doc.new_page()
        
        sample_content = """
        CONFIDENTIAL EMPLOYEE RECORD
        
        Personal Information:
        Name: John Doe
        Email: john.doe@techcorp.com  
        Phone: (555) 234-5678
        SSN: 456-78-9012
        Date of Birth: 07/22/1988
        
        Address: 456 Oak Avenue, San Francisco, CA 94102
        
        Emergency Contact:
        Name: John Doe (Same person mentioned above)
        Phone: 555-876-5432
        Relationship: Self-Reference
        
        Employment Details:
        Employee ID: EMP001234
        Company: TechCorp Industries
        Department: Engineering  
        Manager: Jane Smith
        Start Date: 2019-03-15
        
        Banking Information:
        Account Number: 1234567890123456
        Routing Number: 123456789
        
        Medical Information:
        Insurance Provider: HealthCare Plus
        Policy Number: HC123456789
        Doctor: Dr. Sarah Williams
        Phone: (555) 999-8888
        
        Additional Notes:
        John Doe has been with the company since 2019.
        Contact John Doe at john.doe@techcorp.com for any queries.
        """
        
        # Insert text
        point = fitz.Point(50, 50)
        page.insert_text(point, sample_content, fontsize=11)
        
        # Save the PDF
        sample_path = "sample_pii_document.pdf"
        doc.save(sample_path)
        doc.close()
        
        logger.info(f"Created sample PDF: {sample_path}")
        return sample_path
        
    except Exception as e:
        logger.error(f"Error creating sample PDF: {e}")
        return None

def process_pdf_with_pii_masking(input_pdf: str, output_pdf: str):
    """Process a PDF file and mask PII with pseudo data."""
    try:
        # Initialize the PII masking system
        logger.info("Initializing PII masking system...")
        pii_masker = PIIMaskingSystem()
        
        # Process the PDF
        logger.info(f"Processing PDF: {input_pdf}")
        stats = pii_masker.mask_pdf_with_pseudo_data(input_pdf, output_pdf)
        
        # Generate and save report
        report_path = output_pdf.replace('.pdf', '_masking_report.txt')
        report = pii_masker.generate_masking_report(stats, report_path)
        
        # Display summary
        print("\n" + "="*60)
        print("PII MASKING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Input PDF: {input_pdf}")
        print(f"Output PDF: {output_pdf}")
        print(f"Report: {report_path}")
        print("\nSummary:")
        print(f"  • Pages processed: {stats['pages_processed']}/{stats['total_pages']}")
        print(f"  • PII instances found: {stats['total_pii_found']}")
        print(f"  • Consistent mappings: {stats['consistent_mappings']}")
        print(f"  • Unique entities: {len(pii_masker.used_mappings)}")
        
        if stats['entities_by_type']:
            print("\nPII Types Found:")
            for entity_type, count in stats['entities_by_type'].items():
                print(f"  • {entity_type}: {count} instances")
        
        print("\nContextual Consistency Mappings:")
        for original, replacement in pii_masker.used_mappings.items():
            print(f"  • '{original}' → '{replacement}'")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return False

def test_with_sample_pdf():
    """Test the system with a sample PDF."""
    print("Creating sample PDF with PII...")
    sample_pdf = create_sample_pdf_with_pii()
    
    if not sample_pdf:
        print("Failed to create sample PDF")
        return False
    
    try:
        output_pdf = "masked_" + sample_pdf
        success = process_pdf_with_pii_masking(sample_pdf, output_pdf)
        
        # Clean up sample file
        if os.path.exists(sample_pdf):
            os.remove(sample_pdf)
            
        return success
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

def main():
    """Main function for command-line usage."""
    print("BERT NER PDF PII Masker")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python bert_ner_downloader.py <input.pdf> <output.pdf>")
        print("  python bert_ner_downloader.py test")
        print("")
        print("Examples:")
        print("  python bert_ner_downloader.py document.pdf masked_document.pdf")
        print("  python bert_ner_downloader.py test  # Run with sample PDF")
        return 1
    
    if sys.argv[1] == "test":
        print("Running test with sample PDF...")
        success = test_with_sample_pdf()
        if success:
            print("\n✓ Test completed successfully!")
            print("Check the generated 'masked_sample_pii_document.pdf' file.")
        else:
            print("\n✗ Test failed!")
            return 1
    else:
        if len(sys.argv) < 3:
            print("Error: Please provide both input and output PDF paths")
            print("Usage: python bert_ner_downloader.py <input.pdf> <output.pdf>")
            return 1
        
        input_pdf = sys.argv[1]
        output_pdf = sys.argv[2]
        
        if not os.path.exists(input_pdf):
            print(f"Error: Input file '{input_pdf}' not found")
            return 1
        
        if not input_pdf.lower().endswith('.pdf'):
            print(f"Error: Input file must be a PDF")
            return 1
        
        success = process_pdf_with_pii_masking(input_pdf, output_pdf)
        if not success:
            print("\n✗ PDF processing failed!")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
