import uuid
from django.db import models
from users.models import User
from teams.models import Team
from campaigns.models import Campaign
from categories.models import Category

# Create your models here.
class Project(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, related_name='projects')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='projects')
    name = models.CharField(max_length=255)
    summary = models.TextField(max_length=300)
    description = models.TextField()
    image = models.ImageField(upload_to='uploads/project-images/', blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Projects"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def total_votes(self):
        return self.votes.count()

    @property
    def overall_votes(self):
        return self.votes.filter(is_overall=True).count()

    @property
    def category_votes(self):
        return self.votes.filter(is_overall=False).count()