import requests

grafana_url = "http://localhost:3000/api/health"
api_key = "eyJrIjoiaTkzVldCSXdYSW16c05DdHU5d2RIMkJTZWJEbHo4RDkiLCJuIjoiaW1wb3J0IiwiaWQiOjF9"
headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get(grafana_url, headers=headers)
    print(response.status_code)
    print(response.json())
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
