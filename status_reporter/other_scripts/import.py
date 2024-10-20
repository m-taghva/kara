import requests
import json

grafana_url = "http://localhost:3000/api/dashboards/db"
api_key = "eyJrIjoiUlBRSzl0R0Y3OEFQMWJGa0YxTWtZb1JUTk52OG1wR0UiLCJuIjoiaW1wb3J0IiwiaWQiOjF9"
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# Load the dashboard JSON file
with open("Partial_Monitoring-1725861552265.json", "r") as file:
    dashboard_json = json.load(file)

# Prepare the payload
payload = {
    "dashboard": dashboard_json,
    "folderId": 0,
    "overwrite": True
}

# Grafana API expects the payload to include a "dashboard" field with a name, UID, and other properties.
# Ensure the loaded JSON contains these properties.
# If not, include them in the payload like this:
payload["dashboard"]["id"] = "qwer3"
payload["dashboard"]["uid"] = "1234456637"
payload["dashboard"]["title"] = "wsx3"

# Send the POST request to import the dashboard
response = requests.post(grafana_url, headers=headers, json={"dashboard": payload["dashboard"], "folderId": payload["folderId"], "overwrite": payload["overwrite"]})

# Send the POST request to import the dashboard
#response = requests.post(grafana_url, headers=headers, json=payload)

# Check if the import was successful
if response.status_code == 200:
    print("Dashboard imported successfully.")
else:
    print(f"Failed to import dashboard. Status code: {response.status_code}")
    print(response.text)