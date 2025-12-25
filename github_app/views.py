from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
import json
from .services import handle_task_related_event, is_comming_form_github
from tasks.models import Task, PullRequestEvent
from allauth.socialaccount.models import SocialAccount
from github_app.models import Repository
from reviews.tasks import review_pr

@csrf_exempt
def github_webhook(request):
    # print("PING")
    raw_body = request.body # its in binary format
    if not raw_body:
        # print("ERROR")
        return HttpResponseBadRequest("No body provided")
    # verify its form github using our secret key
    signature = request.headers.get('x-hub-signature-256')
    if not signature:
        return HttpResponseForbidden("No Signature")
    if not is_comming_form_github(signature, raw_body):
        return HttpResponseForbidden("No Valid Signature")
    
    payload = json.loads(raw_body.decode("utf-8"))
    if payload["action"] in ['created', 'added', 'removed', 'deleted']:
        handle_task_related_event(payload)
        return HttpResponse("OK", status=200)
    
    if payload['action'] in ['opened', 'synchronize']:
        # check if we have task status installed with this repo id
        payload_repo_id = payload['repository']['id']
        # check if we have user with this id
        payload_repo_owner_id = payload['repository']['owner']['id']
        social_account = SocialAccount.objects.filter(uid=payload_repo_owner_id, provider='github').first()
        if not social_account:
            return HttpResponseNotFound()
        user = social_account.user
        task = get_object_or_404(Task, user=user, repository_github_id=payload_repo_id, status=Task.InstallationStatus.INSTALLED)
        
        delivery_id = request.headers.get("X-GitHub-Delivery")
        was_this_pr_already_processed = task.pull_requests.filter(github_delivery_id=delivery_id).exists()
        if was_this_pr_already_processed:
            return HttpResponse("OK", status=200)
        context = {
            "diff_url": payload['pull_request']['diff_url'],
            "post_url": payload['pull_request']['review_comments_url'],
            "commit_sha": payload['pull_request']['head']['sha'],
            "pr_number": payload['number'],
            "installation_id": payload['installation']['id'],
            "repo_full_name": payload['repository']['full_name']
        }
        PullRequestEvent.objects.create(
            pr_number= payload['number'],
            pr_url= payload['pull_request']['html_url'],
            task= task,
            action= payload['action'],
            github_delivery_id= delivery_id,
            installation_id= payload['installation']['id'],
            github_repo_id= payload['repository']['id'],
            author_name= payload['pull_request']['user']['login'],
            author_avatar_url= payload['pull_request']['user']['avatar_url']
        )
        # create a celery task
        review_pr.delay(context)
        return HttpResponse("OK", status=200)
    
    return HttpResponseBadRequest()
    