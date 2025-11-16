from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'  # Tell SimpleJWT to use email

    def validate(self, attrs):
        # Replace 'email' with 'username' internally
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    "No active account found with the given credentials",
                    code='authorization'
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    "Account is disabled.",
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                "Must include 'email' and 'password'.",
                code='authorization'
            )

        # This calls the parent to generate tokens
        data = super().validate(attrs)
        return data