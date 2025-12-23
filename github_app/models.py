from django.db import models
from django.contrib.auth.models import User
import uuid

class GithubAppInstallation(models.Model):
    class AccountTypeChoice(models.TextChoices):
        USER = 'user'
        ORG = 'org'

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    installation_id = models.BigIntegerField(unique=True)
    account_id = models.BigIntegerField()
    user = models.ForeignKey(User, related_name='installed_apps',on_delete=models.CASCADE)
    installed_date = models.DateField(auto_now_add=True)
    account_type = models.CharField(max_length=5, choices=AccountTypeChoice.choices, default=AccountTypeChoice.USER)

    def __str__(self):
        return f"Installation {self.installation_id} ({self.user.username})"


class Repository(models.Model):
    class OwnerTypeChoice(models.TextChoices):
        USER = 'user'
        ORG = 'org'
    
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    github_repo_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=200)
    github_app_installation = models.ForeignKey(GithubAppInstallation, related_name="repositories", on_delete=models.CASCADE)
    repo_url = models.URLField(max_length=200)
    is_private = models.BooleanField(default=False)
    owner_type = models.CharField(max_length=5, choices=OwnerTypeChoice.choices, default=OwnerTypeChoice.USER)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['github_repo_id', 'github_app_installation'],
                name='unique_repo_per_installation'
            )
        ]

    def __str__(self):
        return f"{self.full_name}"