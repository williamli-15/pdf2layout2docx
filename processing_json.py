import argparse
import json
import os
from PIL import Image, ImageDraw
import fitz  # PyMuPDF

def extract_font_and_page_info(pdf_path, target_page_number):
    font_info_list = []

    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(target_page_number - 1)  # Page numbers are 0-indexed

    page_info = page.get_text("dict")
    page_width = page_info["width"]
    page_height = page_info["height"]

    blocks = page_info["blocks"]

    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                line_bbox = [float('inf'), float('inf'), float('-inf'), float('-inf')]  # Initialize to extreme values
                line_text = ""
                for span in line["spans"]:
                    font_size = round(span["size"], 2)
                    font_name = span["font"]
                    text = span["text"]
                    bbox = span["bbox"]
                    line_text += text + " "  # Concatenate text from spans
                    # Update line bbox
                    line_bbox[0] = min(line_bbox[0], bbox[0])
                    line_bbox[1] = min(line_bbox[1], bbox[1])
                    line_bbox[2] = max(line_bbox[2], bbox[2])
                    line_bbox[3] = max(line_bbox[3], bbox[3])

                font_info = {
                    "Font Size": font_size,
                    "Font": font_name,
                    "Text": line_text.strip(),
                    "Bbox": line_bbox
                }
                font_info_list.append(font_info)

    return font_info_list, page_width, page_height


def extract_elements(data, page_number, extract_content=True, extract_polygon=True, extract_spans=True):
    filtered_pages = [page for page in data['pages'] if page['page_number'] == page_number]
    extracted_data = []

    for page in filtered_pages:
        extracted_page = {'page_number': page_number}  # Add page number to extracted data

        if extract_content:
            extracted_page['content'] = [line['content'] for line in page.get('lines', [])]

        if extract_polygon:
            extracted_page['polygon'] = [line['polygon'] for line in page.get('lines', [])]

        if extract_spans:
            extracted_page['spans'] = [line['spans'] for line in page.get('lines', [])]

        extracted_data.append(extracted_page)

    return extracted_data

def visualize_bbox(image, bbox_list, outline_color="red"):
    draw = ImageDraw.Draw(image)
    for bbox_entry in bbox_list:
        for bbox in bbox_entry:
            x0, y0, x1, y1 = bbox
            draw.rectangle([x0, y0, x1, y1], outline=outline_color)

