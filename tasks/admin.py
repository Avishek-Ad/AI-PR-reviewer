from django.contrib import admin
from .models import Task, PullRequestEvent

admin.site.register(Task)
admin.site.register(PullRequestEvent)