from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


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
                'timestamp': timezone.now(),
                'status': 'completed', # or 'processing'
                'github_url': 'https://github.com/Avishek-Ad/file-share/pull/42'
            },
        ]
    }
    return render(request, 'tasks/task-events.html', context)