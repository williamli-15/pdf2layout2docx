# Script to use ppocr_api
# Required packages
# python3 -m pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
# pip install "paddleocr>=2.0.1"

# filename: ppocr_api.py
from paddleocr import PaddleOCR, draw_ocr
import fitz
import json
from PIL import Image
import cv2
import numpy as np

def process_pages(input_file):

    with fitz.open(input_file) as pdf:
        PAGE_NUM = len(pdf)  # Determine the number of pages

        # Initialize PaddleOCR with the correct number of pages
        ocr = PaddleOCR(use_angle_cls=True, lang="en", page_num=PAGE_NUM)  # Modify lang as needed, see Abbreviation
        # ocr = PaddleOCR(use_angle_cls=True, lang="ch", page_num=PAGE_NUM, use_gpu=0) # To Use GPU, uncomment this line and comment the above one.

        # Process the entire PDF through OCR
        result = ocr.ocr(input_file, cls=True)

        # Initialize the JSON structure as per prebuilt-read model
        json_output = {
            # "api_version": "",
            # "model_id": "",
            # "content": "",
            # "languages": [],
            "pages": [],
            # "paragraphs": [],
            # "tables": [],
            # "key_value_pairs": [],
            # "styles": [],
            # "documents": []
        }

        for pg in range(0, PAGE_NUM):
            page = pdf[pg]
            scale_factor = 2
            mat = fitz.Matrix(scale_factor, scale_factor)
            pm = page.get_pixmap(matrix=mat, alpha=False)

            # if width or height > 2000 pixels, don't enlarge the image
            if pm.width > 2000 or pm.height > 2000:
                scale_factor = 1
                mat = fitz.Matrix(scale_factor, scale_factor)
                pm = page.get_pixmap(matrix=mat, alpha=False)

            dpi = 72 * scale_factor  # Adjust DPI based on the actual scale factor used
            img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
            img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            res = result[pg]  # Fetch the OCR result for the current page
            if res is None:  # Skip when empty result detected to avoid TypeError:NoneType
                print(f"[DEBUG] Empty page {pg+1} detected, skip it.")
                continue
            boxes = [line[0] for line in res]
            txts = [line[1][0] for line in res]

            page_data = {
                "page_number": pg + 1,  # Page numbers start from 1
                # "angle": None,  # TODO: Actually not always None, check Azure doc
                "width": pm.width / dpi,
                "height": pm.height / dpi,
                # "unit": "inch",
                "lines": [],
                "words": [],
                # "selection_marks": [],
                # "spans": [],
                # "barcodes": [],
                # "formulas": []
            }

            # Calculate and append line data for each text-box pair
            for box, txt in zip(boxes, txts):
                line_data = {
                    "content": txt,
                    "polygon": [
                        {"x": (coord[0] / dpi), "y": (coord[1] / dpi)} for coord in box
                    ]
                }
                page_data["lines"].append(line_data)

            # Add the formatted page data to the JSON structure
            json_output["pages"].append(page_data)
    return json_output

def main(input_pdf: str) -> dict:
    print(f"Starting OCR process...")
    return process_pages(input_pdf)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Process PDF with OCR and generate JSON output.")
    parser.add_argument('input_pdf', type=str, help="Input PDF file path")
    args = parser.parse_args()
    processed_json = main(args.input_pdf)
    # Save or print the JSON
    # print(json.dumps(processed_json, indent=4))
    with open("output.json", "w") as json_file:
        json.dump(processed_json, json_file, indent=4)
    
