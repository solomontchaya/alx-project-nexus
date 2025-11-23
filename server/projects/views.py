from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Project
from .serializers import ProjectSerializer

@extend_schema(tags=['Projects'])
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('team', 'campaign', 'category').all()
    serializer_class = ProjectSerializer
    lookup_field = 'ref'  # Use UUID ref for URLs
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['campaign__id', 'category__id', 'team__id']
    search_fields = ['title', 'summary', 'description']
    ordering_fields = ['title', 'created_at', 'total_votes']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]  # Or AllowAny if public
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]  # Custom permission for team leader below
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Example: Filter by votes if query param
        min_votes = self.request.query_params.get('min_votes')
        if min_votes:
            queryset = queryset.filter(votes__count__gte=min_votes)
        return queryset

    @extend_schema(
        summary="List all projects",
        responses={200: ProjectSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new project (team leader only)",
        responses={
            201: ProjectSerializer,
            400: OpenApiResponse(description="Invalid data or team already has project")
        }
    )
    def create(self, request, *args, **kwargs):
        if not request.user.team_member.is_leader:  # Assuming TeamMember has 'is_leader' or 'role' == 'leader'
            return Response({"error": "Only team leaders can create projects."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update project (team leader only)"
    )
    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if request.user.team_member.team != project.team or not request.user.team_member.is_leader:
            return Response({"error": "Only the team leader can update this project."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete project (team leader or admin only)",
        responses={204: OpenApiResponse(description="Deleted")}
    )
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if request.user.is_staff or (request.user.team_member.team == project.team and request.user.team_member.is_leader):
            return super().destroy(request, *args, **kwargs)
        return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        methods=['GET'],
        summary="Get vote counts for a project"
    )
    @action(detail=True, methods=['get'])
    def votes(self, request, ref=None):
        project = self.get_object()
        return Response({
            'total_votes': project.total_votes,
            'overall_votes': project.overall_votes,
            'category_votes': project.category_votes
        })