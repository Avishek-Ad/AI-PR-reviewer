from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from github_app.models import Repository
from tasks.models import Task

def home(request):
    return render(request, 'main/home.html')

@login_required(login_url='/')
def dashboard(request):
    tasks = Task.objects.all()
    context = {
        'tasks' : tasks
    }
    return render(request, 'main/dashboard/index.html', context)
