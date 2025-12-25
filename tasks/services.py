
from allauth.socialaccount.models import SocialToken
import requests
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List

class RepoResponseSchema(BaseModel):
    id: int
    full_name: str
    updated_at: datetime
    private: bool

def _get_users_repos(request) -> List[RepoResponseSchema]:
    user = request.user
    token = SocialToken.objects.filter(account__user=user, account__provider="github").first()

    if not token:
        return []

    repos = []
    page = 1
    per_page = 100

    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Accept": "application/vnd.github.v3+json"
    }

    while True:
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
        }
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code != 200:
            break

        if not response.json():
            break
        
        for repo in response.json():
            updated_at = datetime.now(timezone.utc) - datetime.fromisoformat(repo['updated_at'].replace("Z", "+00:00"))
            repos.append({
                'id': repo['id'],
                'full_name': repo['full_name'],
                'updated_at': updated_at,
                'private': repo['private']
            })
        page += 1
    return repos

def filter_list_of_dicts(uf_data, query):
    filtered_data = []
    for data in uf_data:
        if query.lower() in data['full_name'].lower():
            filtered_data.append(data)
    return filtered_data