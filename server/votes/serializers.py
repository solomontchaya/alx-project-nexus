# votes/serializers.py
from rest_framework import serializers
from .models import Vote
from projects.models import ProjectCampaign

class VoteCreateSerializer(serializers.ModelSerializer):
    project_ref = serializers.UUIDField(write_only=True)
    campaign_ref = serializers.UUIDField(write_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_overall = serializers.BooleanField(default=False)

    class Meta:
        model = Vote
        fields = ['project_ref', 'campaign_ref', 'category_id', 'is_overall']

    def validate(self, data):
        user = self.context['request'].user
        project_ref = data['project_ref']
        campaign_ref = data['campaign_ref']
        is_overall = data.get('is_overall', False)

        # Find ProjectCampaign entry
        try:
            pc = ProjectCampaign.objects.get(
                project__ref=project_ref,
                campaign__ref=campaign_ref
            )
        except ProjectCampaign.DoesNotExist:
            raise serializers.ValidationError("Project not participating in this campaign.")

        # Check campaign is open
        if not pc.campaign.is_open:
            raise serializers.ValidationError("This campaign is not open for voting.")

        # Category validation
        if not is_overall:
            if not data.get('category_id'):
                raise serializers.ValidationError("category_id is required for category vote.")
            if not pc.campaign.categories.filter(id=data['category_id']).exists():
                raise serializers.ValidationError("This category is not part of the campaign.")

        # Check already voted
        exists = Vote.objects.filter(
            voter=user,
            project_campaign=pc,
            is_overall=is_overall,
            category_id=data.get('category_id')
        ).exists()

        if exists:
            raise serializers.ValidationError(
                "You have already voted in this category for this project in this campaign."
            )

        data['project_campaign'] = pc
        return data

    def create(self, validated_data):
        validated_data.pop('project_ref')
        validated_data.pop('campaign_ref')
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id

        return Vote.objects.create(
            voter=self.context['request'].user,
            **validated_data
        )


class VoteSerializer(serializers.ModelSerializer):
    project = serializers.CharField(source='project_campaign.project.name', read_only=True)
    campaign = serializers.CharField(source='project_campaign.campaign.name', read_only=True)
    category = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    voter_email = serializers.CharField(source='voter.email', read_only=True)

    class Meta:
        model = Vote
        fields = [
            'id', 'project', 'campaign', 'category',
            'is_overall', 'voter_email', 'created_at'
        ]