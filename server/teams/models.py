import uuid
from django.db import models
from users.models import User

# Create your models here.
class Team(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Teams"
        ordering = ['name']

    @property
    def member_count(self):
        return self.memberships.count()

    @property
    def project_count(self):
        return self.projects.count()
    
    @property
    def leader(self):
        try:
            return self.memberships.filter(role='admin').first().user
        except:
            return None
    
    def __str__(self):
        return self.name
    
class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teammemberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'user')
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"

    def __str__(self):
        return f"{self.user.email} - {self.team.name} ({self.role})"

    