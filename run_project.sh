#!/bin/bash

# Install required packages
pip install pymupdf python-docx azure-ai-formrecognizer

# Clone the project repository
git clone https://github.com/williamli-15/pdf2layout2docx.git
cd pdf2layout2docx

# Create a folder for PDF files
mkdir -p docs

# Move PDF files to the 'docs' folder (replace 'pdf_files' with the actual path)
mv /path/to/pdf_files/*.pdf ./docs/

# Set Azure Form Recognizer endpoint URL and API key
export AZ_ENDPOINT="https://your-form-recognizer-endpoint-url/"
export AZ_KEY="your-form-recognizer-api-key"

# Obtain JSON files from PDFs
python obtain_json.py ./docs

# Process JSON files
python processing_json.py ./docs

# Convert PDFs to DOCX
python convert_main.py ./docs/your_pdf_file.pdf ./docs/your_json_file.json 0 2
