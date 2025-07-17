import React from 'react';
import { User as UserIcon } from 'lucide-react';

interface UserAvatarProps {
  user: {
    name?: string;
    email?: string;
    profile_picture?: string;
  };
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const UserAvatar: React.FC<UserAvatarProps> = ({ 
  user, 
  size = 'md', 
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'h-6 w-6 text-xs',
    md: 'h-8 w-8 text-sm',
    lg: 'h-12 w-12 text-base'
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-6 w-6'
  };

  // Get user initials as fallback
  const getInitials = () => {
    if (user.name) {
      return user.name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    if (user.email) {
      return user.email[0].toUpperCase();
    }
    return 'U';
  };

  // Build full URL for profile picture
  const getProfilePictureUrl = () => {
    if (!user.profile_picture) return null;
    
    // If it's already a full URL, return as is
    if (user.profile_picture.startsWith('http')) {
      return user.profile_picture;
    }
    
    // Otherwise, construct URL with backend base
    let backendUrl;
    if (process.env.REACT_APP_API_URL) {
      // Remove /api suffix if present
      backendUrl = process.env.REACT_APP_API_URL.replace('/api', '');
    } else {
      // Default to localhost for development
      backendUrl = 'http://localhost:8000';
    }
    
    return `${backendUrl}${user.profile_picture}`;
  };

  const profilePictureUrl = getProfilePictureUrl();

  return (
    <div 
      className={`${sizeClasses[size]} rounded-full flex items-center justify-center overflow-hidden ${className}`}
    >
      {profilePictureUrl ? (
        <img
          src={profilePictureUrl}
          alt={user.name || user.email || 'User avatar'}
          className="h-full w-full object-cover"
          onError={(e) => {
            // Fallback to initials if image fails to load
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const parent = target.parentElement;
            if (parent) {
              parent.innerHTML = `
                <div class="h-full w-full bg-gray-500 dark:bg-gray-600 text-white flex items-center justify-center font-medium">
                  ${getInitials()}
                </div>
              `;
            }
          }}
        />
      ) : (
        <div className="h-full w-full bg-gray-500 dark:bg-gray-600 text-white flex items-center justify-center">
          {user.name || user.email ? (
            <span className="font-medium">{getInitials()}</span>
          ) : (
            <UserIcon className={iconSizes[size]} />
          )}
        </div>
      )}
    </div>
  );
};