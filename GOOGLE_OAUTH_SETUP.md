# Google OAuth Setup Instructions

To enable Google OAuth authentication, you need to set up a Google Cloud Project and configure OAuth credentials.

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API or People API

## Step 2: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (for testing)
3. Fill in the required information:
   - Application name: "Data Guardians"
   - User support email: your email
   - Developer contact information: your email
4. Add scopes: `openid`, `email`, `profile`
5. Add test users (the emails that can test the app)

## Step 3: Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Add authorized redirect URIs:
   - `http://localhost:5001/api/v1/auth/google/callback`
   - `http://localhost:8080` (for frontend)
5. Copy the Client ID and Client Secret

## Step 4: Update Environment Variables

Update your `.env` file with the OAuth credentials:

```bash
# Google OAuth Settings
GOOGLE_CLIENT_ID=your-actual-google-client-id
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5001/api/v1/auth/google/callback
```

## Available Google OAuth Endpoints

### 1. Server-side OAuth Flow

- **Initiate OAuth**: `GET /api/v1/auth/google`
- **OAuth Callback**: `GET /api/v1/auth/google/callback`

### 2. Frontend SDK Verification

- **Verify ID Token**: `POST /api/v1/auth/google/verify`
  ```json
  {
    "id_token": "google-id-token-from-frontend-sdk"
  }
  ```

## Frontend Integration Options

### Option 1: Use the server-side flow

1. Redirect user to `/api/v1/auth/google`
2. Handle the callback with tokens

### Option 2: Use Google SDK in frontend

1. Include Google SDK in your frontend
2. Get ID token from Google
3. Send ID token to `/api/v1/auth/google/verify`

## Testing

Once configured, you can test Google OAuth by:

1. Starting the API server: `PORT=5001 python app.py`
2. Visiting: `http://localhost:5001/api/v1/auth/google`
3. Following the OAuth flow

The Google OAuth will create user accounts automatically and return the same JWT tokens as regular login.
