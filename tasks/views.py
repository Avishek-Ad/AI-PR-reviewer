from django.shortcuts import render, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from github_app.models import Repository
from .models import Task
from django_htmx.http import HttpResponseClientRedirect
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .services import _get_users_repos, filter_list_of_dicts

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
        if repo.tasks.filter(user=request.user).exists():
            return render(request, 'tasks/partials/error.html', {'message': "A task already existes for this Repository"})
        Task.objects.create(
            repository = repo,
            repository_github_id=repository,
            user= request.user,
            status= Task.InstallationStatus.INSTALLED,
        )
        return HttpResponseClientRedirect(reverse(viewname='dashboard-page'))

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
    print(repo_name)
    repository = Repository.objects.filter(full_name=repo_name).first()
    if not repository:
        return render(request, 'tasks/task-events.html')
    
    task = request.user.tasks.filter(repository=repository).first()
    if not task:
        return render(request, 'tasks/task-events.html')
    
    context = {
        'repo_name': repo_name, #'Avishek-Ad/file-share',
        'repo_url': f"https://github.com/{repo_name}",
        'events': [
            {
                'pr_number': 42,
                'title': 'Feat: Add multi-file upload support',
                'author': 'Avishek-Ad',
                'author_avatar': 'https://github.com/Avishek-Ad.png',
                'timestamp': timezone.now(),
                'status': 'completed', # or 'processing'
                'github_url': 'https://github.com/Avishek-Ad/file-share/pull/42'
            },
            {
                'pr_number': 42,
                'title': 'Feat: Add multi-file upload support',
                'author': 'Avishek-Ad',
                'author_avatar': 'https://github.com/Avishek-Ad.png',
                'timestamp': timezone.now(),
                'status': 'completed', # or 'processing'
                'github_url': 'https://github.com/Avishek-Ad/file-share/pull/42'
            }
        ]
    }
    return render(request, 'tasks/task-events.html', context)


@login_required(login_url='/')
@require_http_methods(['POST'])
def task_toggle_active(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.is_active = not(task.is_active)
    task.save()
    return render(request, 'main/partials/task-row.html', {'task':task})

@login_required(login_url='/')
@require_http_methods(['DELETE'])
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return HttpResponse("")
