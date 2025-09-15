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
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

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
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
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
    
    def _select_best_entity_type(self, entities: List[DetectedPII]) -> DetectedPII:
        """
        Select the most appropriate entity when multiple PII types are detected for the same text.
        Priority order (most specific to least specific):
        1. High-sensitivity types (SSN, CREDIT_CARD, BANK_ACCOUNT, etc.)
        2. Specific identifiers (PASSPORT, EMPLOYEE_ID, STUDENT_ID, etc.)  
        3. Contact info (EMAIL, PHONE)
        4. Address components (ADDRESS over LOC)
        5. Generic types (PERSON, ORG, LOC)
        """
        if len(entities) == 1:
            return entities[0]
        
        # Define priority order (higher number = higher priority)
        type_priority = {
            # Highest priority - sensitive financial/government IDs
            'SSN': 100,
            'CREDIT_CARD': 95,
            'BANK_ACCOUNT': 95,
            'AADHAAR': 90,
            'PAN': 90,
            'PASSPORT': 85,
            'DRIVER_LICENSE': 85,
            'MEDICAL_RECORD': 80,
            'INSURANCE_ID': 80,
            
            # High priority - specific identifiers
            'EMPLOYEE_ID': 75,
            'STUDENT_ID': 75,
            'VACCINE_LOT': 70,
            'TRACKING_NUMBER': 70,
            'RECEIPT_NUMBER': 70,
            'VOLUNTEER_CODE': 70,
            'BARCODE': 65,
            'VEHICLE_PLATE': 65,
            
            # Medium priority - technical identifiers
            'MAC_ADDRESS': 60,
            'IP_ADDRESS': 60,
            'URL': 55,
            'COORDINATES': 55,
            
            # Medium priority - contact information
            'EMAIL': 50,
            'PHONE': 50,
            
            # Medium priority - dates and addresses
            'DATE_OF_BIRTH': 45,
            'DATE': 40,
            'ADDRESS': 35,  # More specific than LOC
            'ZIP_CODE': 35,
            
            # Lower priority - generic types
            'PERSON': 30,
            'ORG': 25,
            'LOC': 20,  # Less specific than ADDRESS
            'MISC': 10
        }
        
        # Sort entities by priority (highest first), then by confidence
        sorted_entities = sorted(entities, 
                               key=lambda x: (type_priority.get(x.pii_type, 0), x.confidence), 
                               reverse=True)
        
        best_entity = sorted_entities[0]
        
        # Log the selection decision
        entity_info = [(e.pii_type, type_priority.get(e.pii_type, 0), e.confidence) for e in entities]
        logger.debug(f"Entity type selection for '{best_entity.text}': {entity_info} -> {best_entity.pii_type}")
        
        return best_entity
    
    def detect_pii_with_bert(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII using BERT NER model with improved entity merging."""
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
    
    def detect_pii_with_llm(self, text: str, max_chunk_size: int = 4000) -> List[Dict[str, Any]]:
        """Use LLM to detect PII entities with high accuracy and context awareness."""
        try:
            # Split text into chunks if too long
            chunks = []
            if len(text) > max_chunk_size:
                words = text.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) > max_chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [word]
                        current_length = len(word)
                    else:
                        current_chunk.append(word)
                        current_length += len(word) + 1
                
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
            else:
                chunks = [text]
            
            all_entities = []
            chunk_offset = 0
            
            for chunk in chunks:
                system_prompt = """You are an expert PII (Personally Identifiable Information) detection system with advanced pattern recognition capabilities. Your task is to meticulously analyze the given text and identify ALL types of PII with extremely high precision and comprehensive coverage.

**CRITICAL DETECTION REQUIREMENTS:**
2. **COMPREHENSIVE COVERAGE**: Do not miss any PII - scan every word, number, and pattern
3. **CONTEXT AWARENESS**: Use surrounding text to determine if something is actually PII
4. **EXACT TEXT MATCHING**: Return the exact text as it appears in the document
5. **PRECISE POSITIONING**: Calculate accurate character positions

**DETAILED PII CATEGORIES TO DETECT:**

**PERSONAL IDENTIFIERS:**
- PERSON: All types of names (first + last), nicknames, name variations (e.g., "Aaron Mehta", "A. Mehta", "Mr. Jonathan Clarke")
- SSN: Social Security Numbers (XXX-XX-XXXX format or variations)
- PASSPORT: Passport numbers (any format with letters/numbers)
- DRIVER_LICENSE: Driver's license numbers (state-specific formats)
- ORGANISATIONS: Company names, institutions, agencies

**CONTACT INFORMATION:**
- EMAIL: All email addresses (any @domain format)
- PHONE: Phone numbers (all formats: +1 (XXX) XXX-XXXX, +XX-XXXXX-XXXXX, etc.)
- ADDRESS: Complete addresses, partial addresses, street names, building names, apartment numbers
- ZIP_CODE: Postal codes, ZIP codes (5-digit, ZIP+4, international formats)

**FINANCIAL DATA:**
- CREDIT_CARD: Credit card numbers (XXXX-XXXX-XXXX-XXXX or any format)
- BANK_ACCOUNT: Bank account numbers, routing numbers, IBAN numbers
- PAN: PAN card numbers (AAAAA0000A format)
- AADHAAR: Aadhaar numbers (XXXX XXXX XXXX format)

**DATES AND IDENTIFIERS:**
- DATE_OF_BIRTH: Birth dates (MM/DD/YYYY, DD/MM/YYYY, any date format)
- EMPLOYEE_ID: Employee IDs, badge numbers (EMP-XXXX-XXXX format)
- STUDENT_ID: Student ID numbers
- MEDICAL_RECORD: Medical record numbers (MRN-XXXXXX format)
- INSURANCE_ID: Insurance policy numbers (INS-XX-XXXXXX-XXXX format)
- VACCINE_LOT: Vaccine lot numbers (VAX-XXXX-XXXX format)
- RECEIPT_NUMBER: Receipt numbers (RN-XXXX-XXXXXX format)
- VOLUNTEER_CODE: Volunteer codes (VOL-XX-XXX format)

**TECHNICAL IDENTIFIERS:**
- IP_ADDRESS: IP addresses (IPv4: XXX.XXX.XXX.XXX, IPv6 formats)
- MAC_ADDRESS: MAC addresses (XX:XX:XX:XX:XX:XX format)
- URL: Website URLs (linkedin.com/in/..., github.com/..., etc.)
- COORDINATES: GPS coordinates (latitude, longitude pairs)

**LOCATION DATA:**
- LOC: Locations, cities, states, countries, building names
- ORG: Organizations, companies, institutions
- VEHICLE_PLATE: License plate numbers (state-specific formats)

**TRACKING AND CODES:**
- TRACKING_NUMBER: Tracking numbers (TRK-XXXXXXXXXX format)
- BARCODE: Barcode numbers (long numeric sequences)

**SPECIAL DETECTION INSTRUCTIONS:**
1. **MAC Addresses**: Look for patterns like "00:1A:2B:3C:4D:5E" - detect the COMPLETE address
2. **IP Addresses**: Detect both local (192.168.x.x) and public IP addresses
3. **Medical Records**: Look for "MRN" followed by numbers or dashes
4. **Vaccine Data**: Look for "VAX-" prefix or "lot no." followed by codes
5. **Barcodes**: Long numeric sequences (12+ digits) especially after "barcode"
6. **Names with Titles**: Include titles like "Mr.", "Ms.", "Dr." with names
7. **Partial Addresses**: Even fragments like "78, Sunrise Apartments" or "7th Floor, Mumbai"
8. **Phone Extensions**: Numbers that appear to be phone numbers even without country codes

Return a JSON list with this EXACT format:
[
    {
        "text": "exact_text_as_found_in_document",
        "pii_type": "SPECIFIC_PII_TYPE",
        "start": character_start_position,
        "end": character_end_position,
        "confidence": confidence_score_0_to_1,
        "context_info": "surrounding_context_for_validation"
    }
]

**VALIDATION CHECKLIST:**
- ✓ Are all IP addresses (both local and public) detected?
- ✓ Are all MAC addresses with colons detected?
- ✓ Are medical record numbers (MRN-XXXXXX) detected?
- ✓ Are vaccine lot numbers (VAX-XXXX-XXXX) detected?
- ✓ Are barcode numbers (long numeric sequences) detected?
- ✓ Are all partial addresses and location references detected?
- ✓ Are tracking numbers with prefixes detected?

Return ONLY the JSON array, no additional text or explanation."""

                human_prompt = f"Analyze this text for PII:\n\n{chunk}"
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt)
                ]
                
                try:
                    response = self.llm.invoke(messages)
                    response_text = response.content.strip()
                    logger.debug(f"LLM Response: {response_text}")
                    
                    # Clean up the response to extract JSON - more robust cleaning
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    elif response_text.startswith('```'):
                        response_text = response_text[3:]
                    
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    
                    # Remove any additional markdown formatting
                    response_text = response_text.strip()
                    
                    entities = json.loads(response_text)
                    
                    # Adjust positions for chunk offset and validate
                    for entity in entities:
                        if isinstance(entity, dict) and 'text' in entity and 'pii_type' in entity:
                            entity_text = entity['text']
                            
                            # More flexible text verification - check if text exists in chunk
                            # Handle cases where LLM might have slight variations in whitespace
                            text_found = False
                            if entity_text in chunk:
                                text_found = True
                            else:
                                # Try normalized text (handle whitespace differences)
                                normalized_entity = ' '.join(entity_text.split())
                                normalized_chunk = ' '.join(chunk.split())
                                if normalized_entity in normalized_chunk:
                                    text_found = True
                                    logger.debug(f"Found text with normalization: '{entity_text}'")
                            
                            if text_found:
                                # Adjust positions for global text (if provided)
                                if 'start' in entity and 'end' in entity:
                                    entity['start'] += chunk_offset
                                    entity['end'] += chunk_offset
                                else:
                                    # If positions not provided, calculate them
                                    start_pos = chunk.find(entity_text)
                                    if start_pos >= 0:
                                        entity['start'] = start_pos + chunk_offset
                                        entity['end'] = start_pos + len(entity_text) + chunk_offset
                                    else:
                                        # Fallback - use approximate positions
                                        entity['start'] = chunk_offset
                                        entity['end'] = chunk_offset + len(entity_text)
                                
                                entity['confidence'] = entity.get('confidence', 0.8)
                                entity['source'] = 'LLM'
                                
                                # Handle both 'type' and 'pii_type' keys for consistency
                                if 'pii_type' not in entity and 'type' in entity:
                                    entity['pii_type'] = entity.pop('type')
                                elif 'type' not in entity and 'pii_type' in entity:
                                    entity['type'] = entity['pii_type']
                                
                                all_entities.append(entity)
                                logger.debug(f"Added entity: '{entity_text}' ({entity['pii_type']})")
                            else:
                                logger.warning(f"Could not verify text in chunk: '{entity_text}'")
                        else:
                            logger.warning(f"Invalid entity structure: {entity}")
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.error(f"Failed to parse LLM response for chunk: {e}")
                    logger.error(f"Response text: {response_text}")
                    continue
                
                chunk_offset += len(chunk) + 1 
            
            logger.info(f"LLM detected {len(all_entities)} PII entities")
            return all_entities
            
        except Exception as e:
            logger.error(f"LLM PII detection failed: {e}")
            return []
    
    def detect_all_pii(self, text: str, page_num: int = 0, doc: fitz.Document = None) -> List[DetectedPII]:
        """Detect all PII using LLM first, then BERT for coordinates, with comprehensive validation."""
        all_entities = []
        
        # Step 1: Use LLM for initial comprehensive PII detection
        logger.info(f"Starting LLM-based PII detection on page {page_num + 1}")
        llm_entities = self.detect_pii_with_llm(text)
        all_entities.extend(llm_entities)
        logger.info(f"LLM detected {len(llm_entities)} entities on page {page_num + 1}")
        
        # Log each LLM entity for debugging
        for i, entity in enumerate(llm_entities):
            logger.debug(f"LLM Entity {i+1}: '{entity.get('text', 'N/A')}' -> {entity.get('pii_type', 'N/A')}")
        
        # Step 2: Use BERT for additional detection and coordinate finding
        if self.ner_pipeline:
            bert_entities = self.detect_pii_with_bert(text)
            all_entities.extend(bert_entities)
            logger.debug(f"BERT detected {len(bert_entities)} additional entities on page {page_num + 1}")
        
        validated_entities = all_entities
        logger.info(f"Total entities before conversion: {len(validated_entities)}")
        
        # Step 3: Convert to DetectedPII objects with coordinates
        detected_pii = []
        for i, entity in enumerate(validated_entities):
            try:
                # Ensure required fields exist
                if not all(key in entity for key in ["text", "pii_type", "start", "end"]):
                    logger.warning(f"Skipping entity {i+1} due to missing required fields: {entity}")
                    continue
                
                # Find coordinates if document is provided
                x0, y0, x1, y1 = 0.0, 0.0, 0.0, 0.0
                if doc:
                    x0, y0, x1, y1 = self.find_text_coordinates(
                        doc, page_num, entity["text"], 
                        entity["start"], entity["end"]
                    )
                
                # Use suggested strategy from LLM validation if available
                suggested_strategy = entity.get('suggested_strategy', 
                                              self._suggest_masking_strategy(entity["pii_type"], entity["text"]))
                
                pii = DetectedPII(
                    text=entity["text"],
                    pii_type=entity["pii_type"],
                    confidence=entity.get("confidence", 0.8),
                    start=entity["start"],
                    end=entity["end"],
                    page_num=page_num,
                    suggested_strategy=suggested_strategy,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1
                )
                detected_pii.append(pii)
                logger.debug(f"Converted entity {i+1}: '{pii.text}' -> {pii.pii_type} ({pii.suggested_strategy})")
                
            except Exception as e:
                logger.error(f"Error converting entity {i+1}: {entity} - Error: {e}")
                continue
        
        logger.info(f"Page {page_num + 1}: Converted {len(detected_pii)} entities to DetectedPII objects")
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
        Find the exact coordinates of text on a PDF page with improved precision.
        
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
            
            # Method 1: Direct text search - try multiple variations
            text_variations = [
                text,
                text.strip(),
                ' '.join(text.split()),  # Normalize whitespace
            ]
            
            for text_variant in text_variations:
                text_instances = page.search_for(text_variant)
                if text_instances:
                    # Return the first match (most likely correct)
                    rect = text_instances[0]
                    logger.debug(f"Found direct match for '{text_variant}': ({rect.x0:.2f}, {rect.y0:.2f}, {rect.x1:.2f}, {rect.y1:.2f})")
                    return (rect.x0, rect.y0, rect.x1, rect.y1)
            
            # Method 2: Use character position mapping with improved accuracy
            page_text = page.get_text()
            
            # Find the actual text at the given positions
            if start_char < len(page_text) and end_char <= len(page_text):
                actual_text = page_text[start_char:end_char]
                
                # Try searching for the actual extracted text
                if actual_text.strip():
                    text_instances = page.search_for(actual_text.strip())
                    if text_instances:
                        rect = text_instances[0]
                        logger.debug(f"Found position-based match for '{actual_text.strip()}': ({rect.x0:.2f}, {rect.y0:.2f}, {rect.x1:.2f}, {rect.y1:.2f})")
                        return (rect.x0, rect.y0, rect.x1, rect.y1)
            
            # Method 3: Use text blocks to find approximate position with better mapping
            blocks = page.get_text("dict")
            
            current_char = 0
            target_start = start_char
            target_end = end_char
            
            for block in blocks.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_start_char = current_char
                    line_text = ""
                    line_spans = []
                    
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        line_text += span_text
                        line_spans.append((span, current_char, current_char + len(span_text)))
                        current_char += len(span_text)
                    
                    # Add newline character
                    line_end_char = current_char
                    current_char += 1
                    
                    # Check if our target text falls within this line
                    if (target_start >= line_start_char and target_start < line_end_char):
                        # Found the line containing our text
                        
                        # Try to find the exact span
                        for span, span_start, span_end in line_spans:
                            if (target_start >= span_start and target_start < span_end):
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                
                                # If the entity spans multiple spans, try to get better coordinates
                                if target_end > span_end:
                                    # Find the last span
                                    last_bbox = bbox
                                    for span2, span_start2, span_end2 in line_spans:
                                        if target_end <= span_end2 and span_start2 >= span_start:
                                            last_bbox = span2.get("bbox", bbox)
                                    
                                    # Combine bboxes
                                    final_bbox = (bbox[0], bbox[1], last_bbox[2], max(bbox[3], last_bbox[3]))
                                    logger.debug(f"Found multi-span match: {final_bbox}")
                                    return final_bbox
                                else:
                                    logger.debug(f"Found single-span match: {bbox}")
                                    return (bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Method 4: Partial word matching for names that might be split
            words = text.split()
            if len(words) > 1:
                # Try to find coordinates for the first word and estimate the full extent
                first_word_instances = page.search_for(words[0])
                last_word_instances = page.search_for(words[-1])
                
                if first_word_instances and last_word_instances:
                    # Find the best combination that could represent our full text
                    for first_rect in first_word_instances:
                        for last_rect in last_word_instances:
                            # Check if they're on the same line (similar y coordinates)
                            if abs(first_rect.y0 - last_rect.y0) < 5 and first_rect.x0 <= last_rect.x1:
                                combined_rect = (first_rect.x0, first_rect.y0, last_rect.x1, max(first_rect.y1, last_rect.y1))
                                logger.debug(f"Found word-combination match for '{text}': {combined_rect}")
                                return combined_rect
            
            # Method 5: Fallback - return approximate coordinates based on page size
            logger.warning(f"Could not find exact coordinates for text: '{text}'")
            page_rect = page.rect
            return (50, 50, min(200 + len(text) * 6, page_rect.width - 50), 80)  # Estimate based on text length
            
        except Exception as e:
            logger.warning(f"Error finding coordinates for text '{text}': {e}")
            # Return safe default coordinates
            return (50, 50, 200, 80)
    
    def generate_config_file(self, detected_pii: List[DetectedPII], output_path: str, 
                           interactive: bool = False) -> Dict[str, Any]:
        """Generate configuration file for bert_pii_masker.py"""
        
        logger.info(f"Starting config generation with {len(detected_pii)} detected PII entities")
        
        # Smart deduplication - consolidate same text with different PII types
        text_to_entities = {}
        
        # Group entities by text and page
        for pii in detected_pii:
            normalized_text = pii.text.strip().lower()
            key = (normalized_text, pii.page_num)
            
            if key not in text_to_entities:
                text_to_entities[key] = []
            text_to_entities[key].append(pii)
        
        # For each group, select the most appropriate PII type
        unique_pii = []
        
        for (normalized_text, page_num), entities in text_to_entities.items():
            if len(entities) == 1:
                # No duplicates, keep as is
                unique_pii.append(entities[0])
                logger.debug(f"Added single entity: '{entities[0].text}' ({entities[0].pii_type})")
            else:
                # Multiple entities with same text - choose the most specific/appropriate one
                best_entity = self._select_best_entity_type(entities)
                unique_pii.append(best_entity)
                
                entity_types = [e.pii_type for e in entities]
                logger.debug(f"Consolidated '{best_entity.text}': {entity_types} -> {best_entity.pii_type}")
        
        # Sort by page number and then by y-coordinate for consistent output
        unique_pii.sort(key=lambda x: (x.page_num, x.y0, x.x0))
        logger.info(f"After smart deduplication: {len(unique_pii)} unique PII entities")
        
        # Log all entities being added to config
        for pii in unique_pii:
            logger.debug(f"Config entry: '{pii.text}' -> {pii.pii_type}:{pii.suggested_strategy}")
        
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
        detector.generate_detection_report(stats, report_path)
        
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
