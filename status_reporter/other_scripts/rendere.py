import json
import os
import subprocess
import requests
import datetime
from datetime import datetime , timedelta

# Function to convert Tehran timestamp to UTC
def convert_tehran_to_utc(tehran_timestamp):
    tehran_timestamp_convert = int(datetime.strptime(tehran_timestamp, "%Y-%m-%d %H:%M:%S").timestamp())
    timestamp_add = tehran_timestamp_convert
    utc_timestamp_result = datetime.utcfromtimestamp(timestamp_add).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_timestamp_result

# Configuration
dashboard_json_file = "dashboard_formatted.json"  # Path to the dashboard JSON file
output_image_path = "./images/"  # Directory where images will be saved
grafana_url = "http://localhost:3000/render/d-solo"
api_key = "eyJrIjoiTTBUMkZ0Wk5INVJhNldSY3JEZnhicGNpdTJQVVR2NU0iLCJuIjoidGVzdDIiLCJpZCI6MX0="  # Replace with your Grafana API key
dashboard_uid = "1AJqM_CIk"  # Replace with the dashboard UID
#start_time = "2024-09-09 09:15:00"
#end_time = "2024-09-09 09:20:00"
#utc_start = convert_tehran_to_utc(start_time)
#utc_end = convert_tehran_to_utc(end_time)
#print(utc_start,utc_end)

time_range = {
    "from": "1725781290207",  # Adjust these times to your range
    "to": "1725781590208"
}
width = 1000  # Image width
height = 500  # Image height
timezone = "Asia%2FTehran"  # Timezone
# Ensure the output image path exists
if not os.path.exists(output_image_path):
    os.makedirs(output_image_path)
# Load the dashboard JSON
with open(dashboard_json_file, "r") as file:
    dashboard_data = json.load(file)

# # Prepare the payload and header
# headers = {"Content-Type": "application/json","Authorization": f"Bearer {api_key}"}
# payload = {"dashboard": dashboard_data,"folderId": 0,"overwrite": True}
# # Send the POST request to import the dashboard
# response = requests.post(grafana_url, headers=headers, json=payload)
# # Check if the import was successful
# if response.status_code == 200:
#     print("Dashboard imported successfully.")
# else:
#     print(f"Failed to import dashboard. Status code: {response.status_code}")

# Extract panels directly from the JSON (top-level "panels" key)
panels = dashboard_data.get("panels", [])
# Loop through the panels and generate images for each
for panel in panels:
    panel_id = panel["id"]
    panel_title = panel["title"].replace(" ", "_").replace("/", "_").replace("&", "_")  # Sanitize the title for the file name
    # Construct the cURL command
    curl_command = (
        f'curl -s -o {output_image_path}{panel_title}.png'
        f'-H "Authorization: Bearer {api_key}" '
        f'"{grafana_url}/{dashboard_uid}/{panel_title}?orgId=1&from={time_range["from"]}&to={time_range["to"]}&panelId={panel_id}&width={width}&height={height}&tz={timezone}"'
        #f'"{grafana_url}/{dashboard_uid}/{panel_title}?orgId=1&from={utc_start}&to={utc_end}&panelId={panel_id}&width={width}&height={height}&tz={timezone}"'
    )
    # Execute the cURL command
    try:
        subprocess.run(curl_command, shell=True, check=True)
        print(f"Image for panel '{panel_title}' (ID: {panel_id}) saved successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to export image for panel '{panel_title}'. Error: {e}")
print("All panel images have been processed.")