import requests
from allauth.socialaccount.models import SocialToken
import jwt
import time
import os
from dotenv import load_dotenv
load_dotenv()

def generate_github_app_jwt():
    GITHUB_APP_ID = os.environ.get('GITHUB_APP_ID')
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": GITHUB_APP_ID
    }
    token = jwt.encode(payload, os.environ.get('GITHUB_APP_PRIVATE_KEY'), algorithm="RS256")
    return token  

def get_installation_token(installation_id):
    jwt_token = generate_github_app_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()['token']


def get_diff_from_github(url, installation_id):
    if "github.com" in url and "api.github.com" not in url:
        url = url.replace("github.com/", "api.github.com/repos/")
        url = url.replace("/pull/", "/pulls/")
        url = url.removesuffix(".diff")
    
    token = get_installation_token(installation_id)
    if not token:
        return ""
    
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"Bearer {token}"
    }
    print(token)
    response = requests.get(url, headers=headers)
    return response.text