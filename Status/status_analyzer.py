import os
import sys
import pandas as pd

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

# Read operation and new column name from the txt file
def read_txt_file(file_path):
    with open(file_path, 'r') as txt_file:
        operation, new_column_name = txt_file.readline().strip().split(':')
        selected_columns = txt_file.read().splitlines()
    return operation, new_column_name, selected_columns

# Process CSV file
def process_csv_file(csv_data, operation, new_column_name, selected_columns):
    if operation == 'sum':
        new_column_name = f"sum.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].sum(axis=1)
    elif operation == 'avg':
        new_column_name = f"avg.{new_column_name}"
        csv_data[new_column_name] = csv_data[selected_columns].mean(axis=1)
    return csv_data

# Get CSV and transformation directory addresses from command-line arguments
if len(sys.argv) != 3:
    print("Usage: python analyzer.py csv_file_path transformation_directory")
    sys.exit(1)

csv_original = sys.argv[1]
transformation_directory = sys.argv[2]

# Initialize CSV data
csv_intermediate = pd.read_csv(csv_original)

# Store the names of selected columns from the t*.txt files
selected_column_names = set()

# Iterate through txt files in the transformation directory
for txt_file in os.listdir(transformation_directory):
    if txt_file.startswith('t') and txt_file.endswith('.txt'):
        txt_file_path = os.path.join(transformation_directory, txt_file)
        operation, new_column_name, selected_columns = read_txt_file(txt_file_path)
        
        # Process CSV data
        csv_intermediate = process_csv_file(csv_intermediate, operation, new_column_name, selected_columns)
        
        # Store the selected column names
        selected_column_names.update(selected_columns)

# Determine the columns to keep in the final CSV
keep_columns = [col for col in csv_intermediate.columns if col not in selected_column_names]

# Create the final CSV with the selected columns
csv_final = csv_intermediate[keep_columns]

# Save the final CSV data as the last CSV file
final_output_csv_name = f"{os.path.splitext(os.path.basename(csv_original))[0]}-{os.path.basename(transformation_directory)}.csv"
final_output_csv_path = os.path.join(os.path.dirname(csv_original), final_output_csv_name)
csv_final.to_csv(final_output_csv_path, index=False)
print(f"{BOLD}Final Analyzed CSV file:{RESET}{YELLOW}{final_output_csv_path}{RESET}")
print("")

# Remove the intermediate CSV file
intermediate_csv_path = os.path.join(os.path.dirname(csv_original), "intermediate.csv")
if os.path.exists(intermediate_csv_path):
    os.remove(intermediate_csv_path)
