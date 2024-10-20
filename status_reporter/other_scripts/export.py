import requests
import json

# Configuration
grafana_url = "http://localhost:3000/api/dashboards/uid/1AJqM_CIk"
api_key = "eyJrIjoiZTJxaXhRUnBnMFIzQnFVbHlJbjFacVF4SmVkNjJBRkwiLCJuIjoiMTAiLCJpZCI6MX0="
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Send GET request to fetch dashboard
response = requests.get(grafana_url, headers=headers)

if response.status_code == 200:
    dashboard_json = response.json()["dashboard"]

    # Save formatted JSON to file
    with open("dashboard_formatted.json", "w") as file:
        json.dump(dashboard_json, file, indent=4)
    
    print("Dashboard exported and formatted successfully.")
else:
    print(f"Failed to export dashboard. Status code: {response.status_code}")
    print(response.text)
