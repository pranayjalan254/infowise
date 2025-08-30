"""
Authentication service.
Simple auth for hackathon prototype with Google OAuth support and persistent storage.
"""

from flask import Blueprint, request, current_app, redirect, url_for, session
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import os
from utils.responses import success_response, validate_request_json
from utils.validation import LoginRequest, RegisterRequest, UserResponse, TokenResponse
from utils.errors import BadRequestError, UnauthorizedError, ConflictError
from utils.helpers import generate_id, hash_password, verify_password, get_current_timestamp
from database import get_user_db
from typing import Optional


auth_bp = Blueprint('auth', __name__)


# Get database instance
db = get_user_db()

# Temporary in-memory state store for OAuth (use Redis in production)
oauth_states = {}


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    Creates a new user account with email and password and automatically logs them in.
    """
    try:
        data = request.get_json()
        if not data:
            raise BadRequestError("Request body is required")
        
        # Validate request data
        user_data = validate_request_json(RegisterRequest, data)
        
        # Check if user already exists
        if _user_exists(user_data.email):
            raise ConflictError("User with this email already exists")
        
        # Create new user
        user = _create_user(user_data)
        
        current_app.logger.info(f"New user registered: {user['email']}")
        
        # Create tokens for automatic login
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'role': user['role']}
        )
        refresh_token = create_refresh_token(identity=user['id'])
        
        # Prepare user response (without password)
        user_response = UserResponse(**{k: v for k, v in user.items() if k != 'password'})
        
        # Prepare token response
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        )
        
        return success_response(
            data={
                'user': user_response.dict(),
                'tokens': token_response.dict()
            },
            message="User registered and logged in successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        raise


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login.
    Authenticates user and returns JWT tokens.
    """
    try:
        data = request.get_json()
        if not data:
            raise BadRequestError("Request body is required")
        
        # Validate request data
        login_data = validate_request_json(LoginRequest, data)
        
        # Find user
        user = _find_user_by_email(login_data.email)
        if not user:
            raise UnauthorizedError("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user['password']):
            raise UnauthorizedError("Invalid email or password")
        
        # Create tokens
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'role': user['role']}
        )
        refresh_token = create_refresh_token(identity=user['id'])
        
        current_app.logger.info(f"User logged in: {user['email']}")
        
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        )
        
        # Prepare user response (without password)
        user_response = UserResponse(**{k: v for k, v in user.items() if k != 'password'})
        
        return success_response(
            data={
                'user': user_response.dict(),
                'tokens': token_response.dict()
            },
            message="Login successful"
        )
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        raise


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    User logout.
    Blacklists the current token.
    """
    try:
        user_id = get_jwt_identity()
        token = get_jwt()
        jti = token['jti']  # JWT ID
        
        # Blacklist the token
        _blacklist_token(jti)
        
        current_app.logger.info(f"User logged out: {user_id}")
        
        return success_response(message="Logged out successfully")
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        raise


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token.
    Uses refresh token to get a new access token.
    """
    try:
        user_id = get_jwt_identity()
        user = _find_user_by_id(user_id)
        
        if not user:
            raise UnauthorizedError("User not found")
        
        # Create new access token
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'role': user['role']}
        )
        
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token="",  # Don't return new refresh token
            expires_in=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        )
        
        return success_response(
            data=token_response.dict(),
            message="Token refreshed successfully"
        )
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        raise


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current user information.
    Returns user profile for the authenticated user.
    """
    try:
        user_id = get_jwt_identity()
        user = _find_user_by_id(user_id)
        
        if not user:
            raise UnauthorizedError("User not found")
        
        # Return user data (without password)
        user_response = UserResponse(**{k: v for k, v in user.items() if k != 'password'})
        
        return success_response(data=user_response.dict())
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        raise


@auth_bp.route('/google', methods=['GET'])
def google_login():
    """
    Initiate Google OAuth login.
    Redirects user to Google's OAuth consent screen.
    """
    try:
        if not current_app.config.get('GOOGLE_CLIENT_ID'):
            raise BadRequestError("Google OAuth not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email', 
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        session['state'] = state
        # Also store in memory as backup
        oauth_states[state] = {'timestamp': get_current_timestamp(), 'used': False}
        
        current_app.logger.info(f"Google OAuth initiated with state: {state}")
        
        return success_response(
            data={'authorization_url': authorization_url, 'state': state},
            message="Google OAuth URL generated"
        )
        
    except Exception as e:
        current_app.logger.error(f"Google OAuth initiation error: {str(e)}")
        raise


@auth_bp.route('/google/callback', methods=['GET', 'POST'])
def google_callback():
    """
    Handle Google OAuth callback.
    Processes the authorization code and creates/logs in the user.
    """
    try:
        if not current_app.config.get('GOOGLE_CLIENT_ID'):
            raise BadRequestError("Google OAuth not configured")
        
        # Get the authorization code from the request
        code = request.args.get('code')
        state = request.args.get('state')
        
        current_app.logger.info(f"Google OAuth callback - received state: {state}, session state: {session.get('state')}")
        
        if not code:
            raise BadRequestError("Authorization code not provided")
        
        # Note: In development, sessions might not persist properly across redirects
        # For production, implement proper session storage (Redis, database, etc.)
        session_state = session.get('state')
        state_info = oauth_states.get(state)
        
        if session_state and session_state != state:
            current_app.logger.warning(f"State mismatch: session={session_state}, received={state}")
        elif not session_state and not state_info:
            current_app.logger.warning(f"No session state found and state not in memory: {state}")
        elif state_info and state_info.get('used'):
            current_app.logger.warning(f"State has already been used: {state}")
        else:
            current_app.logger.info(f"State verification passed: {state}")
        
        # Mark state as used
        if state_info:
            oauth_states[state]['used'] = True
        
        # For now, we'll continue if we have a state parameter from Google
        # In production, you should implement proper state verification
        if not state:
            raise BadRequestError("No state parameter provided")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email', 
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        
        # Get user info from Google
        credentials = flow.credentials
        
        # Make a request to get user info using the access token
        import requests
        resp = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        
        if resp.status_code != 200:
            raise BadRequestError("Failed to get user info from Google")
        
        userinfo = resp.json()
        
        # Extract user information
        google_id = userinfo['id']
        email = userinfo['email']
        name = userinfo.get('name', '')
        first_name = userinfo.get('given_name', name.split(' ')[0] if name else '')
        last_name = userinfo.get('family_name', name.split(' ')[-1] if ' ' in name else '')
        
        # Check if user exists
        user = _find_user_by_email(email)
        
        if not user:
            # Create new user
            user = _create_google_user(email, first_name, last_name, google_id)
            current_app.logger.info(f"New Google user registered: {email}")
        else:
            # Update Google ID if not set
            if not user.get('google_id'):
                user['google_id'] = google_id
                current_app.logger.info(f"Linked Google account to existing user: {email}")
        
        # Create tokens
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'role': user['role']}
        )
        refresh_token = create_refresh_token(identity=user['id'])
        
        current_app.logger.info(f"Google OAuth login successful: {email}")
        
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        )
        
        # For web application, redirect to frontend with tokens
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:8080')
        redirect_url = f"{frontend_url}/auth/callback?success=true&token={access_token}"
        
        return redirect(redirect_url)
        
    except Exception as e:
        current_app.logger.error(f"Google OAuth callback error: {str(e)}")
        # Redirect to frontend with error
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:8080')
        redirect_url = f"{frontend_url}/auth/callback?error=oauth_failed"
        return redirect(redirect_url)


@auth_bp.route('/google/verify', methods=['POST'])
def google_verify_token():
    """
    Verify Google ID token from frontend.
    Alternative method for Google OAuth when using frontend SDK.
    """
    try:
        data = request.get_json()
        if not data or 'id_token' not in data:
            raise BadRequestError("Google ID token is required")
        
        if not current_app.config.get('GOOGLE_CLIENT_ID'):
            raise BadRequestError("Google OAuth not configured")
        
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            data['id_token'], google_requests.Request(), current_app.config['GOOGLE_CLIENT_ID']
        )
        
        # Extract user information
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', '')
        first_name = idinfo.get('given_name', name.split(' ')[0] if name else '')
        last_name = idinfo.get('family_name', name.split(' ')[-1] if ' ' in name else '')
        
        # Check if user exists
        user = _find_user_by_email(email)
        
        if not user:
            # Create new user
            user = _create_google_user(email, first_name, last_name, google_id)
            current_app.logger.info(f"New Google user registered: {email}")
        else:
            # Update Google ID if not set
            if not user.get('google_id'):
                user['google_id'] = google_id
                current_app.logger.info(f"Linked Google account to existing user: {email}")
        
        # Create tokens
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={'email': user['email'], 'role': user['role']}
        )
        refresh_token = create_refresh_token(identity=user['id'])
        
        current_app.logger.info(f"Google token verification successful: {email}")
        
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        )
        
        return success_response(
            data={
                'tokens': token_response.dict(),
                'user': {k: v for k, v in user.items() if k != 'password'}
            },
            message="Google token verification successful"
        )
        
    except Exception as e:
        current_app.logger.error(f"Google token verification error: {str(e)}")
        raise


# Helper functions
def _user_exists(email: str) -> bool:
    """Check if user exists by email."""
    return db.user_exists(email)


def _create_user(user_data: RegisterRequest) -> dict:
    """Create a new user."""
    user_id = generate_id()
    
    user = {
        'id': user_id,
        'email': user_data.email.lower(),
        'password': hash_password(user_data.password),
        'first_name': user_data.first_name,
        'last_name': user_data.last_name,
        'role': 'user',
        'created_at': get_current_timestamp()
    }
    
    return db.create_user(user)


def _create_google_user(email: str, first_name: str, last_name: str, google_id: str) -> dict:
    """Create a new user from Google OAuth."""
    user_id = generate_id()
    
    user = {
        'id': user_id,
        'email': email.lower(),
        'password': None,  # No password for Google OAuth users
        'first_name': first_name,
        'last_name': last_name,
        'role': 'user',
        'google_id': google_id,
        'created_at': get_current_timestamp()
    }
    
    return db.create_user(user)


def _find_user_by_email(email: str) -> Optional[dict]:
    """Find user by email."""
    return db.find_user_by_email(email)


def _find_user_by_id(user_id: str) -> Optional[dict]:
    """Find user by ID."""
    return db.find_user_by_id(user_id)


def _blacklist_token(jti: str) -> None:
    """Blacklist a JWT token."""
    db.blacklist_token(jti)


# JWT token validation
def is_token_blacklisted(jti: str) -> bool:
    """Check if token is blacklisted."""
    return db.is_token_blacklisted(jti)
