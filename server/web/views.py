import json
import logging
import requests
from datetime import date
from django.utils import timezone

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count, Q, F, Sum
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model, authenticate, login, logout


from votes.models import Vote
from teams.forms import Team, TeamForm
from campaigns.models import Campaign
from categories.models import Category
from projects.models import Project, ProjectCampaign

# Create your views here.
API_URL = settings.BACKEND_URL
logger = logging.getLogger(__name__)

class APIClient:
    """Helper class to handle API requests with token refresh"""
    
    def __init__(self, request):
        self.request = request
        self.base_url = API_URL
    
    def refresh_token(self):
        """Refresh the access token using refresh token"""
        refresh_token = self.request.session.get('refresh_token')
        if not refresh_token:
            logger.error("No refresh token available")
            return False
            
        try:
            response = requests.post(
                f'{self.base_url}auth/token/refresh/',
                json={'refresh': refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.request.session['access_token'] = data.get('access')
                # Some APIs return a new refresh token, update if provided
                if 'refresh' in data:
                    self.request.session['refresh_token'] = data.get('refresh')
                self.request.session.modified = True
                logger.info("Token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            return False
    
    def make_authenticated_request(self, url, method='GET', params=None, data=None):
        """Make API request with automatic token refresh"""
        access_token = self.request.session.get('access_token')
        
        # If no access token, try unauthenticated request
        if not access_token:
            logger.warning("No access token, making unauthenticated request")
            return self.make_request(url, method, params, data)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.request(method, url, json=data, headers=headers, timeout=30)
            
            # If token is expired, try to refresh and retry
            if response.status_code == 401:
                token_error = response.json()
                if 'code' in token_error and token_error['code'] == 'token_not_valid':
                    logger.info("Access token expired, attempting refresh...")
                    if self.refresh_token():
                        # Retry with new token
                        new_access_token = self.request.session.get('access_token')
                        headers['Authorization'] = f'Bearer {new_access_token}'
                        if method.upper() == 'GET':
                            response = requests.get(url, params=params, headers=headers, timeout=30)
                        elif method.upper() == 'POST':
                            response = requests.post(url, json=data, headers=headers, timeout=30)
                        else:
                            response = requests.request(method, url, json=data, headers=headers, timeout=30)
                        logger.info("Retried request with refreshed token")
                    else:
                        # Refresh failed, clear session
                        logger.error("Token refresh failed, clearing session")
                        self.clear_session()
                        return None
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def make_request(self, url, method='GET', params=None, data=None):
        """Make unauthenticated API request"""
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                return requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                return requests.post(url, json=data, headers=headers, timeout=30)
            else:
                return requests.request(method, url, json=data, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def clear_session(self):
        """Clear authentication session"""
        session_keys = ['access_token', 'refresh_token', 'user_data', 'is_authenticated']
        for key in session_keys:
            if key in self.request.session:
                del self.request.session[key]
        self.request.session.modified = True
        logger.info("Session cleared due to authentication failure")

class LoginView(TemplateView):
    template_name = 'web/auth/login.html'

    def get(self, request, *args, **kwargs):
        # If user is already authenticated, redirect to home
        if request.user.is_authenticated:
            return redirect('home')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Validate required fields
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, self.template_name, {'email': email})

        # Prepare login data for API
        login_data = {
            'email': email,
            'password': password
        }

        try:
            # Make API request to login user
            response = requests.post(
                f'{API_URL}auth/login/',
                json=login_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                # Login successful - get tokens and user data
                data = response.json()
                logger.info(f"Login successful for email: {email}")
                
                # Store tokens in session
                request.session['access_token'] = data.get('access')
                request.session['refresh_token'] = data.get('refresh')
                request.session['user_data'] = data.get('user', {})
                
                # Debug: Print API response to see what we're getting
                logger.info(f"API Response: {data}")
                
                # Try to create local user session
                user = self.sync_user_with_api(data.get('user', {}), email)
                if user:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name or user.email}!')
                    
                    # Redirect to next page if provided, otherwise home
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
                else:
                    # If user creation fails, still allow login but with limited functionality
                    logger.warning(f"Local user creation failed for {email}, but API login succeeded")
                    messages.warning(request, 'Login successful, but there was an issue with your local session.')
                    # You can still proceed without local user if needed
                    # return redirect('home')
                    # For now, let's show the error
                    messages.error(request, 'Failed to create local user session. Please contact support.')
                    
            else:
                # Login failed - get error message from API
                error_message = self.get_login_error(response)
                messages.error(request, error_message)
                logger.warning(f"Login failed for {email}: {error_message}")
                
        except requests.exceptions.Timeout:
            messages.error(request, 'Login timeout. Please try again.')
            logger.error(f"Login timeout for {email}")
        except requests.exceptions.ConnectionError:
            messages.error(request, 'Cannot connect to server. Please check your internet connection.')
            logger.error(f"Connection error for {email}")
        except requests.exceptions.RequestException as e:
            messages.error(request, f'Network error: {str(e)}')
            logger.error(f"Network error for {email}: {str(e)}")
        except Exception as e:
            messages.error(request, 'An unexpected error occurred. Please try again.')
            logger.error(f"Unexpected error for {email}: {str(e)}")

        # If login fails, return to login page with email preserved
        return render(request, self.template_name, {'email': email})

    def sync_user_with_api(self, user_data, fallback_email=None):
        """Create or update local user based on API response"""
        User = get_user_model()
        
        try:
            # Get email from user_data or use fallback
            email = user_data.get('email', fallback_email)
            if not email:
                logger.error("No email provided for user synchronization")
                return None

            logger.info(f"Syncing user with email: {email}")
            logger.info(f"User data from API: {user_data}")

            # Try to get existing user by email
            try:
                user = User.objects.get(email=email)
                logger.info(f"Found existing user: {user}")
                
                # Update user data from API
                user.first_name = user_data.get('first_name', user.first_name or '')
                user.last_name = user_data.get('last_name', user.last_name or '')
                
                # Ensure username is set (required field)
                if not user.username:
                    user.username = email
                
                user.save()
                logger.info(f"Updated user: {user}")
                
            except User.DoesNotExist:
                # Create new user
                logger.info("Creating new user")
                user = User.objects.create_user(
                    username=email,  # Use email as username
                    email=email,
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    password='api_authenticated_user_' + email  # Unique dummy password
                )
                logger.info(f"Created new user: {user}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error in sync_user_with_api: {str(e)}")
            logger.error(f"User data that caused error: {user_data}")
            return None

    def get_login_error(self, response):
        """Extract appropriate error message from API response"""
        try:
            error_data = response.json()
            logger.error(f"API error response: {error_data}")
            
            if isinstance(error_data, dict):
                # Handle common error formats
                if 'detail' in error_data:
                    return error_data['detail']
                if 'error' in error_data:
                    return error_data['error']
                if 'non_field_errors' in error_data:
                    if isinstance(error_data['non_field_errors'], list):
                        return error_data['non_field_errors'][0]
                    return str(error_data['non_field_errors'])
                
                # Check for field-specific errors
                for field in ['email', 'password']:
                    if field in error_data and isinstance(error_data[field], list):
                        return f"{field.title()}: {error_data[field][0]}"
                        
        except ValueError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Response text: {response.text}")
            
        # Default error messages based on status code
        if response.status_code == 401:
            return 'Invalid email or password.'
        elif response.status_code == 400:
            return 'Invalid login data provided.'
        elif response.status_code == 404:
            return 'Login service unavailable.'
        else:
            return f'Login failed (Error {response.status_code}). Please try again.'
        
class RegisterView(TemplateView):
    template_name = 'web/auth/register.html'

    def get(self, request, *args, **kwargs):
        # If user is already authenticated, redirect to home
        if request.user.is_authenticated:
            return redirect('home')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Prepare registration data for API
        registration_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password
        }

        try:
            # Make API request to register user
            response = requests.post(
                f'{API_URL}auth/register/',
                json=registration_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 201:
                # Registration successful
                messages.success(request, 'Registration successful! Please login to continue.')
                return redirect('signin')
            else:
                # Registration failed - get error message from API
                error_data = response.json()
                error_message = self.get_error_message(error_data)
                messages.error(request, error_message)
                
        except requests.exceptions.RequestException as e:
            # Handle connection errors
            messages.error(request, 'Connection error. Please try again later.')
        
        except Exception as e:
            # Handle other unexpected errors
            messages.error(request, 'An unexpected error occurred. Please try again.')

        # If registration fails, return to registration page with form data
        context = self.get_context_data()
        context['form_data'] = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
        }
        return render(request, self.template_name, context)

    def get_error_message(self, error_data):
        """Extract error message from API response"""
        if isinstance(error_data, dict):
            # Handle field-specific errors
            for field, errors in error_data.items():
                if isinstance(errors, list) and errors:
                    return f"{field.title()}: {errors[0]}"
            # Handle general error message
            if 'detail' in error_data:
                return error_data['detail']
            if 'error' in error_data:
                return error_data['error']
        return 'Registration failed. Please check your information.'

class LeaderboardView(TemplateView):
    template_name = 'web/leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filters
        campaign_ref = self.request.GET.get('campaign')
        category_id = self.request.GET.get('category')

        # Base queryset: one entry per project in a campaign
        entries = ProjectCampaign.objects.select_related(
            'project', 'project__team', 'campaign', 'category'
        ).annotate(
            project_name=F('project__name'),
            project_ref=F('project__ref'),
            project_summary=F('project__summary'),
            team_name=F('project__team__name'),
            campaign_name=F('campaign__name'),
            category_name=F('category__name'),
        )

        # Apply filters
        if campaign_ref:
            entries = entries.filter(campaign__ref=campaign_ref)
        if category_id:
            entries = entries.filter(category_id=category_id)

        # Count votes per entry
        entries = entries.annotate(
            vote_count=Count('votes'),
            category_votes=Count('votes', filter=Q(votes__is_overall=False)),
            overall_votes=Count('votes', filter=Q(votes__is_overall=True)),
        ).order_by('-vote_count', '-overall_votes', 'project__name')

        # Prepare leaderboard list
        leaderboard = []
        user = self.request.user

        for entry in entries:
            has_voted = False
            if user.is_authenticated:
                has_voted = Vote.objects.filter(
                    voter=user,
                    project_campaign=entry
                ).exists()

            leaderboard.append({
                'rank': None,  # Will be set in template-side
                'project_id': entry.project.id,
                'project_ref': entry.project_ref,
                'project_name': entry.project_name,
                'project_summary': entry.project_summary,
                'team_name': entry.team_name or "Solo Project",
                'campaign_name': entry.campaign_name,
                'category_name': entry.category_name,
                'vote_count': entry.vote_count,
                'category_votes': entry.category_votes,
                'overall_votes': entry.overall_votes,
                'has_voted': has_voted,
            })

        # Active campaigns for dropdown
        active_campaigns = Campaign.objects.filter(
            is_active=True,
            date_from__lte=timezone.now().date(),
            date_to__gte=timezone.now().date()
        ).values('ref', 'name')

        # Stats
        today = date.today()
        context.update({
            'leaderboard': leaderboard,
            'campaigns': active_campaigns,
            'selected_campaign': campaign_ref,
            'selected_category': category_id,

            # Stats
            'total_votes': Vote.objects.count(),
            'today_votes': Vote.objects.filter(created_at__date=today).count(),
            'active_voters': Vote.objects.values('voter').distinct().count(),

            # Top 3 for sidebar
            'top_voted_projects': [
                {
                    'project_name': item['project_name'],
                    'vote_count': item['vote_count'],
                    'vote_percentage': round((item['vote_count'] / max(1, Vote.objects.count())) * 100, 1)
                }
                for item in leaderboard[:3]
            ],

            # Categories with project count
            'categories': Category.objects.annotate(
                project_count=Count('projectcampaign')
            ).filter(project_count__gt=0).values('id', 'name', 'project_count'),
        })

        return context

class TeamView(TemplateView, LoginRequiredMixin):
    template_name = 'web/teams.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Annotate teams with correct counts using the real relations
        teams = Team.objects.annotate(
            # Count members → through TeamMember model (reverse name = 'memberships')
            member_count=Count('memberships', distinct=True),

            # Count projects → reverse relation 'projects'
            project_count=Count('projects', distinct=True),

            # Total votes received by all projects of this team
            total_votes=Count(
                'projects__projectcampaign__votes',  # project → projectcampaign → votes
                distinct=True
            ),
        )

        # Rank teams by total votes
        ranked_teams = teams.order_by('-total_votes', '-project_count')
        for rank, team in enumerate(ranked_teams, start=1):
            team.rank = rank

        # Add per-user flags (leader, can_join, etc.)
        user = self.request.user
        user_team = None
        if user.is_authenticated and hasattr(user, 'team_member'):
            user_team = user.team_member.team

        for team in teams:
            # Is current user the leader of this team?
            team.is_user_leader = (
                user.is_authenticated and
                user_team == team and
                getattr(user.team_member, 'is_leader', False)
            )

            # Can user join? (example: max 5 members)
            team.can_join = team.member_count < 5

        # Final ordering & context
        context.update({
            'teams': teams.order_by('-total_votes', '-project_count'),
            'total_members': teams.aggregate(total=Sum('member_count'))['total'] or 0,
        })

        return context
       
class CampaignView(TemplateView):
    template_name = 'web/campaigns.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # All campaigns with project count
        campaigns = Campaign.objects.annotate(
            project_count=Count('projectcampaign', distinct=True)
        ).prefetch_related('categories')

        # Add status and organizer info
        now = timezone.now().date()
        for c in campaigns:
            c.status = c.status  # from @property in model
            c.is_organizer = self.request.user.is_staff or (
                hasattr(self.request.user, 'team_member') and 
                Team.objects.filter(campaigns=c, members=self.request.user).exists()
            )

        context.update({
            'campaigns': campaigns,
            'total_campaigns': campaigns.count(),
        })

        return context
    
class ProjectView(TemplateView):
    template_name = 'web/projects.html'

class VoteView(TemplateView):
    template_name = 'web/votes.html'

class UserView(TemplateView):
    template_name = 'web/users.html'