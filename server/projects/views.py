from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema

from .models import Project, ProjectCampaign
from .serializers import ProjectSerializer


@extend_schema(tags=['Projects'])
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('team').prefetch_related(
        Prefetch('projectcampaign_set', queryset=ProjectCampaign.objects.select_related('campaign', 'category'))
    )
    serializer_class = ProjectSerializer
    lookup_field = 'ref'
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        campaign_ref = self.request.query_params.get('campaign_ref')
        if campaign_ref:
            qs = qs.filter(projectcampaign__campaign__ref=campaign_ref)
        return qs.distinct()

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'team_member') or not self.request.user.team_member.is_leader:
            raise PermissionDenied("Only team leaders can create projects.")
        serializer.save()

    @extend_schema(summary="List projects (optionally filter by campaign)")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Create project and join campaigns with categories")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Update project (team leader only)")
    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.team != request.user.team_member.team or not request.user.team_member.is_leader:
            return Response({"error": "Only your team's leader can edit this project."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Delete project (team leader only)")
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if project.team != request.user.team_member.team or not request.user.team_member.is_leader:
            return Response({"error": "Only your team's leader can delete this project."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(summary="Get vote statistics for this project")
    @action(detail=True, methods=['get'])
    def stats(self, request, ref=None):
        project = self.get_object()
        stats = project.votes.values('project_campaign__campaign__name', 'is_overall') \
            .annotate(count=Count('id')) \
            .order_by('-count')
        return Response(stats)