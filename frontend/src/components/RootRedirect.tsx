import React from 'react';
import { Navigate } from 'react-router-dom';
import { AuthCallback } from './AuthCallback';

/**
 * RootRedirect Component
 *
 * This component handles the root route ("/") and decides whether to:
 * 1. Process an Azure AD authentication callback (if code/state params exist)
 * 2. Redirect to the default route (/chat) if no auth params
 *
 * This prevents the router from interfering with MSAL's authentication flow.
 */
export const RootRedirect: React.FC = () => {
  // Check if we have authentication parameters in the URL
  const urlParams = new URLSearchParams(window.location.search);
  const urlHash = window.location.hash;

  const hasAuthCode = urlParams.has('code') || urlHash.includes('code=');
  const hasState = urlParams.has('state') || urlHash.includes('state=');
  const hasError = urlParams.has('error') || urlHash.includes('error=');

  // If we have authentication parameters, process them with AuthCallback
  if (hasAuthCode || hasState || hasError) {
    console.log('🔐 RootRedirect: Auth parameters detected, processing callback...');
    return <AuthCallback />;
  }

  // Otherwise, redirect to the chat page
  console.log('🏠 RootRedirect: No auth parameters, redirecting to /chat');
  return <Navigate to="/chat" replace />;
};