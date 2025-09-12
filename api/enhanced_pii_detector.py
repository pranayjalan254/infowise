#!/usr/bin/env python3
"""
Enhanced PII Detection System

This module provides comprehensive PII detection using multiple approaches:
1. BERT NER model for entity recognition
2. Presidio/spaCy for advanced pattern matching
3. Custom regex patterns for specific PII types
4. LLM verification to reduce false positives and catch missed PIIs
5. Coordinate-based detection for accurate masking

The system handles coordinate overlapping issues and provides confidence scoring.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    logger.error("PyMuPDF not found. Please install: pip install PyMuPDF")
    sys.exit(1)

try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    BERT_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not installed. BERT detection will be disabled.")
    BERT_AVAILABLE = False

try:
    import spacy
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    PRESIDIO_AVAILABLE = True
except ImportError:
    logger.warning("Presidio/spaCy not installed. Advanced pattern matching will be disabled.")
    PRESIDIO_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("Google Gemini not installed. LLM verification will be disabled.")
    GEMINI_AVAILABLE = False

@dataclass
class PIIEntity:
    """Enhanced PII entity with comprehensive metadata."""
    text: str
    pii_type: str
    confidence: float
    start: int
    end: int
    page_num: int
    source: str  # "BERT", "Presidio", "Regex", "LLM"
    suggested_strategy: str = "redact"
    
    # PDF coordinates
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    
    # Additional metadata
    context: str = ""  # Surrounding text for LLM analysis
    verified_by_llm: bool = False
    is_false_positive: bool = False
    severity: str = "medium"  # "low", "medium", "high"

class EnhancedPIIDetector:
    """
    Comprehensive PII detection system combining multiple approaches.
    """
    
    def __init__(self, google_api_key: Optional[str] = None, spacy_model: str = "en_core_web_sm"):
        """Initialize the enhanced PII detector."""
        self.google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        self.spacy_model = spacy_model
        
        # Detection engines
        self.bert_pipeline = None
        self.presidio_analyzer = None
        self.nlp = None
        self.gemini_llm = None
        
        # Configuration
        self.custom_patterns = self._get_custom_patterns()
        self.pii_types = self._get_pii_types()
        self.false_positive_patterns = self._get_false_positive_patterns()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all available detection models."""
        logger.info("Initializing PII detection models...")
        
        # Initialize BERT
        if BERT_AVAILABLE:
            self._initialize_bert()
        
        # Initialize Presidio/spaCy
        if PRESIDIO_AVAILABLE:
            self._initialize_presidio()
        
        # Initialize Google Gemini
        if GEMINI_AVAILABLE and self.google_api_key:
            self._initialize_gemini()
        
        logger.info("PII detection models initialization completed")
    
    def _initialize_bert(self):
        """Initialize BERT NER model."""
        try:
            model_name = "dslim/bert-base-NER"
            logger.info(f"Loading BERT model: {model_name}")
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            self.bert_pipeline = pipeline(
                "ner", 
                model=model, 
                tokenizer=tokenizer,
                aggregation_strategy="simple"
            )
            logger.info("✓ BERT model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load BERT model: {e}")
            self.bert_pipeline = None
    
    def _initialize_presidio(self):
        """Initialize Presidio analyzer and spaCy."""
        try:
            # Load spaCy model
            logger.info(f"Loading spaCy model: {self.spacy_model}")
            self.nlp = spacy.load(self.spacy_model)
            
            # Initialize Presidio
            logger.info("Initializing Presidio analyzer")
            self.presidio_analyzer = AnalyzerEngine()
            
            logger.info("✓ Presidio/spaCy models loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load Presidio/spaCy: {e}")
            self.presidio_analyzer = None
            self.nlp = None
    
    def _initialize_gemini(self):
        """Initialize Google Gemini LLM."""
        try:
            # Set environment variable for Google API
            if self.google_api_key:
                os.environ["GOOGLE_API_KEY"] = self.google_api_key
            
            self.gemini_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.1
            )
            logger.info("✓ Google Gemini LLM initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Google Gemini: {e}")
            self.gemini_llm = None
    
    def _get_custom_patterns(self) -> Dict[str, List[str]]:
        """Define comprehensive regex patterns for PII detection."""
        return {
            "SSN": [
                r"\b\d{3}-\d{2}-\d{4}\b",          # XXX-XX-XXXX
                r"\b\d{3}\s\d{2}\s\d{4}\b",        # XXX XX XXXX
                r"\b\d{9}\b"                        # XXXXXXXXX
            ],
            "PHONE": [
                r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                r"\b\d{3}-\d{3}-\d{4}\b",
                r"\(\d{3}\)\s?\d{3}-\d{4}",
                r"\+91[-.\s]?\d{10}\b",             # Indian phone numbers
                r"\b[6-9]\d{9}\b",                  # Indian mobile numbers
                r"\+44\s\d{2}\s\d{4}\s\d{4}\b"     # UK phone numbers
            ],
            "EMAIL": [
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            ],
            "CREDIT_CARD": [
                r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
                r"\b4111[-\s]?XXXX[-\s]?XXXX[-\s]?1111\b"  # Masked credit cards
            ],
            "BANK_ACCOUNT": [
                r"\b\d{9,18}\b",                    # General bank account patterns
                r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",  # IBAN format
                r"\bGB\d{2}\s?[A-Z]{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b"  # UK IBAN
            ],
            "AADHAAR": [
                r"\b\d{4}\s\d{4}\s\d{4}\b",       # XXXX XXXX XXXX format
                r"\b\d{12}\b"                      # 12 consecutive digits
            ],
            "PAN": [
                r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"      # ABCDE1234F format
            ],
            "PASSPORT": [
                r"\b[A-Z]\d{7}\b",                 # X1234567 format
                r"\b[A-Z]{2}\d{6}\b"               # XX123456 format
            ],
            "DRIVER_LICENSE": [
                r"\bDL-[A-Z]{2}-\d{10}\b",        # DL-NY-0987654321
                r"\b[A-Z]{1,2}\d{6,8}\b"          # State format variations
            ],
            "IP_ADDRESS": [
                r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
            ],
            "MAC_ADDRESS": [
                r"\b[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}\b"
            ],
            "TRACKING_NUMBER": [
                r"\bTRK-\d{10}\b"
            ],
            "EMPLOYEE_ID": [
                r"\bEMP-\d{4}-\d{4}\b",
                r"\bEmployeeID:\s*[A-Z0-9-]+\b"
            ],
            "STUDENT_ID": [
                r"\bStudentID\s*\d{10}\b"
            ],
            "MEDICAL_RECORD": [
                r"\bMRN-\d{6}\b"
            ],
            "INSURANCE_POLICY": [
                r"\bINS-[A-Z]{2}-\d{6}-\d{4}\b"
            ],
            "VEHICLE_REGISTRATION": [
                r"\b[A-Z]{2}-\d{2}-[A-Z]{2}-\d{4}\b"  # KA-05-MQ-2025
            ],
            "GPS_COORDINATES": [
                r"\b-?\d{1,3}\.\d{6},\s*-?\d{1,3}\.\d{6}\b"
            ],
            "VOLUNTEER_CODE": [
                r"\bVOL-\d{2}-\d{3}\b"
            ],
            "DONATION_RECEIPT": [
                r"\bRN-\d{4}-\d{6}\b"
            ],
            "VACCINE_LOT": [
                r"\bVAX-\d{4}-\d{4}\b"
            ],
            "BARCODE": [
                r"\b\d{18}\b"  # 18-digit barcode
            ],
            "URL": [
                r"\bhttps?://[^\s]+\b",
                r"\b[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov)/[^\s]*\b"
            ],
            "DATE_OF_BIRTH": [
                r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",  # MM/DD/YYYY
                r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b",  # DD/MM/YYYY
                r"\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b",  # YYYY/MM/DD
                r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b"   # DD/MM/YYYY
            ]
        }
    
    def _get_pii_types(self) -> Set[str]:
        """Get all supported PII types."""
        bert_types = {"PER", "ORG", "LOC", "MISC"}
        presidio_types = {
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS", "DATE_TIME", "LOCATION", "URL",
            "US_DRIVER_LICENSE", "US_PASSPORT", "MEDICAL_LICENSE",
            "US_BANK_NUMBER"
        }
        regex_types = set(self.custom_patterns.keys())
        
        return bert_types.union(presidio_types).union(regex_types)
    
    def _get_false_positive_patterns(self) -> List[str]:
        """Define patterns that commonly cause false positives."""
        return [
            r"\b(?:page|section|chapter|figure|table)\s*\d+\b",
            r"\b(?:version|v)\d+\.\d+\b",
            r"\b\d{4}\s*(?:pixels|px|pt|em)\b",
            r"\b(?:isbn|issn)[-:\s]*\d+\b",
            r"\b(?:copyright|©)\s*\d{4}\b",
            r"\b\d+\s*(?:mb|gb|kb|bytes?)\b",
            r"\b\d+\s*(?:inches?|in|cm|mm|ft|feet)\b"
        ]
    
    def detect_pii_with_bert(self, text: str) -> List[PIIEntity]:
        """Detect PII using BERT NER model."""
        entities = []
        
        if not self.bert_pipeline:
            return entities
        
        try:
            bert_entities = self.bert_pipeline(text)
            
            for entity in bert_entities:
                if self._is_valid_bert_entity(entity):
                    pii_type = self._map_bert_entity_type(entity['entity_group'])
                    
                    pii_entity = PIIEntity(
                        text=entity['word'].strip(),
                        pii_type=pii_type,
                        confidence=entity['score'],
                        start=entity['start'],
                        end=entity['end'],
                        page_num=0,  # Will be set by caller
                        source="BERT",
                        suggested_strategy=self._suggest_strategy(pii_type)
                    )
                    
                    entities.append(pii_entity)
            
        except Exception as e:
            logger.error(f"BERT detection error: {e}")
        
        return entities
    
    def detect_pii_with_presidio(self, text: str) -> List[PIIEntity]:
        """Detect PII using Presidio analyzer."""
        entities = []
        
        if not self.presidio_analyzer:
            return entities
        
        try:
            results = self.presidio_analyzer.analyze(text=text, language="en")
            
            for result in results:
                pii_entity = PIIEntity(
                    text=text[result.start:result.end],
                    pii_type=result.entity_type,
                    confidence=result.score,
                    start=result.start,
                    end=result.end,
                    page_num=0,  # Will be set by caller
                    source="Presidio",
                    suggested_strategy=self._suggest_strategy(result.entity_type)
                )
                
                entities.append(pii_entity)
        
        except Exception as e:
            logger.error(f"Presidio detection error: {e}")
        
        return entities
    
    def detect_pii_with_regex(self, text: str) -> List[PIIEntity]:
        """Detect PII using custom regex patterns."""
        entities = []
        
        for pii_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        # Skip false positives
                        if self._is_false_positive(match.group(), text, match.start()):
                            continue
                        
                        pii_entity = PIIEntity(
                            text=match.group(),
                            pii_type=pii_type,
                            confidence=0.8,  # Default confidence for regex matches
                            start=match.start(),
                            end=match.end(),
                            page_num=0,  # Will be set by caller
                            source="Regex",
                            suggested_strategy=self._suggest_strategy(pii_type)
                        )
                        
                        entities.append(pii_entity)
                
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {pii_type}: {e}")
        
        return entities
    
    def verify_with_llm(self, entities: List[PIIEntity], full_text: str) -> List[PIIEntity]:
        """Use Gemini LLM to verify detected PII and find missed entities."""
        if not self.gemini_llm or not entities:
            return entities
        
        try:
            # Prepare context for LLM
            context_data = []
            for entity in entities:
                # Get surrounding context
                start_context = max(0, entity.start - 50)
                end_context = min(len(full_text), entity.end + 50)
                context = full_text[start_context:end_context]
                
                context_data.append({
                    "text": entity.text,
                    "type": entity.pii_type,
                    "context": context,
                    "confidence": entity.confidence,
                    "source": entity.source
                })
            
            # Create LLM prompt
            prompt_content = self._create_llm_verification_prompt(context_data, full_text)
            
            # Create messages for Gemini
            messages = [
                SystemMessage(content="You are an expert in PII detection and privacy compliance. You help identify personally identifiable information and reduce false positives. Identify all types of PII with all the compliance requirements. You have to detect all types like Company Names, Locations, Dates, Phone Numbers, Emails, IP Addresses, Credit Card Numbers, Social Security Numbers, Health Information, etc. "),
                HumanMessage(content=prompt_content)
            ]
            
            # Call Gemini LLM
            response = self.gemini_llm.invoke(messages)
            
            # Parse LLM response
            verified_entities = self._parse_llm_response(response.content, entities)
            
            return verified_entities
        
        except Exception as e:
            logger.error(f"Gemini LLM verification error: {e}")
            return entities
    
    def _create_llm_verification_prompt(self, context_data: List[Dict], full_text: str) -> str:
        """Create a prompt for LLM verification."""
        prompt = """I need you to verify PII entities detected in a document and identify any missed PII.

DETECTED ENTITIES:
"""
        
        for i, entity in enumerate(context_data, 1):
            prompt += f"""
{i}. Text: "{entity['text']}"
   Type: {entity['type']}
   Confidence: {entity['confidence']:.2f}
   Source: {entity['source']}
   Context: "...{entity['context']}..."
"""
        
        prompt += f"""

FULL DOCUMENT (truncated if long):
{full_text[:2000]}{"..." if len(full_text) > 2000 else ""}

Please analyze each detected entity and:
1. Confirm if it's truly PII (true positive) or a false positive
2. Suggest the severity level (low/medium/high)
3. Identify any PII entities that were missed

Respond in JSON format:
{{
  "verified_entities": [
    {{
      "text": "entity text",
      "is_pii": true/false,
      "severity": "low/medium/high",
      "reasoning": "brief explanation"
    }}
  ],
  "missed_entities": [
    {{
      "text": "missed entity text",
      "type": "PII_TYPE",
      "severity": "low/medium/high",
      "reasoning": "why this is PII"
    }}
  ]
}}"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, original_entities: List[PIIEntity]) -> List[PIIEntity]:
        """Parse LLM verification response."""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_text = response_text[json_start:json_end]
            
            response_data = json.loads(json_text)
            
            # Update original entities based on verification
            verified_entities = []
            verified_data = response_data.get('verified_entities', [])
            
            for i, entity in enumerate(original_entities):
                if i < len(verified_data):
                    verification = verified_data[i]
                    entity.verified_by_llm = True
                    entity.is_false_positive = not verification.get('is_pii', True)
                    entity.severity = verification.get('severity', 'medium')
                    
                    if not entity.is_false_positive:
                        verified_entities.append(entity)
                else:
                    verified_entities.append(entity)
            
            # Add missed entities
            missed_entities = response_data.get('missed_entities', [])
            for missed in missed_entities:
                # Find the missed entity in the text
                # This is a simplified implementation
                # In practice, you'd need more sophisticated text matching
                pass
            
            return verified_entities
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return original_entities
    
    def _is_valid_bert_entity(self, entity: Dict[str, Any]) -> bool:
        """Filter out invalid BERT entities."""
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
        
        return word.lower() not in non_pii_terms
    
    def _map_bert_entity_type(self, bert_type: str) -> str:
        """Map BERT entity types to our PII types."""
        mapping = {
            'PER': 'PERSON',
            'ORG': 'ORGANIZATION', 
            'LOC': 'LOCATION',
            'MISC': 'MISCELLANEOUS'
        }
        return mapping.get(bert_type, bert_type)
    
    def _is_false_positive(self, text: str, full_text: str, start_pos: int) -> bool:
        """Check if detected text is likely a false positive."""
        text_lower = text.lower()
        
        # Check against false positive patterns
        for pattern in self.false_positive_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Context-based filtering
        context_start = max(0, start_pos - 20)
        context_end = min(len(full_text), start_pos + len(text) + 20)
        context = full_text[context_start:context_end].lower()
        
        # Skip if in certain contexts
        false_contexts = ['page', 'figure', 'table', 'section', 'chapter', 'version']
        for ctx in false_contexts:
            if ctx in context:
                return True
        
        return False
    
    def _suggest_strategy(self, pii_type: str) -> str:
        """Suggest masking strategy based on PII type."""
        # High-sensitivity PII - redact completely
        high_sensitivity = {
            "SSN", "CREDIT_CARD", "BANK_ACCOUNT", "AADHAAR", "PASSPORT",
            "DRIVER_LICENSE", "MEDICAL_RECORD", "INSURANCE_POLICY"
        }
        
        if pii_type in high_sensitivity:
            return "redact"
        
        # Names and organizations - pseudo replacement
        pseudo_types = {"PERSON", "ORGANIZATION", "ORG", "PER"}
        if pii_type in pseudo_types:
            return "pseudo"
        
        # Contact information - mask
        mask_types = {"EMAIL", "EMAIL_ADDRESS", "PHONE", "PHONE_NUMBER"}
        if pii_type in mask_types:
            return "mask"
        
        # Locations - pseudo replacement
        location_types = {"LOCATION", "LOC", "ADDRESS"}
        if pii_type in location_types:
            return "pseudo"
        
        # Default to redaction
        return "redact"
    
    def merge_overlapping_entities(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Merge overlapping PII entities and resolve conflicts."""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        merged = []
        
        for current in sorted_entities:
            if not merged:
                merged.append(current)
                continue
            
            last = merged[-1]
            
            # Check for overlap
            if current.start <= last.end:
                # Merge overlapping entities
                # Keep the one with higher confidence or from more reliable source
                if self._should_replace_entity(last, current):
                    # Replace last entity with current
                    merged[-1] = current
                    # Update coordinates to cover both
                    merged[-1].start = min(last.start, current.start)
                    merged[-1].end = max(last.end, current.end)
                    merged[-1].text = merged[-1].text  # Keep current text
                # else keep the last entity
            else:
                merged.append(current)
        
        return merged
    
    def _should_replace_entity(self, existing: PIIEntity, new: PIIEntity) -> bool:
        """Determine which entity to keep when merging overlaps."""
        # Priority: LLM verified > Higher confidence > Better source
        
        # LLM verified entities take precedence
        if new.verified_by_llm and not existing.verified_by_llm:
            return True
        if existing.verified_by_llm and not new.verified_by_llm:
            return False
        
        # Higher confidence wins
        if new.confidence > existing.confidence:
            return True
        if existing.confidence > new.confidence:
            return False
        
        # Source priority: BERT > Presidio > Regex
        source_priority = {"BERT": 3, "Presidio": 2, "Regex": 1}
        existing_priority = source_priority.get(existing.source, 0)
        new_priority = source_priority.get(new.source, 0)
        
        return new_priority > existing_priority
    
    def extract_text_with_coordinates(self, pdf_path: str) -> List[Tuple[str, int, Any]]:
        """Extract text with coordinates from PDF."""
        pages_data = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                pages_data.append((text, page_num, doc))
            
            return pages_data
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return []
    
    def find_entity_coordinates(self, page, entity: PIIEntity) -> PIIEntity:
        """Find PDF coordinates for a detected entity."""
        try:
            # Search for the entity text in the page
            text_instances = page.search_for(entity.text)
            
            if text_instances:
                # Take the first instance (could be improved with context matching)
                rect = text_instances[0]
                entity.x0 = float(rect.x0)
                entity.y0 = float(rect.y0)
                entity.x1 = float(rect.x1)
                entity.y1 = float(rect.y1)
            
        except Exception as e:
            logger.warning(f"Could not find coordinates for entity '{entity.text}': {e}")
        
        return entity
    
    def detect_all_pii(self, text: str, page_num: int = 0, page_obj: Any = None) -> List[PIIEntity]:
        """
        Comprehensive PII detection using all available methods.
        
        Args:
            text: Text to analyze
            page_num: PDF page number
            page_obj: PDF page object for coordinate detection
            
        Returns:
            List of detected and verified PII entities
        """
        all_entities = []
        
        # Detect with BERT
        bert_entities = self.detect_pii_with_bert(text)
        for entity in bert_entities:
            entity.page_num = page_num
        all_entities.extend(bert_entities)
        
        # Detect with Presidio
        presidio_entities = self.detect_pii_with_presidio(text)
        for entity in presidio_entities:
            entity.page_num = page_num
        all_entities.extend(presidio_entities)
        
        # Detect with Regex
        regex_entities = self.detect_pii_with_regex(text)
        for entity in regex_entities:
            entity.page_num = page_num
        all_entities.extend(regex_entities)
        
        # Merge overlapping entities
        merged_entities = self.merge_overlapping_entities(all_entities)
        
        # Find coordinates for each entity
        if page_obj:
            for entity in merged_entities:
                entity = self.find_entity_coordinates(page_obj, entity)
        
        # Verify with LLM if available
        if self.gemini_llm and merged_entities:
            merged_entities = self.verify_with_llm(merged_entities, text)
        
        # Filter out false positives
        final_entities = [e for e in merged_entities if not e.is_false_positive]
        
        logger.info(f"Page {page_num}: Detected {len(final_entities)} PII entities after verification")
        
        return final_entities
    
    def generate_detection_report(self, all_entities: List[PIIEntity]) -> Dict[str, Any]:
        """Generate comprehensive detection report."""
        report = {
            "total_entities": len(all_entities),
            "by_type": {},
            "by_source": {},
            "by_severity": {},
            "verification_stats": {
                "llm_verified": 0,
                "false_positives_found": 0
            }
        }
        
        for entity in all_entities:
            # Count by type
            report["by_type"][entity.pii_type] = report["by_type"].get(entity.pii_type, 0) + 1
            
            # Count by source
            report["by_source"][entity.source] = report["by_source"].get(entity.source, 0) + 1
            
            # Count by severity
            report["by_severity"][entity.severity] = report["by_severity"].get(entity.severity, 0) + 1
            
            # Verification stats
            if entity.verified_by_llm:
                report["verification_stats"]["llm_verified"] += 1
            if entity.is_false_positive:
                report["verification_stats"]["false_positives_found"] += 1
        
        return report

