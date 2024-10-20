import json
import os
import subprocess
import datetime
import time
import requests
import uuid
import argparse

#### variables
width = 800
height = 400
timezone = "Asia%2FTehran"

def utc_to_unix_time(utc_time_str):
    # Parse the string into a datetime object
    utc_time = datetime.datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    # Convert to Unix timestamp (in seconds)
    unix_timestamp_seconds = int(utc_time.replace(tzinfo=datetime.timezone.utc).timestamp())
    # Convert to Unix timestamp (in milliseconds)
    unix_timestamp_milliseconds = unix_timestamp_seconds * 1000
    return unix_timestamp_milliseconds

def get_existing_dashboard_names(api_key, grafana_url):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{grafana_url}/api/search", headers=headers)
    if response.status_code == 200:
        dashboards = response.json()
        return {dash['title'] for dash in dashboards}
    else:
        print(f"Failed to retrieve dashboards. Status code: {response.status_code}")
        return set()

def find_unique_dashboard_name(base_name, existing_names):
    name = base_name
    counter = 1
    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1
    return name

#### import dashboard to grafana
def dashboard_import(dashboard_data, api_key, grafana_url):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"dashboard": dashboard_data,"folderId": 0,"overwrite": False}
    # Get existing dashboard names
    existing_names = get_existing_dashboard_names(api_key, grafana_url)
    if dashboard_data["title"] in existing_names:
        # Determine the unique title
        unique_title = find_unique_dashboard_name(dashboard_data["title"], existing_names)
        payload["dashboard"]["id"] = str(uuid.uuid4())
        payload["dashboard"]["uid"] = str(uuid.uuid4())
        payload["dashboard"]["title"] = unique_title
        dashboard_uid_img = payload["dashboard"]["uid"]
        dashboard_name = payload["dashboard"]["title"]
    else:
        payload["dashboard"]["uid"] = str(dashboard_data["uid"])+"-kara"
        payload["dashboard"]["title"] = dashboard_data["title"]
        payload["dashboard"]["id"] = str(dashboard_data["id"])+"-kara"
        dashboard_uid_img = dashboard_data["uid"]
        dashboard_name = payload["dashboard"]["title"]
    # Send the POST request to import the dashboard
    response = requests.post(grafana_url+"/api/dashboards/db", headers=headers, json=payload)
    if response.status_code == 200:
        print(f'Dashboard imported successfully ({payload["dashboard"]["title"]})')
    else:
        print(f'Failed to import dashboard ({payload["dashboard"]["title"]}) Status code: {response.status_code}')
        exit()
    time.sleep(10)
    return dashboard_uid_img, dashboard_name

#### make image and export panels
def images_export(dashboard_data, dashboard_uid_img, dashboard_name, api_key, grafana_url, start_unix, end_unix, image_date, output, servers_name):
    panels = dashboard_data.get("panels", [])
    for server_name in servers_name:
        each_server_path = f"{output}/{server_name}-images"
        if not os.path.exists(each_server_path):
            os.makedirs(each_server_path)
        for panel in panels:
            panel_id = panel["id"]
            panel_title = panel["title"].replace(" ", "_").replace("/", "_").replace("&", "_") 
            # Construct the cURL command
            curl_command = (f'curl -o {each_server_path}/{panel_title}_{server_name}_{image_date}.png -H "Authorization: Bearer {api_key}" "{grafana_url}/render/d-solo/{dashboard_uid_img}/{dashboard_name}?orgId=1&var-hostls={server_name}&from={start_unix}&to={end_unix}&panelId={panel_id}&width={width}&height={height}&tz={timezone}"')
            try:
                result = subprocess.run(curl_command, shell=True, check=True, capture_output=True, text=True)
                # Check if the image file is a valid PNG
                image_path = f"{each_server_path}/{panel_title}_{server_name}_{image_date}.png"
                with open(image_path, 'rb') as img_file:
                    magic_number = img_file.read(8)
                    if magic_number.startswith(b'\x89PNG'):
                        print(f"Image for panel '{panel_title}' (ID: {panel_id}) is a valid and saved successfully for server: {server_name}")
                    else:
                        print(f"Warning: Image for panel '{panel_title}' might be invalid for server {server_name}. First 1000 characters of the file:")
                        img_file.seek(0)
                        print(img_file.read(1000).decode(errors='replace'))  # Print the first 1000 bytes of the file
            except subprocess.CalledProcessError as e:
                print(f"Failed to export image for panel '{panel_title}'. Error: {e}")
    print("All panel images have been processed.")

def main(start_utc, end_utc, data_config, output, servers_name):
    grafana_conf = data_config.get('grafana', {})
    dashboard_json = grafana_conf.get('dashboard_json_file')
    grafana_url = grafana_conf.get('grafana_url')
    api_key = grafana_conf.get('api_key')

    if start_utc.split('T')[0] == end_utc.split('T')[0]:
        image_date = f"{start_utc.split('T')[0]}" 
    elif start_utc.split('T')[0] != end_utc.split('T')[0]:
        image_date = f"{start_utc.split('T')[0]}_to_{end_utc.split('T')[0]}" 
    start_unix = utc_to_unix_time(start_utc)
    end_unix = utc_to_unix_time(end_utc)

    if os.path.exists(dashboard_json):
        with open(dashboard_json, "r") as file:
            dashboard_data = json.load(file)
    else:
        print("json file of dashboard is required ! please select it.")
        exit()

    dashboard_uid_img, dashboard_name = dashboard_import(dashboard_data, api_key, grafana_url)
    images_export(dashboard_data, dashboard_uid_img, dashboard_name, api_key, grafana_url, start_unix, end_unix, image_date, output, servers_name)
    
if __name__ == "__main__":
    # Parse command-line arguments for your new script
    parser = argparse.ArgumentParser(description="image renderer: ")
    parser.add_argument("-st", "--start_utc", help="Enter start time in the format '%Y-%m-%dT%H:%M:%SZ' or read time range from config file")
    parser.add_argument("-et", "--end_utc", help="Enter end time in the format '%Y-%m-%dT%H:%M:%SZ' or read time range from config file")
    parser.add_argument("-dc", "--data_config", help="Enter yaml file data")
    parser.add_argument("-o", "--output", help="Enter output path")
    parser.add_argument("-sn", "--servers_name", help="Enter list of servers")
    args = parser.parse_args()
    # Call your main function with the provided arguments
    main(start_utc=args.start_utc, end_utc=args.end_utc, data_config=args.data_config, output=args.output, servers_name=args.servers_name)