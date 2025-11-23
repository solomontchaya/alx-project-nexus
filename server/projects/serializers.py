from rest_framework import serializers
from .models import Project
from teams.serializers import TeamSerializer
from campaigns.serializers import Campaign, CampaignSerializer
from categories.serializers import Category, CategorySerializer

class ProjectSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    campaign = CampaignSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    campaign_ref = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Project
        fields = [
            'ref', 'name', 'summary', 'description', 'image',
            'team', 'campaign', 'category',
            'campaign_ref', 'category_id',
            'total_votes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['ref', 'total_votes', 'created_at', 'updated_at']

    def create(self, validated_data):
        campaign_ref = validated_data.pop('campaign_ref', None)
        category_id = validated_data.pop('category_id', None)

        project = Project.objects.create(
            team=validated_data['request'].user.team_member.team,
            campaign_id=Campaign.objects.get(ref=campaign_ref).id if campaign_ref else None,
            category_id=category_id,
            **validated_data
        )
        return project