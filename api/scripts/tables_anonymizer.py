#!/usr/bin/env python3
"""
Enhanced PDF Anonymizer with OCR Support
Handles both text-based and image-based PDFs with comprehensive anonymization
"""

import fitz  # PyMuPDF
import os
import re
import random
from faker import Faker
import pytesseract
from PIL import Image
import numpy as np
import cv2
from io import BytesIO

class EnhancedPDFAnonymizer:
    """
    Enhanced PDF anonymizer with OCR support for both text and image-based content
    """

    def __init__(self, debug_mode=False):
        self.fake = Faker()
        self.debug_mode = debug_mode
        print("🔢📝🖼️ Enhanced PDF Anonymizer with OCR initialized")

        # Configure OCR
        try:
            pytesseract.get_tesseract_version()
            print("✅ Tesseract OCR detected")
        except Exception as e:
            print(f"⚠️ Tesseract not found: {e}")
            print("📝 OCR functionality will be limited to text-based PDFs")

    def analyze_pdf_structure(self, pdf_path):
        """
        Analyze PDF structure including both text and images
        """
        print("🔍 Analyzing PDF structure (text + images)...")

        doc = fitz.open(pdf_path)
        structure = {
            'pages': [],
            'fonts': set(),
            'font_sizes': set(),
            'colors': set(),
            'has_images': False
        }

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"📄 Analyzing page {page_num + 1}/{len(doc)}...")

            page_info = {
                'number': page_num,
                'width': page.rect.width,
                'height': page.rect.height,
                'text_blocks': [],
                'image_blocks': []
            }

            # Extract text information (existing functionality)
            text_dict = page.get_text("dict")
            for block in text_dict.get('blocks', []):
                if 'lines' in block:
                    for line in block['lines']:
                        for span in line['spans']:
                            structure['fonts'].add(span.get('font', 'Unknown'))
                            structure['font_sizes'].add(span.get('size', 12))
                            structure['colors'].add(span.get('color', 0))

                            text_block = {
                                'text': span.get('text', ''),
                                'bbox': span.get('bbox', [0, 0, 0, 0]),
                                'font': span.get('font', 'Unknown'),
                                'size': span.get('size', 12),
                                'color': span.get('color', 0),
                                'source': 'text',
                                'page_num': page_num
                            }
                            page_info['text_blocks'].append(text_block)

            # Extract images for OCR processing
            image_list = page.get_images(full=True)
            if image_list:
                structure['has_images'] = True
                print(f"🖼️ Found {len(image_list)} images on page {page_num + 1}")

                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Get image position on page
                        img_rect = page.get_image_bbox(img_info)
                        if img_rect:
                            image_block = {
                                'image_data': image_bytes,
                                'bbox': [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                                'format': base_image.get('ext', 'png'),
                                'index': img_index,
                                'source': 'image'
                            }
                            page_info['image_blocks'].append(image_block)
                    except Exception as e:
                        print(f"⚠️ Failed to extract image {img_index}: {e}")

            structure['pages'].append(page_info)

        doc.close()

        print(f"📊 Structure Analysis Complete:")
        print(f"   - Fonts found: {list(structure['fonts'])}")
        print(f"   - Font sizes: {sorted(list(structure['font_sizes']))}")
        print(f"   - Pages analyzed: {len(structure['pages'])}")
        print(f"   - Contains images: {structure['has_images']}")

        return structure

    def extract_text_from_image(self, image_data, image_bbox):
        """
        Extract text from image using OCR with improved accuracy
        """
        try:
            # Convert image data to PIL Image
            image = Image.open(BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Enhanced preprocessing for better OCR accuracy
            img_array = np.array(image)

            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Apply bilateral filter to reduce noise while keeping edges sharp
            filtered = cv2.bilateralFilter(gray, 11, 17, 17)

            # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(filtered)

            # Apply morphological operations to clean up the image
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

            # Try multiple threshold methods
            _, binary_otsu = cv2.threshold(cleaned, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            binary_adaptive = cv2.adaptiveThreshold(cleaned, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

            # Use the better contrast image
            processed_image = Image.fromarray(binary_otsu)

            # Get OCR data with bounding boxes
            ocr_data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT, config='--psm 6')

            text_blocks = []
            n_boxes = len(ocr_data['text'])

            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])

                # Lower threshold for better detection, but filter very low confidence
                if text and confidence > 15:  # Even lower threshold
                    # Convert image coordinates to PDF coordinates
                    img_x = int(ocr_data['left'][i])
                    img_y = int(ocr_data['top'][i])
                    img_w = int(ocr_data['width'][i])
                    img_h = int(ocr_data['height'][i])

                    # Scale to PDF coordinates with better precision
                    scale_x = (image_bbox[2] - image_bbox[0]) / processed_image.width
                    scale_y = (image_bbox[3] - image_bbox[1]) / processed_image.height

                    pdf_x0 = image_bbox[0] + (img_x * scale_x)
                    pdf_y0 = image_bbox[1] + (img_y * scale_y)
                    pdf_x1 = pdf_x0 + (img_w * scale_x)
                    pdf_y1 = pdf_y0 + (img_h * scale_y)

                    text_block = {
                        'text': text,
                        'bbox': [pdf_x0, pdf_y0, pdf_x1, pdf_y1],
                        'font': 'OCR_Text',
                        'size': 12,
                        'color': 0,
                        'source': 'ocr',
                        'confidence': int(ocr_data['conf'][i])
                    }
                    text_blocks.append(text_block)

            return text_blocks

        except Exception as e:
            print(f"⚠️ OCR failed: {e}")
            return []

    def detect_numerical_values(self, text_blocks):
        """
        Detect numerical values from both text and OCR sources with improved patterns
        """
        print("🔍 Detecting numerical values (text + OCR)...")

        # More comprehensive numerical patterns - ordered by specificity
        numerical_patterns = [
            re.compile(r'\$[\d,]+\.?\d*'),  # $ amounts (highest priority)
            re.compile(r'\b\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\b'),  # large numbers with commas and optional decimals
            re.compile(r'\b\d+\.\d{1,2}\b'),  # decimals (complete)
            re.compile(r'\b\d{2,}\b'),  # general numbers (2+ digits, lowered threshold)
            re.compile(r'\b\d{1,2}(?:,\d{3})+(?:\.\d{1,2})?\b'),  # smaller numbers with commas (like 1,234)
        ]

        numerical_items = []
        total_matches = 0
        filtered_out = 0

        if self.debug_mode:
            print(f"   📊 Processing {len(text_blocks)} text blocks for numerical detection")

        for block in text_blocks:
            text = block['text']
            bbox = block['bbox']
            matched_positions = set()

            if self.debug_mode and text.strip():
                print(f"   🔍 Processing text: '{text}' (source: {block.get('source', 'unknown')})")

            for pattern in numerical_patterns:
                for match in pattern.finditer(text):
                    num_value = match.group()
                    start_pos = match.start()
                    end_pos = match.end()

                    # Check if this match overlaps with any previously matched position
                    overlap_found = False
                    for matched_start, matched_end in matched_positions:
                        if not (end_pos <= matched_start or start_pos >= matched_end):
                            overlap_found = True
                            break

                    if overlap_found:
                        continue

                    total_matches += 1

                    # More intelligent filtering
                    clean_value = num_value.replace('$', '').replace(',', '').replace('.', '')

                    should_exclude = False

                    # Only exclude very obvious non-sensitive patterns
                    if len(clean_value) == 1:
                        should_exclude = True  # Single digits
                    elif len(clean_value) == 4 and clean_value.isdigit():
                        year_val = int(clean_value)
                        # Only exclude if it's clearly a year (1900-2100)
                        if 1900 <= year_val <= 2100:
                            should_exclude = True
                    elif len(clean_value) == 2 and clean_value.isdigit():
                        num_val = int(clean_value)
                        # Only exclude obvious page numbers, not all 2-digit numbers
                        if num_val <= 50:  # Page numbers typically <= 50
                            should_exclude = True

                    if should_exclude:
                        filtered_out += 1
                        continue

                    matched_positions.add((start_pos, end_pos))

                    # Calculate position with better precision
                    if len(text) > 0:
                        char_width = (bbox[2] - bbox[0]) / len(text)
                        x_offset = start_pos * char_width
                        width = (end_pos - start_pos) * char_width
                    else:
                        x_offset = 0
                        width = bbox[2] - bbox[0]

                    precise_bbox = [
                        bbox[0] + x_offset,
                        bbox[1],
                        bbox[0] + x_offset + width,
                        bbox[3]
                    ]

                    numerical_items.append({
                        'type': 'numerical',
                        'value': num_value,
                        'text_block': block,
                        'precise_bbox': precise_bbox,
                        'context': text,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'source': block.get('source', 'text')
                    })

        print(f"🎯 Found {len(numerical_items)} numerical values")
        print(f"   📊 Total matches found: {total_matches}")
        print(f"   🚫 Filtered out: {filtered_out}")
        return numerical_items

    def detect_proper_nouns(self, text_blocks):
        """
        Detect proper nouns from both text and OCR sources with improved patterns
        """
        print("🔍 Detecting proper nouns (text + OCR)...")

        # More comprehensive name patterns
        name_patterns = [
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First Last
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+\b'),  # First M. Last
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First Middle Last
            re.compile(r'\b[A-Z][a-z]+-[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First-Last Name
            re.compile(r'\b[A-Z]\.\s*[A-Z][a-z]+\b'),  # F. Lastname
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z]\.\b'),  # First M. L.
        ]

        # More comprehensive address patterns
        address_patterns = [
            re.compile(r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|Circle|Cir|Square|Sq|Park|Pkwy|Highway|Hwy|Freeway|Fwy)\b'),
            re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b'),  # City, ST ZIP
            re.compile(r'\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|Circle|Cir|Square|Sq|Park|Pkwy|Highway|Hwy|Freeway|Fwy)\b'),
            re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[A-Z]{2}\s*\d{5}\b'),  # City State ZIP
        ]

        # Additional patterns for organizations and companies
        organization_patterns = [
            re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|LLC|Corp|Corporation|Company|Co|Ltd|Limited|GmbH|AG|SA|SAS)\b'),
            re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Bank|Insurance|Financial|Trust|Credit|Union|Savings)\b'),
        ]

        proper_noun_items = []
        total_matches = 0
        filtered_out = 0

        for block in text_blocks:
            text = block['text']
            bbox = block['bbox']
            matched_positions = set()

            # Check all pattern types
            all_patterns = name_patterns + address_patterns + organization_patterns

            for pattern in all_patterns:
                for match in pattern.finditer(text):
                    value = match.group()
                    start_pos = match.start()
                    end_pos = match.end()

                    overlap_found = False
                    for matched_start, matched_end in matched_positions:
                        if not (end_pos <= matched_start or start_pos >= matched_end):
                            overlap_found = True
                            break

                    if overlap_found:
                        continue

                    total_matches += 1

                    # Less aggressive filtering for proper nouns
                    should_exclude = False

                    # Only exclude very obvious non-proper nouns
                    if len(value.split()) == 1 and len(value) < 4:
                        should_exclude = True  # Very short single words
                    elif value.lower() in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'has', 'let', 'put', 'say', 'she', 'too', 'use']:
                        should_exclude = True  # Common words that might match patterns

                    if should_exclude:
                        filtered_out += 1
                        continue

                    matched_positions.add((start_pos, end_pos))

                    # Determine type based on pattern
                    if pattern in name_patterns:
                        item_type = 'name'
                    elif pattern in address_patterns:
                        item_type = 'address'
                    else:
                        item_type = 'organization'

                    # Calculate position with better precision
                    if len(text) > 0:
                        char_width = (bbox[2] - bbox[0]) / len(text)
                        x_offset = start_pos * char_width
                        width = (end_pos - start_pos) * char_width
                    else:
                        x_offset = 0
                        width = bbox[2] - bbox[0]

                    precise_bbox = [
                        bbox[0] + x_offset,
                        bbox[1],
                        bbox[0] + x_offset + width,
                        bbox[3]
                    ]

                    proper_noun_items.append({
                        'type': item_type,
                        'value': value,
                        'text_block': block,
                        'precise_bbox': precise_bbox,
                        'context': text,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'source': block.get('source', 'text')
                    })

        print(f"🎯 Found {len(proper_noun_items)} proper nouns")
        print(f"   📊 Total matches found: {total_matches}")
        print(f"   🚫 Filtered out: {filtered_out}")
        return proper_noun_items

    def generate_replacement(self, original_value):
        """Generate replacement for numerical values"""
        try:
            if '$' in original_value:
                base = float(original_value.replace('$', '').replace(',', ''))
                new_value = base * (0.8 + random.random() * 0.4)
                return f"${new_value:,.2f}"
            elif '.' in original_value:
                base = float(original_value.replace(',', ''))
                new_value = base * (0.8 + random.random() * 0.4)
                return f"{new_value:.2f}"
            else:
                base = float(original_value.replace(',', ''))
                new_value = int(base * (0.8 + random.random() * 0.4))
                return f"{new_value:,}"
        except:
            return '*' * len(original_value)

    def generate_proper_noun_replacement(self, original_value, item_type):
        """Generate replacement for proper nouns"""
        try:
            if item_type == 'name':
                fake_name = self.fake.name()
                return fake_name
            elif item_type == 'address':
                fake_address = self.fake.address().replace('\n', ', ')
                return fake_address
            else:
                return '*' * len(original_value)
        except:
            return '*' * len(original_value)

    def get_safe_font(self, original_font):
        """Map fonts to safe alternatives"""
        font_mapping = {
            'georgia': 'helv',
            'Georgia': 'helv',
            'verdana': 'helv',
            'Verdana': 'helv',
            'trebuchet': 'helv',
            'TrebuchetMS': 'helv',
        }
        return font_mapping.get(original_font, 'helv')

    def bboxes_overlap(self, bbox1, bbox2, threshold=2):
        """Check if two bounding boxes overlap"""
        return not (bbox1.x1 + threshold < bbox2.x0 or
                   bbox1.x0 - threshold > bbox2.x1 or
                   bbox1.y1 + threshold < bbox2.y0 or
                   bbox1.y0 - threshold > bbox2.y1)

    def apply_anonymization(self, input_pdf, output_pdf):
        """
        Apply comprehensive anonymization with OCR support
        """
        print("🔢📝🖼️ Applying comprehensive anonymization (text + OCR)...")

        structure = self.analyze_pdf_structure(input_pdf)

        # Collect all text blocks (from both text and OCR)
        all_text_blocks = []

        for page_info in structure['pages']:
            all_text_blocks.extend(page_info['text_blocks'])

            # Process images with OCR
            for image_block in page_info['image_blocks']:
                print(f"🖼️ Processing image with OCR...")
                ocr_text_blocks = self.extract_text_from_image(
                    image_block['image_data'],
                    image_block['bbox']
                )
                all_text_blocks.extend(ocr_text_blocks)
                print(f"   📝 OCR extracted {len(ocr_text_blocks)} text blocks")
                if self.debug_mode and ocr_text_blocks:
                    print("📝 Extracted text samples:")
                    for i, block in enumerate(ocr_text_blocks):
                        print(f"   Block {i+1}: '{block['text']}' (confidence: {block.get('confidence', 'N/A')})")

        # Detect all sensitive items
        all_items = []
        numerical_items = self.detect_numerical_values(all_text_blocks)
        all_items.extend(numerical_items)

        proper_noun_items = self.detect_proper_nouns(all_text_blocks)
        all_items.extend(proper_noun_items)

        if not all_items:
            print("ℹ️ No sensitive data detected")
            return

        # Group items by page
        items_by_page = {}
        for item in all_items:
            page_num = item.get('text_block', {}).get('page_num', 0)
            if page_num not in items_by_page:
                items_by_page[page_num] = []
            items_by_page[page_num].append(item)

        # Apply anonymization
        doc = fitz.open(input_pdf)

        total_numerical = 0
        total_proper_nouns = 0
        total_failed = 0

        for page_num, items in items_by_page.items():
            if page_num >= len(doc):
                continue

            page = doc[page_num]
            print(f"📝 Processing page {page_num + 1} with {len(items)} items...")

            items.sort(key=lambda x: (x['precise_bbox'][1], x['precise_bbox'][0]))

            applied_bboxes = []
            applied_count = 0
            skipped_count = 0
            page_numerical = 0
            page_proper_nouns = 0
            page_failed = 0

            for item in items:
                bbox = fitz.Rect(item['precise_bbox'])

                # Check for overlaps with better logic
                overlap_detected = False
                for applied_bbox in applied_bboxes:
                    if self.bboxes_overlap(bbox, applied_bbox, threshold=2.0):  # Slightly more tolerant
                        overlap_detected = True
                        if self.debug_mode:
                            print(f"⚠️  Skipping overlapping item: '{item['value']}' ({item['type']}) from {item.get('source', 'unknown')}")
                            print(f"   📍 Original bbox: {bbox}")
                            print(f"   📍 Applied bbox: {applied_bbox}")
                        break

                if overlap_detected:
                    skipped_count += 1
                    continue

                # Generate replacement
                if item['type'] == 'numerical':
                    replacement = self.generate_replacement(item['value'])
                    page_numerical += 1
                else:
                    replacement = self.generate_proper_noun_replacement(item['value'], item['type'])
                    page_proper_nouns += 1

                safe_font = self.get_safe_font(item['text_block'].get('font', 'helv'))

                expanded_bbox = fitz.Rect(
                    bbox.x0 - 1, bbox.y0,
                    bbox.x1 + 1, bbox.y1
                )

                # Try redaction strategies
                success = self._apply_redaction_with_fallbacks(
                    page, expanded_bbox, replacement, safe_font,
                    item['text_block'].get('size', 12), item, page_num
                )

                if success:
                    applied_bboxes.append(expanded_bbox)
                    applied_count += 1
                else:
                    page_failed += 1
                    total_failed += 1

            print(f"   ✅ Applied: {applied_count} redactions")
            print(f"   ⚠️  Skipped: {skipped_count} items")
            print(f"   ❌ Failed: {page_failed} items")
            print(f"   🔢 Numerical: {page_numerical}")
            print(f"   📝 Proper nouns: {page_proper_nouns}")

            total_numerical += page_numerical
            total_proper_nouns += page_proper_nouns

        # Apply redactions
        for page in doc:
            page.apply_redactions()

        doc.save(output_pdf, deflate=True, clean=True)
        doc.close()

        print(f"✅ Enhanced anonymization complete!")
        print(f"   📄 Saved to: {output_pdf}")
        print(f"   🔢 Numerical values anonymized: {total_numerical}")
        print(f"   📝 Proper nouns anonymized: {total_proper_nouns}")
        print(f"   🎯 Total items processed: {total_numerical + total_proper_nouns}")
        if total_failed > 0:
            print(f"   ⚠️  Total failed redactions: {total_failed}")

    def _apply_redaction_with_fallbacks(self, page, bbox, replacement, font, size, item, page_num):
        """Apply redaction with enhanced fallback strategies"""
        strategies = [
            {'bbox': bbox, 'font': font, 'size': size, 'replacement': replacement, 'description': 'original'},
            {'bbox': bbox, 'font': 'helv', 'size': size, 'replacement': replacement, 'description': 'fallback font'},
            {'bbox': fitz.Rect(item['text_block']['bbox']), 'font': 'helv', 'size': size, 'replacement': replacement, 'description': 'original bbox'},
            {'bbox': bbox, 'font': 'helv', 'size': max(8, size-2), 'replacement': replacement, 'description': 'smaller font'},
            {'bbox': bbox, 'font': 'helv', 'size': min(24, size+2), 'replacement': replacement, 'description': 'larger font'},
            {'bbox': fitz.Rect(bbox.x0-0.5, bbox.y0, bbox.x1+0.5, bbox.y1), 'font': 'helv', 'size': size, 'replacement': replacement, 'description': 'expanded bbox'},
            {'bbox': bbox, 'font': 'helv', 'size': size, 'replacement': '*' * len(item['value']), 'description': 'asterisks'},
            {'bbox': bbox, 'font': 'helv', 'size': size, 'replacement': '***', 'description': 'short replacement'}
        ]

        for strategy in strategies:
            try:
                page.add_redact_annot(
                    strategy['bbox'],
                    strategy['replacement'],
                    fontname=strategy['font'],
                    fontsize=strategy['size']
                )
                if strategy['description'] != 'original':
                    if self.debug_mode:
                        print(f"   ✅ Success with {strategy['description']} strategy")
                return True
            except Exception as e:
                if strategy['description'] == 'original' and self.debug_mode:
                    print(f"⚠️  Failed to add redaction for '{item['value']}' ({item['type']}): {e}")
                    print(f"   📍 Location: page {page_num + 1}, bbox: {bbox}")
                    print(f"   🔤 Font: {font}, Size: {size}")
                    print(f"   📝 Replacement: '{replacement}'")
                continue

        if self.debug_mode:
            print(f"   ❌ All redaction strategies failed for '{item['value']}'")
        return False

def main():
    """Main function"""
    import sys

    print("🔢📝🖼️ Enhanced PDF Anonymizer with OCR")
    print("=" * 45)

    if len(sys.argv) < 3:
        print("❌ Usage: python enhanced_anonymizer.py <input_pdf> <output_pdf> [--debug]")
        print("   --debug: Enable debug mode for detailed logging")
        return

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    debug_mode = '--debug' in sys.argv

    if not os.path.exists(input_pdf):
        print(f"❌ Input file not found: {input_pdf}")
        return

    anonymizer = EnhancedPDFAnonymizer(debug_mode=debug_mode)
    anonymizer.apply_anonymization(input_pdf, output_pdf)

if __name__ == "__main__":
    main()