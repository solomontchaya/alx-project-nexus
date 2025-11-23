# campaigns/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet

router = DefaultRouter()
router.register(r'projects', CampaignViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]