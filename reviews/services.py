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
    # print(token)
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

def get_total_line_changed(patch):
    added_lines = 0
    removed_lines = 0
    for patch_file in patch:
        added_lines += patch_file.added
        removed_lines += patch_file.removed
    return added_lines + removed_lines

def is_line_in_diff(patch_file, target_line_number):
    for hunk in patch_file:
        if hunk.target_start <= target_line_number < hunk.target_start + hunk.target_length:
            for line in hunk:
                if line.target_line_no == target_line_number and not line.is_removed:
                    return True
    return False

def final_verification(patch, responses):
    unique_responses = {}
    number_of_line_changed = get_total_line_changed(patch)

    # eg of responses
    # ReviewResponse(reviews=[CodeReview(
                                # file='README.md', 
                                # line_number=4, 
                                # type='readability', 
                                # severity='minor', 
                                # comment='informationkwjsdf.', 
                                # suggestion='f the repository.', 
                                # confidence_score=0.8), ...])
    for response in responses:
        for review in response.reviews:
            if review.confidence_score < 0.6:
                continue
            
            # filter out low severity and low confidence comment based on PR size
            if number_of_line_changed > 1000 and review.severity != "critical":
                continue
            if number_of_line_changed > 500 and review.severity not in ['critical', 'major']:
                continue

            # ensure line number llm gave has a code + diff
            # we have property hunk.target_start and hunk.target_length
            for patch_file in patch:
                does_exists = is_line_in_diff(patch_file, review.line_number)
                if not does_exists:
                    continue
            
            prev_review = unique_responses.get(f"{review.file}-{review.line_number}")
            if prev_review:
                if prev_review.severity == "critical":
                    continue
                if (review.confidence_score > prev_review.confidence_score) or review.severity == "critical":
                    unique_responses[f"{review.file}-{review.line_number}"] = review
            else:
                unique_responses[f"{review.file}-{review.line_number}"] = review
    return list(unique_responses.values())

def clear_pending_reviews(token, repo_full_name, pull_number):
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pull_number}/reviews"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    
    reviews = requests.get(url, headers=headers).json()
    
    for r in reviews:
        if r.get('state') == 'PENDING':
            delete_url = f"{url}/{r['id']}"
            requests.delete(delete_url, headers=headers)
            # print(f"Deleted pending review {r['id']}")


def post_review_to_github(context, reviews):
    token = get_installation_token(context['installation_id'])
    pull_number = context['pr_number']
    repo_full_name = context['repo_full_name']

    clear_pending_reviews(token, repo_full_name, pull_number)

    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pull_number}/reviews"
    
    comments = []
    for r in reviews:
        comments.append({
            "path": r.file,
            "line": int(r.line_number),
            "side": "RIGHT",
            "body": f"**{r.type.upper()}** ({r.severity}): {r.comment}\n\n**Suggestion:** {r.suggestion}"
        })
    
    payload = {
        "event": "COMMENT",
        "body": "AI Code Review Summary: I found some potential issues.",
        "comments": comments
    }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        # print(f"GitHub API Error {response.status_code}: {response.text}")
        return response.text
    return response.json()
