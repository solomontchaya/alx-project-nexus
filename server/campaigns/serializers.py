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