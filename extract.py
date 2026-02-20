import os
import glob
import fitz  # pymupdf
import pdfplumber
from tqdm import tqdm

PDF_DIR = r"data/pdfs"
EXTRACTED_DIR = r"data/extracted"
# Fallback/Original directory
ORIGINAL_PDF_DIR = r"lahore highcourt judgements 1000 pdf folder"

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        # Try pymupdf first (faster)
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"Error with pymupdf for {pdf_path}: {e}")
        # Fallback to pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e2:
            print(f"Error with pdfplumber for {pdf_path}: {e2}")
            return None
    return text

def main():
    if not os.path.exists(EXTRACTED_DIR):
        os.makedirs(EXTRACTED_DIR)

    pdf_files = []
    
    # Check data/pdfs
    if os.path.exists(PDF_DIR):
        pdf_files.extend(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
        
    # Check original folder
    if os.path.exists(ORIGINAL_PDF_DIR):
        pdf_files.extend(glob.glob(os.path.join(ORIGINAL_PDF_DIR, "*.pdf")))

    # Remove duplicates if any (based on filename)
    seen = set()
    unique_files = []
    for f in pdf_files:
        name = os.path.basename(f)
        if name not in seen:
            seen.add(name)
            unique_files.append(f)
            
    pdf_files = unique_files

    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR} or {ORIGINAL_PDF_DIR}")
        return

    print(f"Found {len(pdf_files)} PDFs to process.")

    for pdf_path in tqdm(pdf_files):
        filename = os.path.basename(pdf_path)
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        txt_path = os.path.join(EXTRACTED_DIR, txt_filename)

        if os.path.exists(txt_path):
            continue

        text = extract_text_from_pdf(pdf_path)
        if text:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

if __name__ == "__main__":
    main()
