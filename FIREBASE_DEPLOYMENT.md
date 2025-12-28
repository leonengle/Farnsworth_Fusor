# Firebase Hosting Deployment Guide

This guide explains how to deploy the Farnsworth Fusor web interface to Firebase Hosting.

## Important Note

**Firebase Hosting only serves static files** (HTML, CSS, JavaScript). The Python Flask API server (`web_api_server.py`) **cannot run on Firebase Hosting** and must be hosted separately.

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Firebase Hosting   │  HTTP   │  Python API      │  TCP/UDP │  Raspberry   │
│  (Web Interface)    │────────▶│  Server          │────────▶│  Pi (Target) │
│  (Static Files)     │         │  (Flask)         │         │              │
└─────────────────────┘         └──────────────────┘         └──────────────┘
```

## Step 1: Deploy Web Interface to Firebase

### Prerequisites

1. Install Firebase CLI:

```bash
npm install -g firebase-tools
```

2. Login to Firebase:

```bash
firebase login
```

### Deploy Static Files

1. Build/deploy the web interface:

```bash
# From the project root directory
firebase deploy --only hosting
```

The web interface will be available at: `https://lab-automation-web.web.app` (or your Firebase project URL)

## Step 2: Host the Python API Server

You have several options for hosting the Python API server:

### Option 1: Cloud Run (Google Cloud) - Recommended

Cloud Run can run containerized Python applications:

1. Create a Dockerfile in `src/Host_Codebase/`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV TARGET_IP=192.168.0.2

# Run the application
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 web_api_server:app
```

2. Build and deploy:

```bash
gcloud run deploy fusor-api \
  --source src/Host_Codebase \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TARGET_IP=192.168.0.2
```

3. Update `index.html` with the Cloud Run URL:

```html
<script>
  window.API_BASE_URL = "https://fusor-api-xxxxx.run.app/api";
</script>
```

### Option 2: VPS/Cloud Server (DigitalOcean, AWS EC2, etc.)

1. Deploy the Python API server on your VPS:

```bash
# SSH into your server
ssh user@your-server.com

# Install Python dependencies
pip install -r requirements.txt

# Run with systemd service (create /etc/systemd/system/fusor-api.service)
[Unit]
Description=Farnsworth Fusor API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/FarnsworthFusor_ControlSystem/src/Host_Codebase
Environment="TARGET_IP=192.168.0.2"
ExecStart=/usr/bin/python3 web_api_server.py --host 0.0.0.0 --port 5000
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable fusor-api
sudo systemctl start fusor-api
```

2. Configure nginx reverse proxy (optional but recommended):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location /api {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

3. Update `index.html`:

```html
<script>
  window.API_BASE_URL = "https://api.yourdomain.com/api";
</script>
```

### Option 3: Local Server with Tunnel (Development/Testing)

For testing or if you have a server on your local network:

1. Run the API server locally:

```bash
python web_api_server.py --host 0.0.0.0 --port 5000
```

2. Use a tunnel service (ngrok, Cloudflare Tunnel, etc.):

```bash
# Using ngrok
ngrok http 5000

# Or using Cloudflare Tunnel
cloudflared tunnel --url http://localhost:5000
```

3. Update `index.html` with the tunnel URL:

```html
<script>
  window.API_BASE_URL = "https://xxxxx.ngrok.io/api";
</script>
```

## Step 3: Configure CORS (Important!)

The API server needs to allow requests from Firebase Hosting. Update `web_api_server.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://lab-automation-web.web.app",
            "https://lab-automation-web.firebaseapp.com",
            "http://localhost:8080",  # For local testing
            "http://localhost:*"       # For development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

Or allow all origins (less secure, for testing only):

```python
CORS(app)  # Allows all origins
```

## Step 4: Environment-Specific Configuration

### Development (Local)

- Web interface: `http://localhost:8080` (served locally)
- API: `http://localhost:5000` (auto-detected)

### Production (Firebase)

- Web interface: `https://lab-automation-web.web.app`
- API: Set `window.API_BASE_URL` in `index.html` before deploying

## Deployment Checklist

- [ ] Install Firebase CLI and login
- [ ] Set `window.API_BASE_URL` in `index.html` to your API server URL
- [ ] Configure CORS on API server to allow Firebase domain
- [ ] Deploy web interface: `firebase deploy --only hosting`
- [ ] Ensure API server is running and accessible
- [ ] Test the connection from Firebase-hosted site to API

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:

- Ensure `flask-cors` is installed: `pip install flask-cors`
- Check CORS configuration in `web_api_server.py`
- Verify Firebase domain is in allowed origins

### Connection Refused

- Verify API server is running
- Check firewall rules allow connections on port 5000 (or your configured port)
- Ensure API server is accessible from the internet (not just localhost)

### API Timeouts

- Check network connectivity between API server and Raspberry Pi
- Verify Raspberry Pi is running and accessible
- Check firewall settings for TCP/UDP ports

## Security Considerations

1. **API Authentication**: Consider adding authentication to your API endpoints
2. **HTTPS**: Use HTTPS for both Firebase Hosting and API server
3. **Rate Limiting**: Implement rate limiting on API endpoints
4. **Input Validation**: All inputs are validated, but review security measures
5. **Network Security**: Use VPN or secure network for Raspberry Pi communication

## Quick Start Commands

```bash
# Deploy to Firebase
firebase deploy --only hosting

# Run API server locally (for testing)
cd src/Host_Codebase
python web_api_server.py --host 0.0.0.0 --port 5000

# View Firebase hosting logs
firebase hosting:channel:list
```
