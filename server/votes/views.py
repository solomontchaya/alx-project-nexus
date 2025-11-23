# votes/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Case, When, IntegerField
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Vote
from .serializers import VoteCreateSerializer, VoteSerializer


@extend_schema(tags=['Votes'])
class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.select_related(
        'voter', 'project_campaign__project', 'project_campaign__campaign', 'category'
    ).all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return VoteCreateSerializer if self.action == 'create' else VoteSerializer

    @extend_schema(
        summary="Cast a vote",
        request=VoteCreateSerializer,
        responses={201: VoteSerializer, 400: OpenApiResponse(description="Invalid vote")}
    )
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vote = serializer.save()
        return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="My votes")
    @action(detail=False, methods=['get'])
    def my_votes(self, request):
        votes = Vote.objects.filter(voter=request.user)
        serializer = VoteSerializer(votes, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Leaderboard (all campaigns)")
    @action(detail=False, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request):
        campaign_ref = request.query_params.get('campaign_ref')
        category_id = request.query_params.get('category_id')

        base_qs = Vote.objects.values(
            'project_campaign__project__ref',
            'project_campaign__project__name',
            'project_campaign__campaign__name'
        )

        if campaign_ref:
            base_qs = base_qs.filter(project_campaign__campaign__ref=campaign_ref)

        # Count votes
        leaderboard = base_qs.annotate(
            overall_votes=Count('id', filter=Q(is_overall=True)),
            category_votes=Count('id', filter=Q(is_overall=False)),
            total_votes=Count('id')
        ).annotate(
            rank=Case(
                When(category_id__isnull=False, then=Count('id', filter=Q(category_id=category_id))),
                default=Count('id'),
                output_field=IntegerField()
            )
        ).order_by('-rank')[:20]

        return Response(list(leaderboard))