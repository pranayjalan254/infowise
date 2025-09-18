import time
import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

# ----- Setup -----
load_dotenv()
llm = ChatOllama(model="phi3:latest")

def correct_text(text):
    """Correct spelling and grammar using LLM"""
    messages = [
        SystemMessage(content="""You are an expert text corrector. Your task is to:
1. Fix spelling mistakes
2. Do not change layout of addresses or special formatting (like lists, bullet points, etc.)
3. Do not change sentences.

Return ONLY the corrected text without any explanations."""),
        HumanMessage(content=f"Correct this text:\n\n{text}")
    ]
    
    try:
        corrected = llm.invoke(messages).content.strip()
        return corrected
    except Exception as e:
        print(f"Error correcting text: {e}")
        return text  # Return original if correction fails

def create_text_file(corrected_pages, output_path):
    """Create text file from corrected text"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# OCR Extracted and Corrected Text\n")
            f.write("# This file was generated from a scanned PDF using OCR\n")
            f.write("# Each page is separated by === PAGE N === markers\n\n")
            
            # Add corrected text for each page
            for i, corrected_text in enumerate(corrected_pages, 1):
                if corrected_text.strip():
                    f.write(f"=== PAGE {i} ===\n")
                    f.write(corrected_text)
                    f.write("\n\n")
        
        print(f"✅ Corrected text file created: {output_path}")
    except Exception as e:
        print(f"❌ Error creating text file: {e}")
        raise

def process_pdf(input_pdf, output_text="corrected_output.txt"):
    """Main processing: PDF → OCR → LLM → Corrected Text File"""
    print(f"Processing: {input_pdf}")
    
    # Convert PDF to images
    pages = convert_from_path(input_pdf)
    corrected_pages = []
    
    for i, page in enumerate(pages, 1):
        print(f"Processing page {i}/{len(pages)}...")
        
        # Extract text with OCR
        raw_text = pytesseract.image_to_string(page)
        
        # Skip empty pages
        if not raw_text.strip():
            print(f"  Page {i} is empty, skipping...")
            continue
        
        print(f"  Extracted {len(raw_text)} characters")
        
        # Correct text with LLM
        print(f"  Correcting text...")
        corrected_text = correct_text(raw_text)
        corrected_pages.append(corrected_text)
        
        print(f"  ✅ Page {i} completed")
        
        # Small delay between pages
        if i < len(pages):
            time.sleep(1)
    
    # Create final corrected text file
    if corrected_pages:
        create_text_file(corrected_pages, output_text)
        print(f"🎉 Success! Corrected text saved as: {output_text}")
        return True
    else:
        print("❌ No text found to process")
        return False

# Example usage
if __name__ == "__main__":
    process_pdf("scan-sample.pdf", "scan-sample-corrected.txt")