/**
 * Application configuration
 */

// Function to determine the API base URL
export const getApiBaseUrl = (): string => {
  // If we're on localhost, always use localhost backend
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  // If REACT_APP_API_URL is defined, use it (for tunnel/production)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  // Default to relative URL for production
  return '';
};

// Export API base URL
export const API_BASE_URL = getApiBaseUrl();