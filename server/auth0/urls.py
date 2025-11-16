# auth/urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.utils import extend_schema_view, extend_schema
from .serializers import CustomTokenObtainPairSerializer
from .views import RegisterView, LogoutView, ForgotPasswordView, ResetPasswordView


# ------------------------------------------------------------------
# Wrap SimpleJWT views with @extend_schema_view to override tag
# ------------------------------------------------------------------
@extend_schema_view(
    post=extend_schema(tags=['Auth'], summary="Login - get JWT tokens")
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@extend_schema_view(
    post=extend_schema(tags=['Auth'], summary="Refresh JWT access token")
)
class RefreshView(TokenRefreshView):
    pass

@extend_schema_view(
    post=extend_schema(tags=['Auth'], summary="Verify JWT token")
)
class VerifyView(TokenVerifyView):
    pass

urlpatterns = [
    path("", LoginView.as_view(), name="token_obtain_pair"),
    path("login/", LoginView.as_view(), name="token_obtain_pair"),
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("refresh/", RefreshView.as_view(), name="token_refresh"),
    path("verify/", VerifyView.as_view(), name="token_verify"),
    path("logout/", LogoutView.as_view(), name="token_blacklist"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth_forgot_password"),
    path("reset-password/<str:token>/", ResetPasswordView.as_view(), name="auth_reset_password"),
]