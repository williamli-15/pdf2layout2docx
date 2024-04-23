from is_pdf_searchable import is_searchable_pdf

import subprocess
import sys
import os

def convert_pdf_to_word(pdf_path, output_path):
    """Converts a searchable PDF to a Word document."""
    from pdf2docx import Converter
    cv = Converter(pdf_path)
    cv.convert(output_path)
    cv.close()
    print(f"Converted {pdf_path} to {output_path}")

def generate_searchable_pdf(input_file, output_file):
    """Calls an external script to generate a searchable PDF and returns the path of the output."""
    subprocess.run(['python', 'generate_searchable_pdf.py', input_file, '-o', output_file], check=True)
    print(f"Generated searchable PDF at {output_file}")
    return output_file

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert PDF to Word or make it searchable if it's not already.")
    parser.add_argument('pdf_path', type=str, help="Path to the PDF file.")
    parser.add_argument('--output_path', type=str, default=None, help="Path where the output DOCX or searchable PDF will be saved. Defaults to the same name with a .docx extension.")
    args = parser.parse_args()

    # Set the default output path if not specified
    if args.output_path is None:
        base_name = os.path.splitext(args.pdf_path)[0]
        args.output_path = f"{base_name}.docx"

    if is_searchable_pdf(args.pdf_path):
        convert_pdf_to_word(args.pdf_path, args.output_path)
    else:
        print("PDF is not searchable. Generating a searchable PDF first.")
        searchable_pdf_path = generate_searchable_pdf(args.pdf_path, f"{os.path.splitext(args.pdf_path)[0]}_searchable.pdf")
        # Once the searchable PDF is generated, convert it to Word
        convert_pdf_to_word(searchable_pdf_path, args.output_path)

if __name__ == '__main__':
    main()
