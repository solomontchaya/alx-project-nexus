import logging
import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model, authenticate, login, logout

# Create your views here.
API_URL = settings.BACKEND_URL
logger = logging.getLogger(__name__)

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

    def get(self, request, *args, **kwargs):
        campaign_id = request.GET.get('campaign')
        category_id = request.GET.get('category')
        
        context = self.get_context_data()
        
        try:
            # Fetch leaderboard data from API
            leaderboard_data = self.fetch_leaderboard(campaign_id, category_id)
            context['leaderboard'] = leaderboard_data
            
            # Fetch campaigns for filter dropdown
            campaigns = self.fetch_campaigns()
            context['campaigns'] = campaigns
            
            # Fetch categories for filter dropdown
            categories = self.fetch_categories()
            context['categories'] = categories
            
            # Store current filters
            context['selected_campaign'] = campaign_id
            context['selected_category'] = category_id
            
            # Calculate statistics
            if leaderboard_data:
                context['total_projects'] = len(leaderboard_data)
                context['total_votes'] = sum(entry.get('vote_count', 0) for entry in leaderboard_data)
                context['top_project'] = leaderboard_data[0] if leaderboard_data else None
                
        except Exception as e:
            logger.error(f"Error loading leaderboard: {e}")
            messages.error(request, 'Failed to load leaderboard data. Please try again.')
            context['leaderboard'] = []
            context['campaigns'] = []
            context['categories'] = []
        
        return render(request, self.template_name, context)

    def fetch_leaderboard(self, campaign_id=None, category_id=None):
        """Fetch leaderboard data from API"""
        params = {}
        if campaign_id:
            params['campaign'] = campaign_id
        if category_id:
            params['category'] = category_id
            
        # Get access token from session for authenticated requests
        headers = {}
        access_token = self.request.session.get('access_token')
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        try:
            response = requests.get(
                f'{API_URL}votes/leaderboard/',
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching leaderboard: {e}")
            return []

    def fetch_campaigns(self):
        """Fetch available campaigns from API"""
        headers = {}
        access_token = self.request.session.get('access_token')
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
            
        try:
            response = requests.get(
                f'{API_URL}campaigns/',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API returned status {response.status_code} for campaigns: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching campaigns: {e}")
            return []

    def fetch_categories(self):
        """Fetch available categories from API"""
        headers = {}
        access_token = self.request.session.get('access_token')
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
            
        try:
            response = requests.get(
                f'{API_URL}categories/',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API returned status {response.status_code} for categories: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching categories: {e}")
            return []

    