def calculate_iou(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    x_intersection = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
    y_intersection = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
    intersection_area = x_intersection * y_intersection

    area_box1 = w1 * h1
    area_box2 = w2 * h2

    iou = intersection_area / (area_box1 + area_box2 - intersection_area)
    return iou

def populate_font_info(extracted_data, font_info):
    for item in extracted_data:
        item_bbox_list = item['Bbox']
        item['Font Size'] = []
        item['Font'] = []

        for item_bbox in item_bbox_list:
            font_size_list = []
            font_list = []

            for font_item in font_info:
                font_item_bbox = font_item['Bbox']
                iou = calculate_iou(item_bbox[0], font_item_bbox)

                if iou > 0.8:
                    font_size_list.append(font_item['Font Size'])
                    font_list.append(font_item['Font'])

            item['Font Size'].append(font_size_list)
            item['Font'].append(font_list)


def obtain_font_and_sizes(pdf_path, json_path):
    with open(json_path, 'r') as json_file:
        data = json.load(json_file)

    total_pages = len(data['pages'])

    extracted_data = []  # Initialize the list before the loop

    for target_page_number in range(1, total_pages + 1):  # Loop through all pages
        font_info_list, page_width, page_height = extract_font_and_page_info(pdf_path, target_page_number)
        page_data = extract_elements(data, target_page_number, extract_content=True, extract_polygon=True, extract_spans=False)

        # Convert 'polygon' format to 'Bbox' format, multiply points by 72, and round to 4 decimal places
        for entry in page_data:
            entry['Bbox'] = [
                [(round(72 * min(point['x'] for point in polygon), 4), round(72 * min(point['y'] for point in polygon), 4),
                  round(72 * max(point['x'] for point in polygon), 4), round(72 * max(point['y'] for point in polygon), 4))]
                for polygon in entry['polygon']
            ]
            del entry['polygon']

        # Call the function to populate font information
        populate_font_info(page_data, font_info_list)

        # Process Font Size
        for entry in page_data:
            if 'Font Size' in entry:
                # Check if each 'Font Size' list is not empty before extracting the first element
                entry['Font Size'] = [size[0] if size else None for size in entry['Font Size']]

        # Process Font
        for entry in page_data:
            if 'Font' in entry:
                # Check if each 'Font' list is not empty before extracting the first element
                entry['Font'] = [font[0] if font else None for font in entry['Font']]


        extracted_data.append(page_data[0])  # Add the processed data of the current page to the list

    return extracted_data



def process_pdf_json(pdf_path, json_path):
    # Load the JSON content into memory
    with open(json_path, "r") as file:
        data = json.load(file)

    extracted_data = obtain_font_and_sizes(pdf_path, json_path)

    # Match the content from extracted_data with the content in the JSON file
    for page_data in extracted_data:
        page_number = page_data['page_number']
        extracted_contents = page_data['content']
        fonts = page_data['Font']
        font_sizes = page_data['Font Size']

        # Loop through the lines in the JSON for the given page
        for i, line in enumerate(data['pages'][page_number - 1]['lines']):
            if i < len(extracted_contents) and line['content'] == extracted_contents[i]:
                line['Font'] = fonts[i]
                line['Font Size'] = font_sizes[i]

    # Assigning roles to lines based on content matching
    for paragraph in data['paragraphs']:
        para_content = paragraph['content']

        # Going through each page and its lines
        for page in data['pages']:
            for line in page['lines']:
                if line['content'] in para_content:
                    # Assigning the role from the paragraph to the line
                    line['role'] = paragraph['role']

    # Correcting the approach to rearrange the fields
    for page in data['pages']:
        for idx, line in enumerate(page['lines']):
            if 'role' in line:
                role = line.pop('role')
                updated_line = {'role': role, **line}
                page['lines'][idx] = updated_line

    # Correcting the logic to match lines with cells
    for table in data['tables']:
        for cell in table['cells']:
            # Check if 'spans' is not empty
            if cell['spans']:
                # Extracting the start and end offsets for the cell
                cell_start = cell['spans'][0]['offset']
                cell_end = cell_start + cell['spans'][0]['length']

                # To store the lines corresponding to this cell
                cell_lines = []

                # Going through each page and its lines
                for page in data['pages']:
                    for line in page['lines']:
                        # Checking for the existence of the "spans" key and then extracting start and end offsets
                        if 'spans' in line:
                            line_start = line['spans'][0]['offset']
                            line_end = line_start + line['spans'][0]['length']

                            # Checking if the line's span falls within or overlaps with the cell's span
                            if (line_start >= cell_start and line_end <= cell_end):
                                cell_lines.append({
                                    'content': line['content'],
                                    'polygon': line['polygon'],
                                    'Font': line['Font'],
                                    'Font Size': line['Font Size'],
                                })

                # Adding the identified lines to the cell
                cell['lines'] = cell_lines
            else:
                # Handle the case where 'spans' is empty, possibly by setting cell['lines'] to an empty list
                cell['lines'] = []


    # Saving the modified JSON structure with the updated filename
    output_filename = os.path.join(os.path.dirname(json_path), 'updated_' + os.path.basename(json_path))
    with open(output_filename, "w") as file:
        json.dump(data, file, indent=4)

def get_file_pairs(directory):
    file_pairs = []
    for file in os.listdir(directory):
        if file.endswith(".pdf"):
            json_file = file.replace(".pdf", ".json")
            if json_file in os.listdir(directory):
                file_pairs.append((os.path.join(directory, file), os.path.join(directory, json_file)))
    return file_pairs

def process_all_files(directory):
    file_pairs = get_file_pairs(directory)
    for pdf_path, json_path in file_pairs:
        print(pdf_path)
        process_pdf_json(pdf_path, json_path)
        print('done!')

def main(directory_path):
    process_all_files(directory_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process PDF and JSON files in a directory')
    parser.add_argument('directory_path', type=str, help='Path to the directory containing PDF and JSON files')
    args = parser.parse_args()

    main(args.directory_path)
