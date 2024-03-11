import argparse
import json
from pdf2docx import Converter, Converter_Image
from update_json_layout_convert import layout_convert_format

def main(pdf_path, out_path, json_path, start_page, end_page):
    # Main conversion function
    json_convertor_result_list = layout_convert_format.convert_format_main(json_path)

    print(json_convertor_result_list)

    # Original PDF file
    docx_img_convert = Converter_Image(pdf_path)

    # Convert JSON to list
    docx_img_convert.convert(json_convertor_result_list, out_path, start_page, end_page)

if __name__ == "__main__":
    # Command-line arguments
    parser = argparse.ArgumentParser(description='Convert specified range of pages from PDF to DOCX with layout formatting')
    parser.add_argument('pdf_path', type=str, help='Path to the original PDF file (.pdf)')
    parser.add_argument('out_path', type=str, help='Path to the output DOCX file (.docx)')
    parser.add_argument('json_path', type=str, help='Path to the processed JSON file (.json)')
    parser.add_argument('start_page', type=int, help='Starting page for conversion. Use 0 for the first page.')
    parser.add_argument('end_page', type=int, help='Ending page for conversion. Use 1 for the first page, 2 for the second page, and so on.')
    args = parser.parse_args()

    # Call the main function with command-line arguments
    main(args.pdf_path, args.out_path, args.json_path, args.start_page, args.end_page)

