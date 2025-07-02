// Debug script para testar autenticação no console do navegador
// Cole este código no console do navegador em http://localhost:3000

console.log('=== Testing Knight Agent Authentication ===');

// 1. Check Dev Mode
fetch('/api/auth/dev/check/')
  .then(res => res.json())
  .then(data => {
    console.log('Dev Mode Check:', data);
    
    // 2. Try Dev Login
    if (data.dev_mode) {
      console.log('Dev mode is enabled, attempting login...');
      
      return fetch('/api/auth/dev/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      });
    } else {
      console.error('Dev mode is NOT enabled!');
      return Promise.reject('Dev mode not enabled');
    }
  })
  .then(res => res.json())
  .then(data => {
    console.log('Login Response:', data);
    
    if (data.session_token) {
      console.log('✅ Login successful!');
      console.log('Session Token:', data.session_token);
      console.log('User:', data.user);
      
      // Save token
      localStorage.setItem('sessionToken', data.session_token);
      console.log('Token saved to localStorage');
      
      // Try to get profile
      return fetch('/api/auth/profile/', {
        headers: {
          'Authorization': `Bearer ${data.session_token}`
        }
      });
    }
  })
  .then(res => res?.json())
  .then(profile => {
    if (profile) {
      console.log('Profile fetch successful:', profile);
    }
  })
  .catch(err => {
    console.error('Error during authentication test:', err);
  });

// Check current localStorage
console.log('Current sessionToken in localStorage:', localStorage.getItem('sessionToken'));