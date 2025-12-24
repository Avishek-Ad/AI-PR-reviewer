from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from github_app.models import GithubAppInstallation, Repository
from .models import Task
from django_htmx.http import HttpResponseClientRedirect

from allauth.socialaccount.models import SocialToken
import requests
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List
from pprint import pprint

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
    
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    
    result = []
    for repo in response.json():
        updated_at = datetime.now(timezone.utc) - datetime.fromisoformat(repo['updated_at'].replace("Z", "+00:00"))
        result.append({
            'id': repo['id'],
            'full_name': repo['full_name'],
            'updated_at': updated_at,
            'private': repo['private']
        })
    return result


def _get_users_repos_gql(request):
    # Retrieve the token string from the SocialToken model instance
    social_token = SocialToken.objects.filter(
        account__user=request.user, 
        account__provider="github"
    ).first()

    if not social_token:
        return []
    
    token_string = social_token.token
    url = "https://api.github.com/graphql"
    query = """
    query {
      viewer {
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            databaseId
            nameWithOwner
            updatedAt
            isPrivate
          }
        }
      }
    }
    """
   
    headers = {"Authorization": f"Bearer {token_string}"}
    
    try:
        response = requests.post(url, json={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            return []
            
        raw_repos = data['data']['viewer']['repositories']['nodes']
        
        # Clean and format the data
        cleaned_repos = []
        for repo in raw_repos:
            cleaned_repos.append({
                "id": repo["databaseId"],
                "full_name": repo["nameWithOwner"],
                "updated_at": datetime.now(timezone.utc)-datetime.fromisoformat(repo["updatedAt"].replace("Z", "+00:00")),
                "private": repo["isPrivate"]
            })
        return cleaned_repos
        
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"Error: {e}")
        return []

def filter_list_of_dicts(uf_data, query):
    filtered_data = []
    for data in uf_data:
        if query.lower() in data['full_name'].lower():
            filtered_data.append(data)
    return filtered_data

@login_required(login_url='/')
def task_create(request):
    if request.POST:
        repository = request.POST.get('repository')
        if not repository:
            return render(request, 'tasks/partials/error.html', {'message': "Please select a Repository"})
        repo = Repository.objects.filter(github_repo_id=repository).first()
        if not repo:
            # edge case what if this was done before and user didnot install and created again
            task_exists = Task.objects.filter(
                repository_github_id=repository,
                user= request.user,
                status= Task.InstallationStatus.PENDING,
            ).exists()
            if not task_exists:
                Task.objects.create(
                    repository_github_id=repository,
                    user= request.user,
                    status= Task.InstallationStatus.PENDING,
                )
            # send user to the github to install the app for this repo
            # the github will send a webhook with action="created" when created a webhook
            return HttpResponseClientRedirect('https://github.com/apps/mine-ai-code-reviewer/installations/new')
        # create task entry, github installation entry and repository entry
        if repo.tasks:
            return render(request, 'tasks/partials/error.html', {'message': "A task already existes for this Repository"})
        Task.objects.create(
            repository = repo,
            repository_github_id=repository,
            user= request.user,
            status= Task.InstallationStatus.INSTALLED,
        )
        return redirect('dashboard-page')

    # cache 10 minute
    repos = cache.get(f"{request.user.pk}-repos")
    if not repos:
        repos = _get_users_repos(request)
        cache.set(f"{request.user.pk}-repos", repos, timeout=10*60) # 10 minute

    query = request.GET.get('query', '')
    # print("Q",query)
    if query:
        repos = filter_list_of_dicts(repos, query)
    context = {
        'available_repos': repos
    }
    if request.htmx:
        return render(request, 'tasks/partials/list-repos.html', context)
    return render(request, 'tasks/task-create.html', context)


@login_required(login_url='/')
def task_events(request, repo_name):
    context = {
        'repo_name': repo_name, #'Avishek-Ad/file-share',
        'repo_url': 'https://github.com/Avishek-Ad/file-share',
        'events': [
            {
                'pr_number': 42,
                'title': 'Feat: Add multi-file upload support',
                'author': 'Avishek-Ad',
                'author_avatar': 'https://github.com/Avishek-Ad.png',
                'timestamp': datetime.now(timezone.utc),
                'status': 'completed', # or 'processing'
                'github_url': 'https://github.com/Avishek-Ad/file-share/pull/42'
            },
        ]
    }
    return render(request, 'tasks/task-events.html', context)
