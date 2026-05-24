# Goala Frontend - Admin Panel

React-based admin panel for managing Goala RAG system parameters and viewing chat history.

## Features

### 1. Settings Management
- **LLM Configuration**: Change provider, model, and temperature
- **Retrieval Settings**: Adjust number of documents retrieved (K)
- **PDF Processing**: Configure language and processing strategy
- **Chunking Parameters**: Fine-tune chunk sizes and overlap
- **RAG Prompt**: Customize the system prompt template

### 2. Chat History Viewer
- View all question-answer pairs logged by the system
- Search functionality across questions and answers
- Pagination for large datasets
- Response time tracking
- Model tracking for each interaction

## Tech Stack

- **React 18** with TypeScript
- **React Router** for navigation
- **Vite** for build tooling
- **Nginx** for production serving

## Development

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:3000 and proxies API requests to the backend.

If you want to run the frontend against a deployed Railway backend, set `VITE_API_URL` before starting Vite. You can use either the backend origin or the full API base path:

```bash
VITE_API_URL=https://your-backend.up.railway.app
```

or

```bash
VITE_API_URL=https://your-backend.up.railway.app/api
```

## Production Build

The frontend is containerized and runs in Docker:

```bash
docker compose up -d frontend
```

The production build uses a multi-stage Dockerfile:
1. Build stage: Compiles React app with Vite
2. Production stage: Serves static files with Nginx

## Architecture

- **Layout**: Sidebar navigation with settings and history pages
- **API Client**: Centralized fetch wrapper for backend communication
- **Styling**: CSS modules with light/dark mode support

## API Integration

All API calls go through `/api` prefix which is proxied to the backend container:

- `GET /api/settings` - Fetch current settings
- `PUT /api/settings` - Update settings
- `GET /api/history` - Fetch paginated chat history with optional search

## Environment Variables

`VITE_API_URL` - Optional. Backend base URL for the deployed frontend. If omitted, the app falls back to `/api` for the Docker/nginx setup.

`VITE_NOVNC_URL` - Optional. noVNC websocket endpoint for the live browser preview. For Railway, this can be the proxy host and port (for example `kodama.proxy.rlwy.net:11575`) or a full websocket URL. If no path is provided, the frontend defaults to `/websockify`.

For Railway deployment, also set `CORS_ORIGINS` on the backend to include your Vercel domain, for example:

```bash
https://your-frontend.vercel.app,http://localhost:3000,http://127.0.0.1:3000
```
