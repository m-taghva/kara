import os
import re
import json
import subprocess
import argparse
import requests
import sys
import time
from datetime import datetime, timedelta, timezone
import concurrent.futures
import threading
import yaml
import logging
import pytz
import uuid
from PIL import Image

# variables
config_file = "/etc/kara/status_reporter.conf"
log_path = "/var/log/kara/"
jsons_dir = "./../status_reporter/jsons"
# grafana variables
api_timezone = "Asia%2FTehran" # timezone of grafana
var_host = "var-hostIs"
var_time = "var-timeVariable"

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"
RED = "\033[91m"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

################################################################################# convert time functions

# Function to convert "now-nh", "now-nd", or "now" format to timestamp
def parse_time(tehran_timestamp):
    if tehran_timestamp == "now":
        now_time_timestamp = int(datetime.now().timestamp())
        return now_time_timestamp
    elif tehran_timestamp.startswith("now-") and (tehran_timestamp.endswith("h") or tehran_timestamp.endswith("d")):
        try:
            time_value = int(tehran_timestamp.split("-")[1][:-1])
            if tehran_timestamp.endswith("h"):
                # Subtract hours
                now_time_subtract = datetime.now() - timedelta(hours=time_value)
            elif tehran_timestamp.endswith("d"):
                # Subtract days
                now_time_subtract = datetime.now() - timedelta(days=time_value)
            now_time_timestamp = int(now_time_subtract.timestamp())
            return now_time_timestamp
        except ValueError:
            print("\033[91mInvalid time range format. Expected format: 'now-nh' for hours or 'now-nd' for days where n is a number\033[0m")
            exit()
    else:
        print("\033[91mInvalid time range format. Expected format: 'now', 'now-nh', or 'now-nd' where n is a number\033[0m")
        exit()

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp, add_seconds):
    if tehran_timestamp.startswith("now") or tehran_timestamp.endswith("h") or tehran_timestamp.endswith("d"):
        now_time_result = parse_time(tehran_timestamp)
        timesamp_time_add = now_time_result + add_seconds
        utc_now_time_result = datetime.utcfromtimestamp(timesamp_time_add).strftime("%Y-%m-%dT%H:%M:%SZ")
        return utc_now_time_result
    elif not tehran_timestamp.startswith("now-") and not tehran_timestamp.endswith("h"):
        tehran_timestamp_convert = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
        timestamp_add = tehran_timestamp_convert + add_seconds
        utc_timestamp_result = datetime.utcfromtimestamp(timestamp_add).strftime("%Y-%m-%dT%H:%M:%SZ")
        return utc_timestamp_result
    else:
        print("\033[91mInvalid time range format. Expected format: 'now-nh' where n is a number or time stamp format (Y-M-D H:M:S) for start and end time !\033[0m")
        exit()

def utc_to_unix_time(utc_time_str):
    # Parse the string into a datetime object
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    # Convert to Unix timestamp (in seconds)
    unix_timestamp_seconds = int(utc_time.replace(tzinfo=timezone.utc).timestamp())
    # Convert to Unix timestamp (in milliseconds)
    unix_timestamp_milliseconds = unix_timestamp_seconds * 1000
    return unix_timestamp_milliseconds

################################################################################# make & remove dashboard with image and json 