def main():
    """Test the enhanced PII detector with the provided sample text."""
    sample_text = """Fictional PII Test Document
Fictional test document — all data below is made-up and intended for PII masking tests.
My name is Aaron Mehta. I was born on 12/07/1989 and I grew up on 221B Meadow Lane, Flat
4A, Greenfield Towers, Newtown, NY 10001. People call me Aaron or A. Mehta. My passport
number is X1234567, and my driver's license reads DL-NY-0987654321. At home my phone
rings on +1 (212) 555-0198 and my mobile is +91 98765 43210. My work email is
aaron.mehta@example-test.com and my personal email is a.mehta89@mailtest.co."""
    
    # Initialize detector
    detector = EnhancedPIIDetector()
    
    # Detect PII
    entities = detector.detect_all_pii(sample_text)
    
    # Generate report
    report = detector.generate_detection_report(entities)
    
    print("Enhanced PII Detection Results:")
    print("=" * 50)
    print(f"Total entities detected: {len(entities)}")
    
    for entity in entities:
        print(f"\nText: '{entity.text}'")
        print(f"Type: {entity.pii_type}")
        print(f"Confidence: {entity.confidence:.3f}")
        print(f"Source: {entity.source}")
        print(f"Strategy: {entity.suggested_strategy}")
        print(f"Severity: {entity.severity}")
        if entity.verified_by_llm:
            print("✓ LLM Verified")
    
    print(f"\nDetection Report:")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
