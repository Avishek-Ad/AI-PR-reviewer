from django.urls import path
from . import views

urlpatterns = [
    path('<path:repo_name>/events/', views.task_events, name="task-events"),
    path('create/', views.task_create, name="task-create"),
    path('toggle-active/<uuid:task_id>/', views.task_toggle_active, name="task-toggle-active"),
    path('delete/<uuid:task_id>', views.task_delete, name="task-delete"),
]
