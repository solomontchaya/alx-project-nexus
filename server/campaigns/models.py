import uuid
from django.db import models
from teams.models import Team

# Create your models here.
class Campaign(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    organizer = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=255)
    flyer = models.ImageField(upload_to='uploads/flyers/')
    summary = models.CharField(max_length=500)
    description = models.TextField()
    
    date_from = models.DateField()
    date_to = models.DateField()

    is_active = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Campaigns"
        ordering = ['-created_at']

    def __str__(self):
        return self.name