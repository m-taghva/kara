import os
import re
import csv
import argparse
from glob import glob
# for font
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

def extract_string_number_pairs(target_directory):
    keys = re.findall("(?<=#)[^:]*(?=:)", target_directory)
    values = re.findall("(?<=:)[^#]*(?=#)", target_directory)
    return list(zip(keys, values))

def create_extracted_data(pairs):
    return dict(pairs)

def read_csv_data(csv_file_path):
    with open(csv_file_path, mode='r') as input_csv:
        csv_reader = csv.reader(input_csv)
        headers = next(csv_reader)
        input_data = list(csv_reader)
    return headers, input_data

def merge_csv_files(input_directory, output_csv_writer, selected_csv):
    headers_written = False
    for subdirectory in os.listdir(input_directory):
        subdirectory_path = os.path.join(input_directory, subdirectory)
        if os.path.isdir(subdirectory_path):
            pairs = extract_string_number_pairs(subdirectory_path)
            if pairs:
                extracted_data = create_extracted_data(pairs)
                csv_file_paths = glob(os.path.join(subdirectory_path, 'query_results', selected_csv))
                if not csv_file_paths:
                    print(f"No CSV files found in {subdirectory_path}")
                    continue
                for i, csv_file_path in enumerate(csv_file_paths):
                    if not headers_written:
                        headers, _ = read_csv_data(csv_file_path)
                        headers = ["Time Ranges"] + list(extracted_data.keys()) + headers
                        output_csv_writer.writerow(headers)
                        headers_written = True
                    _, input_data = read_csv_data(csv_file_path)
                    csv_name_without_extension = os.path.splitext(os.path.basename(csv_file_path))[0]
                    extracted_numbers = list(extracted_data.values())
                    output_csv_writer.writerows([csv_name_without_extension] + extracted_numbers + row for row in input_data)

def main():
    parser = argparse.ArgumentParser(description='Merge CSV files with extracted values.')
    parser.add_argument('-i', '--input_directory', required=True, help='Path to the directory containing CSV files')
    parser.add_argument('-c', '--selected_csv', required=True, help='Name of the selected CSV file or "*.csv"')
    args = parser.parse_args()
    input_directory = args.input_directory.strip()
    selected_csv = args.selected_csv.strip()

    if not os.path.isdir(input_directory):
        print(f"Directory not found: {input_directory}")
        exit(1)

    selected_csv_name = os.path.splitext(selected_csv)[0]
    output_csv_path = os.path.join(input_directory, f"{selected_csv_name}-merge.csv")
    if os.path.exists(output_csv_path):
        os.remove(output_csv_path)

    with open(output_csv_path, mode='a', newline='') as output_csv: 
         csv_writer = csv.writer(output_csv)
         merge_csv_files(input_directory, csv_writer, selected_csv)

    print(f"\n{BOLD}Merged CSV file{RESET}{YELLOW}'{output_csv_path}'{RESET}{BOLD}has been created with the extracted values{RESET}\n")

if __name__ == "__main__":
