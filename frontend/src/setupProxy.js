const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      onError: (err, req, res) => {
        console.error('Proxy error:', err.message);
        res.writeHead(500, {
          'Content-Type': 'text/plain',
        });
        res.end('Proxy error: Could not connect to backend server.');
      },
    })
  );

  // Handle favicon requests specifically to avoid proxy errors
  app.get('/favicon.ico', (req, res) => {
    res.status(204).end();
  });
};