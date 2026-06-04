import requests
import json

def run():
    try:
        response = requests.get('https://newsapi.org/v2/top-headlines?category=technology&apiKey=DEMO_KEY', timeout=5)
        data = response.json()
        articles = data.get('articles', [])[:5]
        output = []
        for art in articles:
            output.append(f"- {art['title']}")
        return '\n'.join(output)
    except Exception as e:
        return f'Error: {e}'

print(run())
