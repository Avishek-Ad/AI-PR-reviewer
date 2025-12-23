from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'main/home.html')

@login_required(login_url='/')
def dashboard(request):
    repositories = ['kjsdf']
    context = {
        'repositories' : repositories
    }
    return render(request, 'main/dashboard/index.html', context)
