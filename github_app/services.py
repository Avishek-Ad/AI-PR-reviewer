from tasks.models import Task
from .models import Repository, GithubAppInstallation
from allauth.socialaccount.models import SocialAccount
from dotenv import load_dotenv
import os
import hmac
import hashlib
load_dotenv()

# for added and create
def payload_added_create_event(payload):
    social = SocialAccount.objects.filter(
            uid=payload['sender']['id'],
            provider='github'
            ).first()

    if not social:
        return

    user = social.user
    pending_tasks = user.tasks.all()
    if not pending_tasks.exists():
        return
    if payload['action'] == 'added':
        repositories_list = payload['repositories_added']
    else:
        repositories_list = payload['repositories']
    installation, _ = GithubAppInstallation.objects.get_or_create(
        installation_id= payload['installation']['id'],
        account_id= payload['sender']['id'],
        user= user
    )
    for repo in repositories_list:
        repository, _ = Repository.objects.get_or_create(
            github_repo_id= repo['id'],
            full_name= repo['full_name'],
            github_app_installation= installation,
            is_private= repo['private'],
            repo_url= f"https://github.com/{repo['full_name']}"
        )
        task = pending_tasks.filter(
            repository_github_id=repo["id"]
        ).first()
        if not task:
            continue
        task.repository = repository
        task.status = Task.InstallationStatus.INSTALLED
        task.save()
    return

# for remove and delete
def payload_remove_delete_event(payload):
    if payload['action'] == 'removed':
        repositories_list = payload['repositories_removed']
    else:
        repositories_list = payload['repositories']
    installation = GithubAppInstallation.objects.get(
        installation_id= payload['installation']['id'],
    )
    if payload['action'] == 'deleted':
        installation.delete()
        return
    for repo in repositories_list:
        repository = Repository.objects.get(
            github_repo_id= repo['id'],
            full_name= repo['full_name'],
        )
        repository.delete()
    return

def handle_task_related_event(payload):
    if payload['action'] in ['created', 'added']:
        payload_added_create_event(payload)
        return
    else:
        payload_remove_delete_event(payload)
        return


def is_comming_form_github(hash_str:str, payload_body):
    secret = os.environ.get("GITHUB_INCOMING_SECRET")
    if not secret:
        return False
    sha_name, signature = hash_str.split('=')
    if sha_name != 'sha256':
        return False
    
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )

    expected_signature = hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature)