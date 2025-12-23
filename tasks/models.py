from django.db import models
from github_app.models import Repository
from django.contrib.auth.models import User
import uuid

class Task(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='tasks', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'repository'],
                name="user_and_repository_must_be_unique"
            )
        ]

    def __str__(self):
        return f"Task for {self.repository.full_name} by {self.user.username}"
    
class PullRequestEvent(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    pr_number = models.IntegerField()
    pr_url = models.URLField(max_length=200)
    task = models.ForeignKey(Task, related_name="pull_requests", on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    github_delivery_id = models.UUIDField(unique=True)
    installation_id = models.BigIntegerField()
    github_repo_id = models.BigIntegerField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pr_number', 'task', 'action'],
                name="Duplicate_PR_received"
            )
        ]

    def __str__(self):
        return f"PR {self.task.repository.full_name} -> {self.pr_number}"