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

##### Constants #####
START_TIME_SUM = 10  # increase your report start time
END_TIME_SUBTRACT = 10  # decrease your report end time
TIME_GROUP = 10  # time group for query 2
CONFIG_FILE = "./../conf/Status-reporter/status.conf"
##### End of Constants #####

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    tehran_timestamp_seconds = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    utc_timestamp_seconds = tehran_timestamp_seconds + add_seconds
    utc_timestamp = datetime.utcfromtimestamp(utc_timestamp_seconds).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp

# Function to extract metrics from files
def get_metrics_from_file(metric_file_path):
    metrics = []
    with open(metric_file_path, 'r') as f:
        metrics = [metric.strip() for metric in f if metric.strip() and not metric.strip().startswith('#')]
    return metrics

# Load configuration from config file
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
parser.add_argument("-o", "--path_dir", help="Path to the parent directory")
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
    time_range = data_loaded.get('time', [])[0]

# Generate CSV file name based on the time range
time_range_parts = time_range.split(',')
start_time, end_time = time_range_parts[0], time_range_parts[1]
start_time_csv = start_time.replace(" ", "-")
end_time_csv = end_time.replace(" ", "-")
output_csv = os.path.join(OUTPUT_PARENT_DIR, f"{start_time_csv}_{end_time_csv}.csv")
if os.path.exists(output_csv):
    os.remove(output_csv)

metric_operation_mapping = {}
metric_operations = []

if args.metric_file:
    # Extract metric operations from file names in the command-line argument
    metric_files_command = args.metric_file.split(',')
    metric_operations = [os.path.basename(metric_file).split('_')[0] for metric_file in metric_files_command]
    metric_operation_mapping = dict(zip(metric_files_command, metric_operations))
else:
    # Read metric file paths and operations from the configuration file
    for metric_operation, metric_file in data_loaded.get('metrics', {}).items():
        metric_operations.append(metric_operation)
        metric_files_config = [metric_file.get('path', '')]
        metric_operation_mapping[metric_file.get('path', '')] = metric_operation

output_csv_str = ["Host_alias"]  # name of the first column in csv
csvi = 0
# Loop through each combination of time range, host, IP, PORT, and execute the curl command
for mc_server, config in data_loaded.get('influxdbs', {}).items():
    ip = config.get('ip')
    influx_port = config.get('influx_port')
    for db_name, db_data in config.get('databases', {}).items():
        hostls = db_data.get('hostls', {})
        for host_name, alias in hostls.items():
            alias = alias if alias and len(alias) > 1 else host_name
            start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
            end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
            output_csv_str.append(alias)  # value inside the first column of csv
            csvi += 1
            for metric_file, metric_operation in metric_operation_mapping.items():
                if os.path.isfile(metric_file):
                    metrics = get_metrics_from_file(metric_file)
                    for metric_name in metrics:
                        metric_name = metric_name.strip()
                        if csvi == 1:
                            metric_name = metric_name.replace(" ", "")
                            output_csv_str[0] += f",{metric_operation}_{metric_name.replace('netdata.', '')}"
                            # Construct the curl command for query 1
                        query1_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM \\"{metric_name}\\" WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"'
                        query_result = subprocess.getoutput(query1_curl_command)
                        values = json.loads(query_result).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                        values = [str(v[1]) for v in values]
                        output_csv_str[csvi] += "," + ",".join(values)
                        print(f"{BOLD}Add metrics to CSV, please wait ...{RESET}")
                        # Construct the curl command for query 2
                        query2_curl_command = f'curl -sG "http://{ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM /{metric_name}/ WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' GROUP BY time({TIME_GROUP}s) fill(none)"'
                        query2_output = subprocess.getoutput(query2_curl_command)
                        os.system(f"python3 ./../Status/image_renderer.py '{query2_output}' '{host_name}' '{path_dir}'")
# Write the CSV file for each time range
with open(output_csv, 'a') as csv_file:
    for line in output_csv_str:
        csv_file.write(line + "\n")
print("")
print(f"{BOLD}Done! Csv and Images are saved in the {RESET}{YELLOW}'{OUTPUT_PARENT_DIR}'{RESET}{BOLD} directory{RESET}")
print("")
print(f"{YELLOW}========================================{RESET}")
print("")
