# VOID storefront

React/Vite storefront for the VOID Django API.

## Local frontend setup

1. Install Node.js 20 or newer.
2. Copy .env.example to .env.local and set the four API URLs.
3. Run npm ci, then npm run dev.
4. Run npm run lint and npm run build before release.

The frontend is a static site. Configure the host to serve the dist/ directory and rewrite client-side routes to index.html. VITE_* values are public build-time URLs; never put secrets in them.

## Production deployment

1. Set the four VITE_*_API_URL values to HTTPS API endpoints before building.
2. Run npm ci, npm run lint, and npm run build.
3. Publish dist/ to a static host with SPA route fallback.
4. Configure API host, CORS, and CSRF origins as documented in ../void-backend/README.md.
5. Verify registration/email verification, login/refresh/logout, catalog, cart, checkout, payment verification, and admin flows before opening traffic.

The old JSON Server mock API and its sample customer/order data have been retired.
