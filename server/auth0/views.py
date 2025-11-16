# auth/views.py
import uuid
from datetime import timedelta

from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from users.models import User
from users.serializers import UserSerializer


# ----------------------------------------------------------------------
# Helper: JWT response
# ----------------------------------------------------------------------
def _jwt_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserSerializer(user).data,
    }

@extend_schema(tags=['Auth'])
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        request={
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "password": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
        },
        responses={201: _jwt_response, 400: OpenApiResponse(description="Invalid data")},
    )
    def post(self, request):
        from users.serializers import UserRegisterSerializer
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(_jwt_response(user), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['Auth'])
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Request password reset link",
        request={"type": "object", "properties": {"email": {"type": "string"}}},
        responses={
            200: {"type": "object", "properties": {"message": {"type": "string"}}},
            404: OpenApiResponse(description="User not found"),
        },
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"message": "If the email exists, a reset link has been sent."},
                status=status.HTTP_200_OK,
            )

        # Generate token
        token = urlsafe_base64_encode(force_bytes(user.pk)) + "-" + str(uuid.uuid4())
        user.profile.reset_token = token
        user.profile.reset_token_expiry = timezone.now() + timedelta(hours=1)
        user.profile.save()

        # Send email
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}/"
        html_message = render_to_string("emails/password_reset.html", {
            "user": user,
            "reset_url": reset_url,
        })

        send_mail(
            subject="Password Reset Request",
            message="",
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "If the email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )

@extend_schema(tags=['Auth'])
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reset password with token",
        request={
            "type": "object",
            "properties": {
                "password": {"type": "string", "minLength": 8},
                "confirm_password": {"type": "string"},
            },
        },
        responses={
            200: {"type": "object", "properties": {"message": {"type": "string"}}},
            400: OpenApiResponse(description="Invalid/expired token or passwords don't match"),
        },
    )
    def post(self, request, token):
        password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uidb64, _ = token.split("-", 1)
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        profile = user.profile
        if not profile.reset_token or profile.reset_token != token:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        if profile.reset_token_expiry < timezone.now():
            return Response({"error": "Token has expired."}, status=status.HTTP_400_BAD_REQUEST)

        # Reset password
        user.set_password(password)
        user.save()

        # Clear token
        profile.reset_token = None
        profile.reset_token_expiry = None
        profile.save()

        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
    
@extend_schema(tags=['Auth'])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout – blacklist refresh token",
        request={"type": "object", "properties": {"refresh": {"type": "string"}}},
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)