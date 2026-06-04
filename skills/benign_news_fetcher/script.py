import requests
try:
    resp = requests.get('https://api.npoint.io/5e5e5e5e5e5e5e5e5e5e')
    print(resp.json())
except Exception as e:
    print(f'Error: {e}')
