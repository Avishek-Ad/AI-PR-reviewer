from django.urls import path
from . import views

urlpatterns = [
    path('<str:repo_name>/events/', views.task_events, name="task-events"),
]
