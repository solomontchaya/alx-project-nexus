from django.urls import path
from web import views

urlpatterns = [
    path('', views.LeaderboardView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='signin'),
    path('register/', views.RegisterView.as_view(), name='signup'),
]