from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count
from drf_spectacular.utils import extend_schema

from projects.models import ProjectCampaign
from campaigns.models import Campaign
from campaigns.serializers import CampaignSerializer

@extend_schema(tags=['Campaigns'])
class CampaignViewSet(viewsets.ModelViewSet):
    # 1. Optimization moved to class attribute matching ProjectViewSet style
    queryset = Campaign.objects.select_related('organizer')
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'ref'

    def get_queryset(self):
        qs = super().get_queryset()
        # Optional: Add filtering logic here similar to ProjectViewSet
        # Example: Filter by active campaigns
        is_active = self.request.query_params.get('is_active')
        if is_active:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        # Logic: Automatically set the current user as the organizer
        # You can add a check here (e.g. is_staff) if needed, similar to the "is_leader" check
        serializer.save(organizer=self.request.user)

    @extend_schema(summary="List all campaigns")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Create a new campaign")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Update campaign (Organizer only)")
    def update(self, request, *args, **kwargs):
        campaign = self.get_object()
        # Logic: Only the organizer can edit the campaign
        if campaign.organizer != request.user:
             return Response({"error": "Only the campaign organizer can edit this campaign."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Delete campaign (Organizer only)")
    def destroy(self, request, *args, **kwargs):
        campaign = self.get_object()
        # Logic: Only the organizer can delete the campaign
        if campaign.organizer != request.user:
            return Response({"error": "Only the campaign organizer can delete this campaign."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(summary="Get statistics for this campaign")
    @action(detail=True, methods=['get'])
    def stats(self, request, ref=None):
        campaign = self.get_object()
        
        # Example Stats: Count total projects associated with this campaign
        # This assumes a Reverse Relation from ProjectCampaign -> Campaign
        stats = {
            "total_projects": ProjectCampaign.objects.filter(campaign=campaign).count(),
            # You could also aggregate total votes across all projects in this campaign here
            "total_votes": campaign.project_campaigns.aggregate(total_votes=Count('votes'))['total_votes'] or 0
        }
        return Response(stats)