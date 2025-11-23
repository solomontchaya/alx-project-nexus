from rest_framework import serializers
from .models import Campaign
from teams.serializers import TeamSerializer

class CampaignSerializer(serializers.ModelSerializer):
    organizer = TeamSerializer(read_only=True)
    organizer_ref = serializers.UUIDField(write_only=True)  # to create
    flyer = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Campaign
        fields = [
            'ref', 'name', 'summary', 'description',
            'flyer', 'organizer', 'organizer_ref',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['ref', 'created_at', 'updated_at']

    def create(self, validated_data):
        organizer_ref = validated_data.pop('organizer_ref')
        team = validated_data['request'].user.team_member.team
        if team.ref != organizer_ref:
            raise serializers.ValidationError("You can only create campaigns for your own team.")
        validated_data['organizer'] = team
        return super().create(validated_data)
    
class CampaignListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Campaign
        fields = ['ref', 'name', 'flyer', 'summary', 'date_from', 'date_to',
                  'is_active', 'status', 'is_open', 'created_at']

class CampaignDetailSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField()
    status = serializers.CharField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = '__all__'

    def get_project_count(self, obj):
        return obj.participating_projects.count()