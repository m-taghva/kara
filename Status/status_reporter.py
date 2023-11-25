import os
import json
import subprocess
import sys
from datetime import datetime
import argparse
import yaml

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

# Constants
START_TIME_SUM = 10
END_TIME_SUBTRACT = 10
CONFIG_FILE = "./../conf/Status-reporter/status.conf"
TIME_GROUP = 10

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    tehran_timestamp_seconds = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds = tehran_timestamp_seconds + add_seconds
    utc_timestamp = datetime.utcfromtimestamp(utc_timestamp_seconds).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp

# Load configuration from YAML file
with open(CONFIG_FILE, "r") as stream:
    try:
        data_loaded = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Error loading the configuration: {exc}")
        sys.exit(1)

print("")
print(f"{YELLOW}========================================{RESET}")
print("")

# Parse command-line arguments 
parser = argparse.ArgumentParser(description="Influxdb Status-reporter")
parser.add_argument("-t", "--time", help="Time range in the format 'start_time,end_time' (e.g., 'Y-M-D h:m:s,Y-M-D h:m:s')")
parser.add_argument("-m", "--metric_file", help="Comma-separated list of metric file paths")
parser.add_argument("-d", "--path_dir", help="Path to the parent directory")
args = parser.parse_args()

# Extract arguments
metric_files = args.metric_file.split(',') if args.metric_file else []
path_dir = args.path_dir if args.path_dir else "."

# Create the output parent directory
OUTPUT_PARENT_DIR = os.path.join(path_dir, "query_results")
os.makedirs(OUTPUT_PARENT_DIR, exist_ok=True)

# Check if the time option is provided
if args.time:
    time_range = args.time
else:
    # Read time range from the configuration file
    time_range = data_loaded.get('time_section', [])[0]

# Generate CSV file name based on the time range
time_range_parts = time_range.split(',')
start_time, end_time = time_range_parts[0], time_range_parts[1]
start_time_csv = start_time.replace(" ", "-")
end_time_csv = end_time.replace(" ", "-")
output_csv = os.path.join(OUTPUT_PARENT_DIR, f"{start_time_csv}_{end_time_csv}.csv")
if os.path.exists(output_csv):
   os.remove(output_csv)

output_csv_str = ["Host_alias"]
csvi = 0
# Loop through each combination of time range, host, IP, PORT, and execute the curl command
for server, values in data_loaded.get('influx_section', {}).items():
    PORT = values['port']
    DATABASE = values['database']
    HOST = values['host']
    ALIAS = values['alias'] if values['alias'] and len(values['alias']) > 1 else HOST
    start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
    end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
    output_csv_str.append(ALIAS)  # value of CSV rows
    csvi += 1
    for metric in metric_files:
        if os.path.isfile(metric):
           with open(metric, 'r') as f:
                for metric_name in f:
                    metric_name = metric_name.strip()
                    if metric_name and not metric_name.startswith('#'):
                       metric_prefix = os.path.basename(metric).split('_')[0]
                       if csvi == 1:
                          metric_name = metric_name.replace(" ", "")
                          output_csv_str[0] += f",{metric_prefix}_{metric_name.replace('netdata.', '')}"
                       # Construct the curl command for query 1
                       query1_curl_command = f'curl -sG "http://{server}:{PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{HOST}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                       query_result = subprocess.getoutput(query1_curl_command)
                       values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                       values = [str(v[1]) for v in values]
                       output_csv_str[csvi] += "," + ",".join(values)
                       print(f"{BOLD}Add metrics to CSV, please wait ...{RESET}")
                       # Construct the curl command for query 2
                       query2_curl_command = f'curl -sG "http://{server}:{PORT}/query" --data-urlencode "db={DATABASE}" --data-urlencode "q=SELECT {metric_prefix}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{HOST}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time({TIME_GROUP}s) fill(none)"'
                       query2_output = subprocess.getoutput(query2_curl_command)
                       os.system(f"python3 ./../Status/image_renderer.py '{query2_output}' '{HOST}' '{path_dir}'")

# Write the CSV file for each time range
with open(output_csv, 'a') as csv_file:
     for line in output_csv_str:
         csv_file.write(line + "\n")
print("")
print(f"{BOLD}Done! Csv and Images are saved in the {RESET}{YELLOW}'{OUTPUT_PARENT_DIR}'{RESET}{BOLD} directory{RESET}")
print("")
print(f"{YELLOW}========================================{RESET}")
print("")
