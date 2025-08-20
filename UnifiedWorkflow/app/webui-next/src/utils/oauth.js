// OAuth utilities for Google services integration with PKCE security
import { SecureAuth, PKCEUtils, OAuthStateManager } from './secureAuth';

export const GOOGLE_SERVICES = {
  CALENDAR: 'calendar',
  DRIVE: 'drive', 
  GMAIL: 'gmail'
};

export const OAUTH_ENDPOINTS = {
  STATUS: '/api/v1/oauth/google/status',
  CONNECT_CALENDAR: '/api/v1/oauth/google/connect/calendar',
  CONNECT_DRIVE: '/api/v1/oauth/google/connect/drive',
  CONNECT_GMAIL: '/api/v1/oauth/google/connect/gmail',
  CALLBACK: '/api/v1/oauth/google/callback'
};

/**
 * Get OAuth status for all Google services using secure authentication
 * @returns {Promise<Object>} OAuth status response
 */
export const getOAuthStatus = async () => {
  try {
    const response = await SecureAuth.makeSecureRequest(OAUTH_ENDPOINTS.STATUS);
    
    if (!response.ok) {
      throw new Error(`OAuth status request failed: ${response.status}`);
    }
    
    const result = await response.json();

    // Add optional token revocation endpoint support
    if (result.revoke_token_url) {
      try {
        await SecureAuth.makeSecureRequest(result.revoke_token_url, { method: 'POST' });
      } catch (revokeError) {
        console.warn('Failed to revoke previous token:', revokeError);
      }
    }

    return result;
  } catch (error) {
    console.error('Failed to get OAuth status:', error);
    throw error;
  }
};

/**
 * Initiate Google OAuth connection for a specific service with PKCE security
 * @param {string} service - Service type (calendar, drive, gmail)
 * @returns {Promise<string>} OAuth authorization URL
 */
/**
 * Initiate OAuth connection with enhanced state management
 * @param {string} service - Service type (calendar, drive, gmail)
 * @returns {Promise<string>} OAuth authorization URL
 */
export const initiateOAuthConnection = async (service, scopeOptions = {}) => {
  const defaultScopes = {
    calendar: {
      readOnly: false,
      createEvents: false,
      deleteEvents: false
    },
    drive: {
      readOnly: false,
      writeFiles: false,
      shareFiles: false
    },
    gmail: {
      readOnly: false,
      sendEmails: false,
      manageDrafts: false
    }
  };
  let endpoint;
  
  switch (service) {
    case GOOGLE_SERVICES.CALENDAR:
      endpoint = OAUTH_ENDPOINTS.CONNECT_CALENDAR;
      break;
    case GOOGLE_SERVICES.DRIVE:
      endpoint = OAUTH_ENDPOINTS.CONNECT_DRIVE;
      break;
    case GOOGLE_SERVICES.GMAIL:
      endpoint = OAUTH_ENDPOINTS.CONNECT_GMAIL;
      break;
    default:
      throw new Error(`Unsupported service: ${service}`);
  }
  
  try {
    // Generate state token to prevent CSRF
    const stateToken = OAuthStateManager.generateStateToken(service);
    
    // Generate PKCE parameters for enhanced security
    const { codeVerifier, codeChallenge, codeChallengeMethod } = PKCEUtils.generatePKCE();
    
    // Store code verifier securely
    PKCEUtils.storePKCEVerifier(codeVerifier);
    
    const finalScopes = { ...defaultScopes[service], ...scopeOptions };
    
    const response = await SecureAuth.makeSecureRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        code_challenge: codeChallenge,
        code_challenge_method: codeChallengeMethod,
        state: stateToken,
        requested_scopes: Object.entries(finalScopes)
          .filter(([key, value]) => value)
          .map(([key]) => key)
      })
    });
    
    if (!response.ok) {
      throw new Error(`OAuth connection request failed: ${response.status}`);
    }
    
    const data = await response.json();
    
    // If the response contains an authorization URL, redirect to it
    if (data.authorization_url) {
      window.location.href = data.authorization_url;
      return data.authorization_url;
    }
    
    return data;
  } catch (error) {
    console.error(`Failed to initiate OAuth for ${service}:`, error);
    throw error;
  }
};

/**
 * Handle OAuth callback with PKCE verification (called when user returns from Google)
 * @param {URLSearchParams} urlParams - URL parameters from callback
 * @returns {Promise<Object>} Callback processing result
 */
export const handleOAuthCallback = async (urlParams) => {
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  const error = urlParams.get('error');
  const service = Object.values(GOOGLE_SERVICES).find(s => state && state.includes(s));
  
  if (error) {
    // Detailed error handling for OAuth failures
    const errorDescriptions = {
      'access_denied': 'User denied authorization',
      'invalid_request': 'Invalid authorization request',
      'unauthorized_client': 'Client not authorized',
      'unsupported_response_type': 'Unsupported response type',
      'invalid_grant': 'Authorization code expired or already used',
      'unauthorized_client': 'Application is not authorized to access the service'
    };

    // Enhanced logging for tracking OAuth errors
    console.error(`OAuth Callback Error: ${error}`);
    
    throw new Error(`OAuth Callback Error: ${errorDescriptions[error] || error}`);
  }
  
  if (!code) {
    throw new Error('OAuth callback missing authorization code');
  }
  
  if (!service) {
    throw new Error('Unable to determine OAuth service from state');
  }
  
  try {
    // Validate state token to prevent CSRF
    if (!OAuthStateManager.validateStateToken(state, service)) {
      throw new Error('Invalid OAuth state - potential CSRF attack');
    }
    
    // Retrieve PKCE code verifier
    const codeVerifier = PKCEUtils.retrievePKCEVerifier();
    if (!codeVerifier) {
      throw new Error('PKCE code verifier not found - potential security issue');
    }
    
    const response = await SecureAuth.makeSecureRequest(OAUTH_ENDPOINTS.CALLBACK, {
      method: 'POST',
      body: JSON.stringify({
        code,
        state,
        service,
        code_verifier: codeVerifier
      })
    });
    
    if (!response.ok) {
      throw new Error(`OAuth callback processing failed: ${response.status}`);
    }
    
    const result = await response.json();

    // Add optional token revocation endpoint support
    if (result.revoke_token_url) {
      try {
        await SecureAuth.makeSecureRequest(result.revoke_token_url, { method: 'POST' });
      } catch (revokeError) {
        console.warn('Failed to revoke previous token:', revokeError);
      }
    }

    return result;
  } catch (error) {
    console.error('Failed to process OAuth callback:', error);
    throw error;
  }
};

/**
 * Get service display information
 * @param {string} service - Service type
 * @returns {Object} Service display information
 */
export const getServiceInfo = (service) => {
  const serviceInfo = {
    [GOOGLE_SERVICES.CALENDAR]: {
      name: 'Google Calendar',
      description: 'Sync your calendar events and meetings',
      icon: 'calendar',
      color: 'bg-blue-600'
    },
    [GOOGLE_SERVICES.DRIVE]: {
      name: 'Google Drive',
      description: 'Access and manage your Google Drive files',
      icon: 'folder',
      color: 'bg-green-600'
    },
    [GOOGLE_SERVICES.GMAIL]: {
      name: 'Gmail',
      description: 'Read and manage your Gmail messages',
      icon: 'mail',
      color: 'bg-red-600'
    }
  };
  
  return serviceInfo[service] || {
    name: 'Unknown Service',
    description: 'Unknown Google service',
    icon: 'help-circle',
    color: 'bg-gray-600'
  };
};