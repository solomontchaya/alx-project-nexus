import uuid
from django.core.exceptions import ValidationError
from django.db import models
from users.models import User
from projects.models import Project, ProjectCampaign

class Vote(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    project_campaign = models.ForeignKey(ProjectCampaign, on_delete=models.CASCADE, null=True, related_name='votes')

    is_overall = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('voter', 'project_campaign')
        verbose_name = "Vote"
        verbose_name_plural = "Votes"

    def clean(self):
        # Overall vote: only one per user
        if self.is_overall:
            if Vote.objects.filter(voter=self.voter, is_overall=True).exclude(pk=self.pk).exists():
                raise ValidationError("You have already cast an overall vote.")

        # Category vote: one per category
        else:
            if not self.project_campaign:
                raise ValidationError("Project campaign is required for category vote.")
            if not self.project_campaign.category:
                raise ValidationError("Project campaign must belong to a category for a category vote.")
            if Vote.objects.filter(
                voter=self.voter,
                project_campaign__category=self.project_campaign.category,
                is_overall=False
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    f"You have already voted in the '{self.project_campaign.category.name}' category."
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # Enforces clean() at model level
        super().save(*args, **kwargs)

    def __str__(self):
        kind = "Overall" if self.is_overall else "Category"
        project_name = self.project_campaign.project.name if self.project_campaign and self.project_campaign.project else "No Project"
        return f"{self.voter.email} → {kind}: {project_name}"