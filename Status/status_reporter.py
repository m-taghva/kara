import os
import json
import csv
import subprocess
from datetime import datetime, timedelta
import argparse
import requests

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

# Constants
START_TIME_SUM = 60
END_TIME_SUBTRACT = 60
CONFIG_FILE = "./../conf/Status-reporter/status.conf"

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Influxdb Status-reporter")
parser.add_argument("-t", "--time", help="Time range in the format 'start_time,end_time' (e.g., 'Y-M-D h:m:s,Y-M-D h:m:s')", required=True)
parser.add_argument("-m", "--metric_file", help="Comma-separated list of metric file paths")
parser.add_argument("-d", "--path_dir", help="Path to the parent directory")
args = parser.parse_args()

# Extract arguments
time_range = args.time
metric_files = args.metric_file.split(',') if args.metric_file else []
path_dir = args.path_dir if args.path_dir else "."

print("")
print(f"{YELLOW}========================================{RESET}")

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    tehran_timestamp_seconds = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds = tehran_timestamp_seconds + add_seconds
    utc_timestamp = datetime.utcfromtimestamp(utc_timestamp_seconds).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp

# Create the output parent directory if it doesn't exist
OUTPUT_PARENT_DIR = os.path.join(path_dir, "query_results")
os.makedirs(OUTPUT_PARENT_DIR, exist_ok=True)

# Generate CSV file name based on the time range
time_range_parts = time_range.split(',')
start_time, end_time = time_range_parts[0], time_range_parts[1]
start_time_csv = start_time.replace(" ", "-")
end_time_csv = end_time.replace(" ", "-")
csv_file_name = f"{start_time_csv}_{end_time_csv}.csv"
output_csv_all = os.path.join(OUTPUT_PARENT_DIR, csv_file_name)

# Initialize the CSV file with the header
output_csv_str = ["Host_alias"]
# Loop through each combination of time range, host, IP, PORT, and execute the curl command
with open(CONFIG_FILE, 'r') as config_file:
    csvi = 0
    for line_conf in config_file:
        line_conf = line_conf.strip()
        if line_conf and not line_conf.startswith('#'):
            IP_PORT, DATABASE, HOSTS_ALIASE = line_conf.split(',')
            parts = HOSTS_ALIASE.split(':')
            host = parts[0]
            alias = parts[1] if len(parts) > 1 else host
            start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
            end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
            output_csv_str.append(f"{alias}") #value of CSV rows
            csvi += 1
            for metric in metric_files:
              if os.path.isfile(metric):
                with open(metric, 'r') as f:
                    for metric_name in f:
                        metric_name = metric_name.strip()
                        # Check if the line is not empty and doesn't start with #
                        if metric_name and not metric_name.startswith('#'):
                            metric_prefix = os.path.basename(metric).split('_')[0]
                            if csvi == 1 :
                                metric_name = metric_name.replace(" ", "")
                                output_csv_str[0] += f",{metric_prefix}_{metric_name.replace('netdata.', '')}"
                            curl_command = f'curl -sG "http://{IP_PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{host}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                            query_result = subprocess.getoutput(curl_command)
                            values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                            values = [str(v[1]) for v in values]
                            output_csv_str[csvi] += "," + ",".join(values)
                            print(f"{BOLD}Add metrics to CSV, please wait ...{RESET}")
                            # Construct the curl command for query 2
                            query2_curl_command = f'curl -sG "http://{IP_PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{host}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time(10s) fill(none)"'
                            query2_output = subprocess.getoutput(query2_curl_command)
                            os.system(f"python3 ./../Status/image_renderer.py '{query2_output}' '{host}' '{path_dir}'")
with open(output_csv_all, 'a') as csv_file:
    for line in output_csv_str:
        csv_file.write(line + "\n")
print("")
print(f"{BOLD}Done! Csv and Images are saved in the {RESET}{YELLOW}'{OUTPUT_PARENT_DIR}'{RESET}{BOLD} directory{RESET}")
print("")
print(f"{YELLOW}========================================{RESET}")
