from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from github_app.models import Repository
from tasks.models import Task, PullRequestEvent

def home(request):
    return render(request, 'main/home.html')

@login_required(login_url='/')
def dashboard(request):
    tasks = Task.objects.all()
    total_reviews = PullRequestEvent.objects.all().count()
    context = {
        'tasks' : tasks,
        'total_reviews': total_reviews
    }
    return render(request, 'main/dashboard/index.html', context)
