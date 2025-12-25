import requests
from allauth.socialaccount.models import SocialToken
import jwt
import time
import os
from dotenv import load_dotenv
from tiktoken import encoding_for_model
load_dotenv()

encoding = encoding_for_model('gpt-4o')

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

def get_hunks_with_numbers(hunk):
    # return in format
    # if added, Line 15: + print("Hello world!")
    # or if no change, Line 10: print("Hello World")
    # or if removed, Removed: print("Hello world")
    lines = []
    current_line = hunk.target_start

    for line in hunk:
        if line.is_added:
            lines.append(f"Line {current_line}: {line.value.strip()}")
            current_line += 1
        elif line.is_context:
            lines.append(f"Line {current_line}: {line.value.strip()}")
            current_line += 1
        elif line.is_removed:
            lines.append(f"REMOVED: {line.value.strip()}")
    return "\n".join(lines)

def count_token(hunk_string):
    return len(encoding.encode(hunk_string))

def chunk_hunks(patch, token_limit=4000):
    current_chunks = []
    current_tokens = 0
    for patch_file in patch:
        for hunk in patch_file:
            # get hunks with more info
            hunk_with_number = get_hunks_with_numbers(hunk)
            hunk_str = f"File: {patch_file.path}\n{hunk_with_number}\n"
            hunk_token = count_token(hunk_str)

            # further breaking
            if hunk_token > token_limit:
                if current_chunks:
                    yield current_chunks
                    current_chunks = []
                    current_tokens = 0
                
                lines = hunk_str.split('\n')
                sub_chunks = []
                sub_tokens = 0
                for line in lines:
                    line_token = count_token(line)
                    if sub_tokens + line_token > token_limit:
                        yield sub_chunks
                        sub_chunks = []
                        sub_tokens = 0
                    else:
                        sub_chunks.append(line)
                        sub_tokens += line_token
                if sub_chunks:
                    yield sub_chunks

            # regular chunking by hunks
            if current_tokens + hunk_token > token_limit:
                yield current_chunks

                current_chunks = []
                current_tokens = 0
            else:
                current_chunks.append(hunk_str)
                current_tokens += hunk_token
    if current_chunks:
        yield current_chunks