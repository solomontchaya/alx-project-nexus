import uuid
from django.db import models
from django.utils import timezone
from teams.models import Team

# Create your models here.
class Campaign(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    organizer = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='campaigns')
    categories = models.ManyToManyField('categories.Category', related_name='campaigns')
    name = models.CharField(max_length=255)
    flyer = models.ImageField(upload_to='flyers/', blank=True, null=True)
    summary = models.CharField(max_length=500)
    description = models.TextField()

    date_from = models.DateField()
    date_to = models.DateField()
    is_active = models.BooleanField(default=False, help_text="Publish campaign")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        """True if campaign is active AND within date range"""
        today = timezone.now().date()
        return self.is_active and self.date_from <= today <= self.date_to

    @property
    def status(self):
        if not self.is_active:
            return "Draft"
        today = timezone.now().date()
        if today < self.date_from:
            return "Scheduled"
        if today > self.date_to:
            return "Closed"
        return "Open"