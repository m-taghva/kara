import os
import re
import csv
import sys
import argparse
from glob import glob

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

def extract_string_number_pairs(target_directory):
    # Extract all string:number pairs from the target directory
    keys = re.findall("(?<=#)[^:]*(?=:)", target_directory)
    values = re.findall("(?<=:)[^#]*(?=#)", target_directory)
    
    return list(zip(keys, values))

def create_extracted_data(pairs):
    # Create a dictionary to store the extracted data with cleaned keys
    return {key: value for key, value in pairs}

def read_csv_data(csv_file_path):
    # Read the data from the input CSV file
    with open(csv_file_path, mode='r') as input_csv:
        csv_reader = csv.reader(input_csv)
        headers = next(csv_reader)
        input_data = list(csv_reader)  # Read the entire data into a list
    return headers, input_data

def merge_csv_files(target_directory_path, output_csv_writer, extracted_data, first_target_directory, selected_csv):
    # Find all CSV files inside the target directory
    csv_file_paths = glob(os.path.join(target_directory_path, 'query_results', selected_csv))

    if not csv_file_paths:
        print(f"No CSV files found in {target_directory_path}")
        return

    # Initialize the concatenated data
    concatenated_data = []

    for i, csv_file_path in enumerate(csv_file_paths):
        headers, input_data = read_csv_data(csv_file_path)
        if i == 0 and target_directory_path == first_target_directory:
            # Write the header row with the extracted strings, original headers, and "CSV File Name" as the first column for the first target directory
            header_row = ["Time Ranges"] + list(extracted_data.keys()) + headers
            output_csv_writer.writerow(header_row)
        for row in input_data:
            # Get the CSV file name without the ".csv" extension
            csv_file_name = os.path.basename(csv_file_path)
            csv_name_without_extension = os.path.splitext(csv_file_name)[0]
            # Write the data to the output CSV
            extracted_numbers = list(extracted_data.values())
            output_csv_writer.writerow([csv_name_without_extension] + extracted_numbers + row)

def main():
    parser = argparse.ArgumentParser(description='Merge CSV files with extracted values.')
    parser.add_argument('-i', '--input_directory', required=True, help='Path to the directory containing CSV files')
    parser.add_argument('-c', '--selected_csv', required=True, help='Name of the selected CSV file or "*.csv"')
    args = parser.parse_args()

    input_directory = args.input_directory.strip()
    selected_csv = args.selected_csv.strip()

    # Verify if the input directory exists
    if not os.path.isdir(input_directory):
        print(f"Directory not found: {input_directory}")
        exit(1)

    # Specify the output file path
    selected_csv_name = os.path.splitext(selected_csv)[0]
    output_csv_path = os.path.join(input_directory, f"{selected_csv_name}-merge.csv")

    # Remove the existing output.csv file if it exists
    if os.path.exists(output_csv_path):
        os.remove(output_csv_path)

    # Initialize the extracted data
    extracted_data = {}

    # Process each subdirectory in the input directory
    first_target_directory = None
    for subdirectory in os.listdir(input_directory):
        subdirectory_path = os.path.join(input_directory, subdirectory)
        if os.path.isdir(subdirectory_path):
            # Extract string:number pairs from the subdirectory
            pairs = extract_string_number_pairs(subdirectory_path)
            if pairs:
                # Create a dictionary to store the extracted data with cleaned keys
                extracted_data = create_extracted_data(pairs)
                if first_target_directory is None:
                    first_target_directory = subdirectory_path
                # Merge CSV files and append data to the output file
                with open(output_csv_path, mode='a', newline='') as output_csv:
                    csv_writer = csv.writer(output_csv)
                    merge_csv_files(subdirectory_path, csv_writer, extracted_data, first_target_directory, selected_csv)
    print("")
    print(f"{BOLD}merged CSV file{RESET}{YELLOW}'{output_csv_path}'{RESET}{BOLD}has been created with the extracted values{RESET}")
    print("")
    
if __name__ == "__main__":
    main()
