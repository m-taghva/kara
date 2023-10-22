import os
import json
import subprocess
from datetime import datetime, timedelta
import csv
import pandas as pd
import requests
import argparse

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

# Increase or reduce time of queries and CSV (use seconds)
START_TIME_SUM = 60
END_TIME_SUBTRACT = 60

CONFIG_FILE = "status.conf"  # config file for ip:port, db name, host name:alias Change this to your file path

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Your script description here.")
parser.add_argument("input_files", help="Input files separated by commas (metric_file.txt,time_file.txt,parent_path)")
args = parser.parse_args()

# Split the input files by commas
input_files = args.input_files.split(',')

# Initialize the variables
METRIC_FILES_ARRAY = []
TIME_RANGE_FILES = []
PARENT_DIR = None

print("")
print(f"{YELLOW}========================================{RESET}")

# Check each input file
for file in input_files:
    # Check if the file name contains "metric" to identify metric files
    if "metric" in file:
        METRIC_FILES_ARRAY.append(file)
    elif "time" in file:
        TIME_RANGE_FILES.append(file)
    else:
        # If it's not a metric or time file, assume it's the parent directory
        PARENT_DIR = file

# If PARENT_DIR is not provided, use the current working directory
if not PARENT_DIR:
    PARENT_DIR = "."

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc_start(tehran_timestamp_st):
    tehran_timestamp_seconds_st = int(datetime.strptime(tehran_timestamp_st, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds_st = tehran_timestamp_seconds_st + START_TIME_SUM
    utc_timestamp_st = datetime.utcfromtimestamp(utc_timestamp_seconds_st).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp_st

def convert_tehran_to_utc_end(tehran_timestamp_ed):
    tehran_timestamp_seconds_ed = int(datetime.strptime(tehran_timestamp_ed, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds_ed = tehran_timestamp_seconds_ed - END_TIME_SUBTRACT
    utc_timestamp_ed = datetime.utcfromtimestamp(utc_timestamp_seconds_ed).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp_ed

# Function to convert UTC to Tehran timestamp for CSV
def tehran_time_csv_st(tehran_timestamp_csv_st):
    tehran_timestamp_seconds_csv_st = int(datetime.strptime(tehran_timestamp_csv_st, "%Y-%m-%d %H:%M:%S").timestamp())
    new_tehran_timestamp_seconds_csv_st = tehran_timestamp_seconds_csv_st + START_TIME_SUM
    new_tehran_timestamp_csv_st = datetime.fromtimestamp(new_tehran_timestamp_seconds_csv_st).strftime("%Y-%m-%d %H:%M:%S")
    return new_tehran_timestamp_csv_st

def tehran_time_csv_ed(tehran_timestamp_csv_ed):
    tehran_timestamp_seconds_csv_ed = int(datetime.strptime(tehran_timestamp_csv_ed, "%Y-%m-%d %H:%M:%S").timestamp())
    new_tehran_timestamp_seconds_csv_ed = tehran_timestamp_seconds_csv_ed - END_TIME_SUBTRACT
    new_tehran_timestamp_csv_ed = datetime.fromtimestamp(new_tehran_timestamp_seconds_csv_ed).strftime("%Y-%m-%d %H:%M:%S")
    return new_tehran_timestamp_csv_ed

# Create the output parent directory if it doesn't exist
OUTPUT_PARENT_DIR = os.path.join(PARENT_DIR, "query_results")
os.makedirs(OUTPUT_PARENT_DIR, exist_ok=True)

# Create a single CSV file for all hosts in the 'query_results' directory
output_csv_all = os.path.join(OUTPUT_PARENT_DIR, "all_hosts_output.csv")

# Initialize the CSV file with the header
header = "Host_alias,Start_Time,End_Time"

for metric_file in METRIC_FILES_ARRAY:
    with open(metric_file, 'r') as f:
        lines = f.read().splitlines()
        # Extract the prefix from the metric filename
        metric_prefix = os.path.basename(metric_file).split('_')[0]  # Split by '_' and take the first part
        for metric_name in lines:
            # Check if the line is not empty and doesn't start with #
            if metric_name and not metric_name.startswith('#'):
                # Remove spaces from the metric name
                metric_name = metric_name.replace(" ", "")
                header += f",{metric_prefix}_{metric_name.replace('netdata.', '')}"

with open(output_csv_all, 'w') as csv_file:
    csv_file.write(header + "\n")

# Loop through each combination of time range, host, IP, PORT, and execute the curl command
with open(CONFIG_FILE, 'r') as config_file:
    for line_conf in config_file:
        # Skip lines starting with # and blank lines
        line_conf = line_conf.strip()
        if line_conf and not line_conf.startswith('#'):
            IP_PORT, DATABASE, HOSTS_ALIASE = line_conf.split(',')
            parts = HOSTS_ALIASE.split(':')
            host = parts[0]
            alias = parts[1] if len(parts) > 1 else host
            for time_file in TIME_RANGE_FILES:
                with open(time_file, 'r') as time_file:
                    for line_time in time_file:
                        line_time = line_time.strip()
                        # Check if the line is not empty (removes blank lines)
                        if line_time and not line_time.startswith('#'):
                            start_time_tehran, end_time_tehran = line_time.split(',')
                            start_time_utc = convert_tehran_to_utc_start(start_time_tehran)
                            end_time_utc = convert_tehran_to_utc_end(end_time_tehran)

                            line_values = f"{alias},{tehran_time_csv_st(start_time_tehran)},{tehran_time_csv_ed(end_time_tehran)}"  # value of CSV rows

                            for metric_file in METRIC_FILES_ARRAY:
                                if os.path.isfile(metric_file):
                                    with open(metric_file, 'r') as f:
                                        for metric_name in f:
                                            metric_name = metric_name.strip()
                                            # Check if the line is not empty and doesn't start with #
                                            if metric_name and not metric_name.startswith('#'):
                                                metric_prefix = os.path.basename(metric_file).split('_')[0]
                                                curl_command = f'curl -sG "http://{IP_PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{host}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                                                query_result = subprocess.getoutput(curl_command)
                                                values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                                                values = [str(v[1]) for v in values]
                                                line_values += "," + ",".join(values)
                                                # Construct the curl command for query 2
                                                query2_curl_command = f'curl -sG "http://{IP_PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{host}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time(10s) fill(none)"'
                                                query2_output = subprocess.getoutput(query2_curl_command)
                                                os.system(f"python3 image_renderer.py '{query2_output}' '{host}' '{PARENT_DIR}'")

                            with open(output_csv_all, 'a') as csv_file:
                                csv_file.write(line_values + "\n")
                            print(f"{BOLD}Add metrics to CSV, please wait ...{RESET}")
print("")
print(f"Progress: {YELLOW}|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||{RESET} 100%")
print("")
print(f"{BOLD}CSV and Images are saved in the {RESET}{YELLOW}'{OUTPUT_PARENT_DIR}'{RESET}{BOLD} directory{RESET}")
print("")
print(f"{YELLOW}========================================{RESET}")
