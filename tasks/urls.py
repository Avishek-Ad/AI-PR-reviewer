from django.urls import path
from . import views

urlpatterns = [
    path('<path:repo_name>/events/', views.task_events, name="task-events"),
    path('create/', views.task_create, name="task-create"),
]
