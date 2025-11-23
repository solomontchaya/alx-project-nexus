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
    name = models.CharField(max_length=255)
    summary = models.TextField(max_length=300)
    description = models.TextField()
    image = models.ImageField(upload_to='uploads/project-images/', blank=True, null=True)

    campaigns = models.ManyToManyField(
        Campaign,
        through='ProjectCampaign',
        related_name='participating_projects'
    )

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
    
class ProjectCampaign(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Category for this campaign"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'campaign')
        verbose_name_plural = "Project Campaign Entries"

    def __str__(self):
        return f"{self.project} → {self.campaign}"
    
    def clean(self):
        if self.category and self.category not in self.campaign.categories.all():
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Category '{self.category}' is not part of campaign '{self.campaign}'"
            )