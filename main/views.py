from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tasks.models import Task, PullRequestEvent

def home(request):
    return render(request, 'main/home.html')

@login_required(login_url='/')
def dashboard(request):
    tasks = request.user.tasks.all()
    total_reviews = PullRequestEvent.objects.all().count()

    search = request.GET.get('search', '').strip()
    if search:
        tasks = tasks.filter(repository__full_name__icontains=search)

    if request.htmx:
        return render(request, 'main/partials/task-repo-table.html', {'tasks': tasks})
    context = {
        'tasks' : tasks,
        'total_reviews': total_reviews
    }
    return render(request, 'main/dashboard/index.html', context)
