from django.db import models
from github_app.models import Repository
from django.contrib.auth.models import User
import uuid

class Task(models.Model):
    class InstallationStatus(models.TextChoices):
        PENDING = 'pending'
        INSTALLED = 'installed'
    
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, related_name='tasks', on_delete=models.CASCADE, null=True)
    repository_github_id = models.BigIntegerField()
    user = models.ForeignKey(User, related_name='tasks', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=InstallationStatus.choices, default=InstallationStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'repository'],
                name="user_and_repository_must_be_unique"
            )
        ]

    def __str__(self):
        return f"Task for {self.repository_github_id} by {self.user.username}"
    
class PullRequestEvent(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    pr_number = models.IntegerField()
    pr_url = models.URLField(max_length=200)
    task = models.ForeignKey(Task, related_name="pull_requests", on_delete=models.CASCADE)
    title = models.CharField(max_length=400)
    action = models.CharField(max_length=50)
    github_delivery_id = models.UUIDField(unique=True)
    installation_id = models.BigIntegerField()
    github_repo_id = models.BigIntegerField()
    author_name = models.CharField(max_length=100, default="")
    author_avatar_url = models.URLField(max_length=200, default="")
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pr_number', 'task', 'action', 'github_delivery_id'],
                name="Duplicate_PR_received"
            )
        ]
        ordering = ['-received_at']

    def __str__(self):
        return f"PR {self.task.repository.full_name} -> {self.pr_number}"