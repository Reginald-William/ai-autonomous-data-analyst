from dotenv import load_dotenv
load_dotenv()

import requests
import os
import pprint

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

pprint.pprint(response.json())
