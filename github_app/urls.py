from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^webhook-receiver/?$', views.github_webhook, name="github-webhook")
]
