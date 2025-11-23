from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Campaign
from .serializers import CampaignSerializer

@extend_schema_view(
    list=extend_schema(tags=['Campaigns']),
    retrieve=extend_schema(tags=['Campaigns']),
    create=extend_schema(tags=['Campaigns']),
)
class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'ref'

    def get_queryset(self):
        return Campaign.objects.select_related('organizer').all()