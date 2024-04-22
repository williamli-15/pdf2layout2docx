# filename: doctr_api.py
import os
import json
import torch
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

def convert_geometry(geometry, width_in_inches, height_in_inches):
    """Converts rectangle corners from PDF points to inches using pre-calculated scales."""
    (x1, y1), (x2, y2) = geometry
    return [
        {'x': round(x1 * width_in_inches, 4), 'y': round(y1 * height_in_inches, 4)},
        {'x': round(x2 * width_in_inches, 4), 'y': round(y1 * height_in_inches, 4)},
        {'x': round(x2 * width_in_inches, 4), 'y': round(y2 * height_in_inches, 4)},
        {'x': round(x1 * width_in_inches, 4), 'y': round(y2 * height_in_inches, 4)}
    ]

def process_pages(json_export):
    new_json = {"pages": []}
    for page in json_export['pages']:
        page_number = page['page_idx'] + 1
        dimensions = page['dimensions']
        width_in_inches = dimensions[1] / 144
        height_in_inches = dimensions[0] / 144
        
        page_content = {
            "page_number": page_number,
            "width": round(width_in_inches, 4),
            "height": round(height_in_inches, 4),
            "unit": "inch",
            "words": []
        }
        for block in page['blocks']:
            for line in block['lines']:
                for word in line['words']:
                    # Simplified function call
                    polygon = convert_geometry(word['geometry'], width_in_inches, height_in_inches)
                    word_data = {
                        "content": word['value'],
                        "polygon": polygon
                    }
                    page_content["words"].append(word_data)
        new_json["pages"].append(page_content)
    return new_json

def main(input_pdf: str) -> dict:
    os.environ['USE_TORCH'] = '1'
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    docs = DocumentFile.from_pdf(input_pdf)
    print(f"Starting OCR process...")
    predictor = ocr_predictor(pretrained=True).to(device)
    result = predictor(docs)
    return process_pages(result.export())

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Process PDF with OCR and generate JSON output.")
    parser.add_argument('input_pdf', type=str, help="Input PDF file path")
    args = parser.parse_args()
    processed_json = main(args.input_pdf)
    # print(json.dumps(processed_json, indent=4))