def dashboard_maker_with_image(final_images_path_dict, output_file, panels_per_column, max_panels):
    logging.info("Executing status reporter dashboard_maker_with_image function")
     # Gather all image file paths from the directory
    if not final_images_path_dict:
        print("No images found to make image dashboard")
        return
    output_files_dict = {}
    for dashboard_org_name, image_paths in final_images_path_dict.items():
        dash_list = []
        # Split the images into chunks
        image_chunks = [image_paths[i:i + max_panels] for i in range(0, len(image_paths), max_panels)]
        for idx, chunk in enumerate(image_chunks):
            images = [Image.open(image_path) for image_path in chunk] 
            # Determine the number of images per row and rows needed
            rows = (len(images) + panels_per_column - 1) // panels_per_column
            # Calculate the width and height of the combined image
            max_width = max(image.width for image in images)
            max_height = max(image.height for image in images)
            combined_width = max_width * panels_per_column
            combined_height = max_height * rows 
            # Create a new blank image to hold the combined output
            combined_image = Image.new('RGB', (combined_width, combined_height)) 
            # Paste images into the combined image
            for index, image in enumerate(images):
                x_offset = (index % panels_per_column) * max_width
                y_offset = (index // panels_per_column) * max_height
                combined_image.paste(image, (x_offset, y_offset))
            # Save the combined image with a unique name for each chunk
            result_image_name = f"{output_file}/{dashboard_org_name}_dashboard__{idx + 1}.png"
            combined_image.save(result_image_name)
            if os.path.exists(result_image_name):
                print(f"kara dashboard file saved successfully: '{YELLOW}{result_image_name}{RESET}'")
            else:
                print(f"Failed to save dashboard: '{YELLOW}{result_image_name}{RESET}'")
            dash_list.append(result_image_name)
        output_files_dict[dashboard_org_name] = dash_list
    return output_files_dict

def get_existing_dashboard_names(api_key, grafana_url):
    logging.info("Executing status reporter get_existing_dashboard_names function")
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{grafana_url}/api/search", headers=headers)
    if response.status_code == 200:
        dashboards = response.json()
        return {dash['title'] for dash in dashboards}
    else:
        print(f"Failed to retrieve existing dashboards. Status code: {response.status_code}")
        return set()

def find_unique_dashboard_name(base_name, existing_names):
    name = base_name
    counter = 1
    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1
    return name

#### import dashboard to grafana
def dashboard_import(dashboards_json, api_key, grafana_url, customized_panles):
    logging.info("Executing status reporter dashboard_import function")
    dashboard_data_dict = {}
    for dashboard_org_name in dashboards_json:
        dashboard_file = f"{jsons_dir}/{dashboard_org_name}.json"
        if os.path.exists(dashboard_file):
            with open(dashboard_file, "r") as file:
                dashboard_data = json.load(file)
            if "custom" in dashboard_org_name:
                if customized_panles:
                    for panel in customized_panles:
                        with open(f"{jsons_dir}/{panel}.json", 'r') as json_file:
                            panel_data = json.load(json_file)
                            dashboard_data["panels"].append(panel_data)
                
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {"dashboard": dashboard_data,"folderId": 0,"overwrite": False}
            # Get existing dashboard names
            existing_names = get_existing_dashboard_names(api_key, grafana_url)
            if dashboard_data["title"] in existing_names:
                # Determine the unique title
                unique_title = find_unique_dashboard_name(dashboard_data["title"], existing_names)
                payload["dashboard"]["id"] = str(uuid.uuid4())[:8]
                payload["dashboard"]["uid"] = str(uuid.uuid4())[:8]
                payload["dashboard"]["title"] = unique_title
                dashboard_uid_img = payload["dashboard"]["uid"]
                dashboard_name = payload["dashboard"]["title"]
                logging.info(f"status_reporter - new dashboard name: {dashboard_name}")
            else:
                payload["dashboard"]["uid"] = str(dashboard_data["uid"])+"-kara"
                payload["dashboard"]["title"] = dashboard_data["title"]
                payload["dashboard"]["id"] = str(dashboard_data["id"])+"-kara"
                dashboard_uid_img = dashboard_data["uid"]
                dashboard_name = payload["dashboard"]["title"]
                logging.info(f"status_reporter - new dashboard name: {dashboard_name}")
            # Send the POST request to import the dashboard
            response = requests.post(grafana_url+"/api/dashboards/db", headers=headers, json=payload)
            if response.status_code == 200:
                print(f'Dashboard imported successfully ({YELLOW}{payload["dashboard"]["title"]}{RESET})')
                print("")
                logging.info(f"status_reporter - new dashboard: {dashboard_name} imported successfully")
            else:
                print(f'Failed to import dashboard {RED}({payload["dashboard"]["title"]}) Status code: {response.status_code}{RESET}')
                logging.info(f"status_reporter - new dashboard: {dashboard_name} failed to import")
                exit()
            dashboard_data_dict[dashboard_name.replace(" ", "_")] = [dashboard_org_name, dashboard_uid_img, dashboard_data]
            time.sleep(5)
        else:
            print(f"{RED}if you need images, json file of dashboard is required ! so please select it or check file name{RESET}")
            print("")
            exit()
    return dashboard_data_dict

def remove_dashboard(grafana_url, api_key, dashboard_data_dict):
    logging.info("Executing status reporter remove_dashboard function")
    for dash_name, values in dashboard_data_dict.items():
        dashboard_org_name = values[0]
        dashboard_uid_img = values[1]
        dashboard_data = values[2]
        headers = {"Authorization": f"Bearer {api_key}","Content-Type": "application/json"}
        # Perform the DELETE request
        response = requests.delete(grafana_url+"/api/dashboards/uid/"+dashboard_uid_img, headers=headers)
        if response.status_code == 200:
            print("")
            print(f"Dashboard '{RED}{dash_name}{RESET}' deleted successfully.")
            logging.info(f"status_reporter - new dashboard: {dash_name} deleted successfully")
        elif response.status_code == 404:
            print(f"Dashboard '{RED}{dash_name}{RESET}' not found")
        else:
            print(f"Failed to delete dashboard '{RED}{dash_name}{RESET}' . Status code: {response.status_code}, Response: {response.text}")
            logging.info(f"status_reporter - new dashboard: {dash_name} failed to delete")

################################################################################# export panels of dashboard

# Lock for thread-safe dictionary updates
lock = threading.Lock()

def image_export_threading(dash_name, values, api_key, grafana_url, start_time_utc, end_time_utc, output_parent_dir, hostList, panel_width, panel_height, time_variable, group_name):
    logging.info(f"Processing dashboard: {dash_name}")
    images_path_dict = {}
    dashboard_org_name = values[0]
    dashboard_uid_img = values[1]
    dashboard_data = values[2]
    start_unix = utc_to_unix_time(start_time_utc)
    end_unix = utc_to_unix_time(end_time_utc)
    panels = dashboard_data.get("panels", [])
    host_name = "All" if len(hostList) > 1 else hostList[0]
    each_server_path = f"{output_parent_dir}/{group_name}_{host_name}-images"
    os.makedirs(each_server_path, exist_ok=True)
    images_path_dict[dashboard_org_name] = []
    for panel in panels:
        panel_id = panel["id"]
        panel_title = re.sub(r'[ /&$()]+', '_', panel["title"])
        hostAPIstr = "".join(f"{var_host}={host}&" for host in hostList)
        curl_api = (f'curl -o {each_server_path}/{dashboard_org_name}_{panel_title}.png -H "Authorization: Bearer {api_key}" "{grafana_url}/render/d-solo/{dashboard_uid_img}/{dash_name}?orgId=1&{hostAPIstr}{var_time}={time_variable}&from={start_unix}&to={end_unix}&panelId={panel_id}&width={panel_width}&height={panel_height}&tz={api_timezone}"')
        result = subprocess.run(curl_api, shell=True, check=True, capture_output=True, text=True)
        image_path = f"{each_server_path}/{dashboard_org_name}_{panel_title}.png"
        if os.path.exists(image_path):
            images_path_dict[dashboard_org_name].append(image_path)
            print(f"Image for panel '{YELLOW}{panel_title}{RESET}' (ID: {YELLOW}{panel_id}{RESET}) is a valid and saved successfully for server: {YELLOW}{host_name}{RESET}")
            logging.info(f"status_reporter - Image for panel '{panel_title}' (ID: {panel_id}) is a valid and saved successfully for server: {host_name}")
    if result.returncode == 0:
        print("========================================")
        print(f"{BOLD}All panels of ({dashboard_org_name}) have been processed for ({host_name}) {RESET}")
        print("========================================")
    return images_path_dict

def images_export(dashboard_data_dict, api_key, grafana_url, start_time_utc, end_time_utc, output_parent_dir, hostList, panel_width, panel_height, time_variable, group_name):
    final_images_path_dict = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_dashboard = {executor.submit(image_export_threading, dash_name, values, api_key, grafana_url, start_time_utc, end_time_utc, output_parent_dir, hostList, panel_width, panel_height, time_variable, group_name): dash_name for dash_name, values in dashboard_data_dict.items()}  
        for future in concurrent.futures.as_completed(future_to_dashboard):
            dash_name = future_to_dashboard[future]
            try:
                result_dict = future.result()
                with lock:  # Ensure thread-safe updates to the final dictionary
                    for key, value in result_dict.items():
                        if key in final_images_path_dict:
                            final_images_path_dict[key].extend(value)
                        else:
                            final_images_path_dict[key] = value
            except Exception as e:
                logging.error(f"Dashboard {dash_name} generated an exception: {e}")        
    return final_images_path_dict

################################################################################# get report from database

# Function to extract metrics from files
def get_metrics_from_file(metric_file_path):
    logging.info("Executing status reporter get_metrics_from_file function")
    metrics = []
    all_metrics = {'regex_m': [], 'normal_m': []} 
    with open(metric_file_path, 'r') as f:
        metrics = [metric.strip() for metric in f if metric.strip() and not metric.strip().startswith('#')]
    for non_formated_metric in metrics:
        if non_formated_metric[0]=='/' and non_formated_metric[-1]=='/':
            all_metrics['regex_m'].append(non_formated_metric)
        else:
            all_metrics['normal_m'].append(non_formated_metric) 
    return all_metrics

def get_report(data_loaded, metric_file, path_dir, time_range, img=False):
    # Load configuration from config file
    time_section = data_loaded.get('time', {})
    START_TIME_SUM = time_section.get('start_time_sum')
    END_TIME_SUBTRACT = time_section.get('end_time_subtract')
    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("") 
    # Split time_range and generate output_csv
    time_range_parts = time_range.split(',')
    start_time, end_time = time_range_parts[0], time_range_parts[1]
    if start_time.startswith("now"):
        tehran_tz = pytz.timezone('Asia/Tehran')
        start_time_utc_csv = convert_tehran_to_utc(start_time, START_TIME_SUM) ; end_time_utc_csv = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
        utc_datetime_start = datetime.strptime(start_time_utc_csv, "%Y-%m-%dT%H:%M:%SZ") ; utc_datetime_end = datetime.strptime(end_time_utc_csv, "%Y-%m-%dT%H:%M:%SZ")
        start_timestamp = utc_datetime_start.replace(tzinfo=pytz.utc).astimezone(tehran_tz)
        end_timestamp = utc_datetime_end.replace(tzinfo=pytz.utc).astimezone(tehran_tz)
        start_timestamp_csv = start_timestamp.strftime("%Y-%m-%d %H-%M-%S") ; end_timestamp_csv = end_timestamp.strftime("%Y-%m-%d %H-%M-%S")
        start_time_csv = start_timestamp_csv.replace(" ", "_").replace(":","-") ; end_time_csv = end_timestamp_csv.replace(" ", "_").replace(":","-")
        output_csv_name = f"{start_time_csv}__{end_time_csv}"
    else:
        start_time_csv = start_time.replace(" ", "_").replace(":","-"); end_time_csv = end_time.replace(" ", "_").replace(":","-")
        output_csv_name = f"{start_time_csv}__{end_time_csv}"
    # Create the output parent directory
    output_parent_dir = os.path.join(path_dir,f"{start_time_csv}__{end_time_csv}")
    os.makedirs(output_parent_dir, exist_ok=True)  
    # Generate metric_operation_mapping
    metric_operation_mapping = {}
    metric_operations = []
    if metric_file:
        # Extract metric operations from file names in the command-line argument
        metric_operations = [os.path.basename(metric_file).split('_')[0] for metric_file in metric_file]
        metric_operation_mapping = dict(zip(metric_file, metric_operations))
    else:
        # Read metric file paths and operations from the configuration file
        for metric_operation, metric_file in data_loaded.get('metrics', {}).items():
            metric_operations.append(metric_operation)
            metric_files_config = [metric_file.get('path', '')]
            metric_operation_mapping[metric_file.get('path', '')] = metric_operation

    start_time_utc = convert_tehran_to_utc(start_time, START_TIME_SUM)
    end_time_utc = convert_tehran_to_utc(end_time, -END_TIME_SUBTRACT)
    logging.info(f"status_reporter - start time of query in utc format: {start_time_utc}") ; logging.info(f"status_reporter - end time of query in utc format: {end_time_utc}")
    # Loop through each combination of time range, host, IP, PORT, and execute the curl command
    for mc_server, config in data_loaded.get('influxdbs', {}).items():
        dashborad_images_dict = {}
        all_hosts_csv_dict = {}
        dashboard_rm = None
        influx_ip = config.get('influx_ip')
        influx_port = config.get('influx_port')
        if img:
            time_variable = config['grafana_dashboards'].get('time_variable')
            api_key = config.get('grafana_api_key')
            grafana_ip = config.get('grafana_ip')
            grafana_port = config.get('grafana_port')
            grafana_url = f"http://{grafana_ip}:{grafana_port}"
            dashboard_rm = config['grafana_dashboards'].get('remove_dashboards', True)
            dashboards_json = config['grafana_dashboards'].get('dashboards_name', [])
            customized_panles = config['grafana_dashboards'].get('custom_panels', [])
            if config['grafana_dashboards']['report_images']:
                if 'panels_per_row' in config['grafana_dashboards']['report_images']:
                    panels_per_row = int(config['grafana_dashboards']['report_images'].get('panels_per_row'))
                else:
                    panels_per_row = int("3")
                if 'panels_per_column' in config['grafana_dashboards']['report_images']:
                    panels_per_column = int(config['grafana_dashboards']['report_images'].get('panels_per_column'))
                else:
                    panels_per_column = int("3")
                if 'max_panels' in config['grafana_dashboards']['report_images']:
                    max_panels = int(config['grafana_dashboards']['report_images'].get('max_panels'))
                else:
                    max_panels = None
                if max_panels is None:
                    max_panels = panels_per_row * panels_per_column
                if max_panels < panels_per_column:
                    panels_per_column = max_panels
                if 'panel_width' in config['grafana_dashboards']['report_images']:
                    panel_width = config['grafana_dashboards']['report_images'].get('panel_width')
                else:
                    panel_width = "800"
                if 'panel_height' in config['grafana_dashboards']['report_images']:
                    panel_height = config['grafana_dashboards']['report_images'].get('panel_height')
                else:
                    panel_height = "400"
            else:
                panels_per_row = int("3") ; panels_per_column = int("3")
                max_panels = panels_per_row * panels_per_column
                if max_panels < panels_per_column:
                    panels_per_column = max_panels
                panel_width = "800" ; panel_height = "400"

            logging.info(f"status_reporter - user need dashboard and images")
            dashboard_data_dict = dashboard_import(dashboards_json, api_key, grafana_url, customized_panles)
        for db_name, db_data in config.get('databases', {}).items():
            if f'{start_time_csv}__{end_time_csv}' not in dashborad_images_dict:
                dashborad_images_dict[f'{start_time_csv}__{end_time_csv}'] = {}
            for group_name, hostIsList in db_data['hosts'].items():
                dashborad_images_dict[f'{start_time_csv}__{end_time_csv}'][group_name] = {}
                if img:
                    if len(hostIsList) > 1:
                        all_host = 'All'
                        final_images_path_dict = images_export(dashboard_data_dict, api_key, grafana_url, start_time_utc, end_time_utc, output_parent_dir, hostIsList, panel_width, panel_height, time_variable, group_name)
                        all_img_dashboard_dict = dashboard_maker_with_image(final_images_path_dict, os.path.join(output_parent_dir,group_name+"_"+all_host+"-images"), panels_per_column, max_panels)
                        dashborad_images_dict[f'{start_time_csv}__{end_time_csv}'][group_name][all_host] = all_img_dashboard_dict # make dictionary inside dictionary
                output_csv_str = ["Host_name"]  # name of the first column in csv
                csvi = 0
                for host_name in hostIsList:
                    if img:
                        final_images_path_dict = images_export(dashboard_data_dict, api_key, grafana_url, start_time_utc, end_time_utc, output_parent_dir, [host_name], panel_width, panel_height, time_variable, group_name)
                        img_dashboard_dict = dashboard_maker_with_image(final_images_path_dict, os.path.join(output_parent_dir,group_name+"_"+host_name+"-images"), panels_per_column, max_panels)
                        dashborad_images_dict[f'{start_time_csv}__{end_time_csv}'][group_name][host_name] = img_dashboard_dict # make dictionary inside dictionary
                    output_csv_str.append(host_name)  # value inside the first column of csv
                    csvi += 1
                    retry = 2
                    null_result = 1
                    while retry:
                        for metric_file, metric_operation in metric_operation_mapping.items():
                            if os.path.isfile(metric_file):
                                all_metrics = get_metrics_from_file(metric_file)
                                for regex_metric in all_metrics['regex_m']:
                                    regex_query = subprocess.getoutput(f'curl -sG "http://{influx_ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SHOW MEASUREMENTS WITH MEASUREMENT =~ {regex_metric}"')
                                    regex_query_json = json.loads(regex_query)
                                    if 'results' in regex_query_json:
                                        if 'series' in regex_query_json['results'][0]:
                                            # Extract the new metrics
                                            new_metrics = [m[0] for m in regex_query_json['results'][0]['series'][0]['values']]
                                            # Append new measurements to the list if they don't already exist
                                            for new_metric in new_metrics:
                                                if new_metric not in all_metrics['normal_m']:
                                                    all_metrics['normal_m'].append(new_metric)
                                for final_metric_name in all_metrics['normal_m']:
                                    if csvi == 1:
                                        final_metric_name = final_metric_name.replace(" ", "").strip()
                                        output_csv_str[0] += f",{metric_operation}_{final_metric_name.replace('netdata.', '')}"
                                    csv_query = subprocess.getoutput(f'curl -sG "http://{influx_ip}:{influx_port}/query" --data-urlencode "db={db_name}" --data-urlencode "q=SELECT {metric_operation}(\\"value\\") FROM \\"{final_metric_name}\\" WHERE (\\"host\\" =~ /^{host_name}$/) AND time >= \'{start_time_utc}\' AND time <= \'{end_time_utc}\' fill(none)"')
                                    if csv_query:
                                        values = json.loads(csv_query).get('results', [{}])[0].get('series', [{}])[0].get('values', [])
                                        values = [str(v[1]) for v in values]
                                        output_csv_str[csvi] += "," + ",".join(values)
                                        if values:
                                            print(f"{BOLD}Add metric {RESET}'{YELLOW}{final_metric_name}{RESET}' {BOLD}server{RESET} '{YELLOW}{host_name}{RESET}'{BOLD} to CSV file{RESET}")
                                            null_result = 0
                                        else:
                                            # check database name
                                            check_database_name_result = subprocess.getoutput(f'curl -sG "http://{influx_ip}:{influx_port}/query" --data-urlencode "q=SHOW DATABASES"')
                                            db_json_data = json.loads(check_database_name_result)
                                            databases = [db[0] for db in db_json_data["results"][0]["series"][0]["values"]]
                                            if db_name in databases:
                                                logging.info(f"status_reporter - The database {db_name} is exist in {influx_ip}")
                                                print(f"The database {db_name} is exist in {influx_ip}")
                                                # check metric name
                                                check_metric_name_result = subprocess.getoutput(f'curl -sG "http://{influx_ip}:{influx_port}/query" --data-urlencode "q=SHOW MEASUREMENTS ON {db_name} WITH MEASUREMENT =~ /{final_metric_name}/"')
                                                metric_json_data = json.loads(check_metric_name_result)
                                                if "series" in metric_json_data["results"][0]:
                                                    logging.info(f"status_reporter - metric {final_metric_name} is exist in {db_name}")
                                                    print(f"metric {final_metric_name} is exist in {db_name}")
                                                    # check host name
                                                    check_host_name_result = subprocess.getoutput(f'curl -sG "http://{influx_ip}:{influx_port}/query" --data-urlencode "q=SHOW TAG VALUES ON {db_name} FROM \\"{final_metric_name}\\" WITH KEY = \\"host\\""')
                                                    host_json_data = json.loads(check_host_name_result)
                                                    if "series" in host_json_data["results"][0]:
                                                        host_names = [item[1] for item in host_json_data["results"][0]["series"][0]["values"]]
                                                        if host_name in host_names:
                                                            # check time range
                                                            logging.error(f"status_reporter - database name: {db_name}, metric name: {final_metric_name}, host name: {host_name} are correct but your TIME RANGE doesn't have any value")
                                                            print(f"database name: {db_name}, metric name: {final_metric_name}, host name: {host_name} are correct but \033[91myour TIME RANGE doesn't have any value !\033[0m")
                                                        else:
                                                            logging.error(f"status_reporter - The host {host_name} name is wrong")
                                                            print(f"\033[91mThe host {host_name} name is wrong\033[0m")
                                                    else:
                                                        logging.error(f"status_reporter - metric: {final_metric_name} doesn't have host: {host_name} so value is null !")
                                                        print(f"\033[91mmetric: {final_metric_name} doesn't have host: {host_name} so value is null !\033[0m")
                                                else:
                                                    logging.error(f"status_reporter - metric {final_metric_name} doesn't exist in {db_name}")
                                                    print(f"\033[91mmetric {final_metric_name} doesn't exist in {db_name}\033[0m")
                                            else:
                                                logging.error(f"status_reporter - The database {db_name} doesn't exist in {influx_ip}")
                                                print(f"\033[91mThe database {db_name} doesn't exist in {influx_ip}\033[0m")
                                                exit()
                                    else:
                                        ping_process = subprocess.Popen(["ping", "-c", "1", influx_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                        ping_output, ping_error = ping_process.communicate()
                                        if ping_process.returncode == 0:
                                            logging.info(f"status_reporter - Server {influx_ip} port {influx_port} is wrong")
                                            print(f"\033[91mServer {influx_ip} is reachable but port {influx_port} is wrong\033[0m")
                                        elif ping_process.returncode == 1:
                                            logging.critical(f"status_reporter - Server {influx_ip} is unreachable")
                                            print(f"\033[91mServer {influx_ip} is unreachable so your IP is wrong\033[0m")
                                        exit()
                        if null_result:
                            retry -=1
                            time.sleep(10)
                            if retry == 0:
                                print(f"\033[91mMaximum retries reached. database name: {db_name} in host name: {host_name} have not any value for all metrics\033[0m")
                        else:
                            retry = 0
                # Write the CSV file for each time range
                output_csv_path = os.path.join(output_parent_dir,f"{mc_server}_{db_name}_{group_name}_{output_csv_name}.csv")
                with open(output_csv_path, 'w') as csv_file:
                    for line in output_csv_str:
                        csv_file.write(line + "\n")
                all_hosts_csv_dict[group_name] = output_csv_path
        if dashboard_rm is True and img:
            remove_dashboard(grafana_url, api_key, dashboard_data_dict)
    print("")
    if img:
        print(f"{BOLD}Done! Csv and Images are saved in the {RESET}{YELLOW}'{output_parent_dir}'{RESET}{BOLD} directory{RESET}")
    else:
        print(f"{BOLD}Done! Csv is save in the {RESET}{YELLOW}'{output_parent_dir}'{RESET}{BOLD} directory{RESET}")
    print("")
    print(f"{YELLOW}========================================{RESET}")
    print("")
    return  dashborad_images_dict, all_hosts_csv_dict
  
def main(metric_file, path_dir, time_range, img):
    data_loaded = load_config(config_file)
    log_level = data_loaded['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level_upper in valid_log_levels:
            log_dir_run = subprocess.run(f"sudo mkdir {log_path} > /dev/null 2>&1 && sudo chmod -R 777 {log_path}", shell=True)
            logging.basicConfig(filename= f'{log_path}all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")
    
    logging.info("\033[92m****** status reporter main function start ******\033[0m")   
    metric_file= metric_file.split(',') if metric_file else []
    path_dir = path_dir or data_loaded.get('output_path') or "." 
    time_range = time_range if time_range else data_loaded.get('time', [])['time_range']
    dashborad_images, all_hosts_csv_dict = get_report(data_loaded, metric_file, path_dir, time_range, img)
    logging.info("\033[92m****** status reporter main function end ******\033[0m")
    return dashborad_images, all_hosts_csv_dict, data_loaded['influxdbs'][list(data_loaded['influxdbs'])[0]]['grafana_dashboards']['time_variable'] # it is temp remove it ########

if __name__ == "__main__":
    # Parse command-line arguments for your new script
    parser = argparse.ArgumentParser(description="status reporter: ")
    parser.add_argument("-m", "--metric_file", help="Enter your metric files comma-separated list of metric file paths or read them from config file.")
    parser.add_argument("-o", "--path_dir", help="Enter path to the parent directory or it use current dir as default")
    parser.add_argument("-t", "--time_range", help="Enter time range in the format 'start_time,end_time' or read time range from config file")
    parser.add_argument("--img", action="store_true", help="Create images and graphs")
    args = parser.parse_args()
    # Call your main function with the provided arguments
    main(metric_file=args.metric_file, path_dir=args.path_dir, time_range=args.time_range, img=args.img)