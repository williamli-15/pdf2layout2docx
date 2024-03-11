import os
import json
import argparse
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import AnalysisFeature

# Read Azure Form Recognizer endpoint URL and API key from environment variables
AZ_ENDPOINT = os.environ.get("AZ_ENDPOINT")
AZ_KEY = os.environ.get("AZ_KEY")

def call_fr_api(file_path):
    document_analysis_client = DocumentAnalysisClient(
        endpoint=AZ_ENDPOINT, credential=AzureKeyCredential(AZ_KEY)
    )
    with open(file_path, "rb") as f:
        poller = document_analysis_client.begin_analyze_document("prebuilt-layout", f, features=[AnalysisFeature.FORMULAS])
    api_result = poller.result()
    return api_result

def process_pdf_files(docs_folder):
    # Iterate over files in the folder
    for filename in os.listdir(docs_folder):
        if filename.endswith(".pdf"):
            # Construct the full file path
            file_path = os.path.join(docs_folder, filename)

            # Call the API for the current file
            result = call_fr_api(file_path)
            result_dict = result.to_dict()

            # Store the result as a JSON file with the same name as the PDF
            json_filename = os.path.splitext(filename)[0] + ".json"
            json_file_path = os.path.join(docs_folder, json_filename)

            with open(json_file_path, "w") as json_file:
                json.dump(result_dict, json_file, indent=4)

            print(f"Processed {filename} and saved the result as {json_filename}")

if __name__ == "__main__":
    # Command-line arguments
    parser = argparse.ArgumentParser(description='Process PDF files in a directory using Azure Form Recognizer API')
    parser.add_argument('docs_folder', type=str, help='Path to the folder containing PDF files')
    args = parser.parse_args()

    process_pdf_files(args.docs_folder)
