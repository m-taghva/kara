import re
import string
import random
import sys
import os
import argparse


            
def main(input_file_path, output_directory):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    cleanup_output_config_gen(output_directory)
    with open(input_file_path, 'r') as inputFile:
        input_text = inputFile.read()
    replace_tags(input_text, "", output_directory)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate configuration files.')
    parser.add_argument('-i', '--input', help='Input file path', required=True)
    parser.add_argument('-o', '--output', help='Output directory', required=True)
    args = parser.parse_args()
    input_file_path = args.input
    output_directory = args.output
    main(input_file_path, output_directory)
