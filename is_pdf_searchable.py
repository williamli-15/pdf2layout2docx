import argparse
import fitz  # PyMuPDF
import PyPDF2

def check_text_in_pdf(pdf_path):
    document = fitz.open(pdf_path)
    text_found = any(page.get_text("text").strip() for page in document)
    document.close()
    return text_found

def check_fonts_in_pdf(pdf_path):
    font_found = False
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        font_found = any('/Font' in page['/Resources'] for page in reader.pages)
    return font_found

def is_searchable_pdf(pdf_path):
    text_found = check_text_in_pdf(pdf_path)
    fonts_found = check_fonts_in_pdf(pdf_path)
    return text_found and fonts_found  # Simplified for importability

def main():
    parser = argparse.ArgumentParser(description="Classify PDF files as searchable or image-based.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to be classified.")
    args = parser.parse_args()

    if is_searchable_pdf(args.pdf_path):
        print(f"The PDF '{args.pdf_path}' is searchable.")
    else:
        print(f"The PDF '{args.pdf_path}' is image-based (scanned).")

if __name__ == '__main__':
    main()
