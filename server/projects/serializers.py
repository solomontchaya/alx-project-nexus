from rest_framework import serializers
from .models import Project, ProjectCampaign
from teams.serializers import TeamSerializer
from campaigns.serializers import CampaignListSerializer
from categories.serializers import CategorySerializer

class ProjectCampaignInlineSerializer(serializers.ModelSerializer):
    campaign = CampaignListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    campaign_ref = serializers.UUIDField(write_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = ProjectCampaign
        fields = ['campaign', 'campaign_ref', 'category', 'category_id', 'joined_at']

    def validate(self, data):
        from campaigns.models import Campaign
        campaign_ref = data['campaign_ref']
        try:
            campaign = Campaign.objects.get(ref=campaign_ref)
        except Campaign.DoesNotExist:
            raise serializers.ValidationError("Campaign not found.")

        if not campaign.is_open:
            raise serializers.ValidationError(f"Campaign '{campaign.name}' is not open for submissions.")

        category_id = data.get('category_id')
        if category_id:
            if not campaign.categories.filter(id=category_id).exists():
                raise serializers.ValidationError(
                    f"Category ID {category_id} is not part of campaign '{campaign.name}'"
                )
        else:
            # Optional: require category
            raise serializers.ValidationError("category_id is required.")

        data['campaign'] = campaign
        return data

class ProjectSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    campaigns = ProjectCampaignInlineSerializer(
        source='projectcampaign_set',
        many=True,
        read_only=True
    )
    join_campaigns = ProjectCampaignInlineSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text="List of campaigns to join with category"
    )

    class Meta:
        model = Project
        fields = [
            'ref', 'name', 'summary', 'description', 'image',
            'team', 'campaigns', 'join_campaigns',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['ref', 'team', 'created_at', 'updated_at']

    def create(self, validated_data):
        join_data = validated_data.pop('join_campaigns', [])
        team = self.context['request'].user.team_member.team

        project = Project.objects.create(team=team, **validated_data)

        # Create ProjectCampaign entries
        entries = []
        for item in join_data:
            entries.append(ProjectCampaign(
                project=project,
                campaign=item['campaign'],
                category_id=item.get('category_id')
            ))
        ProjectCampaign.objects.bulk_create(entries, ignore_conflicts=True)

        return project

    def update(self, validated_data):
        join_data = validated_data.pop('join_campaigns', None)
        project = super().update(validated_data)

        if join_data is not None:
            # Optional: allow adding more campaigns on update
            entries = []
            for item in join_data:
                entries.append(ProjectCampaign(
                    project=project,
                    campaign=item['campaign'],
                    category_id=item.get('category_id')
                ))
            ProjectCampaign.objects.bulk_create(entries, ignore_conflicts=True)

        return project