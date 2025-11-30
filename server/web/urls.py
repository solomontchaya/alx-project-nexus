from django.urls import path
from web import views

urlpatterns = [
    path('', views.LeaderboardView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='signin'),
    path('register/', views.RegisterView.as_view(), name='signup'),

    path('users/', views.UserView.as_view(), name='users'),
    path('votes/', views.VoteView.as_view(), name='votes'),
    path('teams/', views.TeamView.as_view(), name='teams'),
    path('projects/', views.ProjectView.as_view(), name='projects'),
    path('campaigns/', views.CampaignView.as_view(), name='campaigns'),
]