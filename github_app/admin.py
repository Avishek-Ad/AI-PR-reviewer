from django.contrib import admin
from .models import Repository, GithubAppInstallation

admin.site.register(GithubAppInstallation)
admin.site.register(Repository)