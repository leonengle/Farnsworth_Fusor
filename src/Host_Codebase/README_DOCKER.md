# Docker Deployment Guide

This guide explains how to build and deploy the Farnsworth Fusor API server using Docker.

## Prerequisites

- Docker installed on your system
- Docker Hub account (optional, for image registry)

## Building the Docker Image

### Option 1: Build from Host_Codebase directory (Recommended)

```bash
cd src/Host_Codebase
docker build -t fusor-api:latest .
```

**Important:** Before building, copy `requirements.txt` to the Host_Codebase directory:

```bash
# From project root
cp requirements.txt src/Host_Codebase/requirements.txt
```

### Option 2: Build from project root

```bash
# From project root
docker build -f src/Host_Codebase/Dockerfile.from-root -t fusor-api:latest .
```

## Running the Container Locally

```bash
docker run -d \
  --name fusor-api \
  -p 8080:8080 \
  -e TARGET_IP=192.168.0.2 \
  -e PORT=8080 \
  fusor-api:latest
```

Access the API at: `http://localhost:8080/api/status`

## Environment Variables

You can override these via `-e` flags or environment file:

- `PORT`: Port to bind to (default: 8080)
- `TARGET_IP`: Raspberry Pi IP address (default: 192.168.0.2)
- `TCP_COMMAND_PORT`: TCP command port (default: 2222)
- `UDP_DATA_PORT`: UDP data port (default: 12345)
- `UDP_STATUS_PORT`: UDP status port (default: 8888)
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins

Example with environment file:

```bash
docker run -d \
  --name fusor-api \
  -p 8080:8080 \
  --env-file .env \
  fusor-api:latest
```

## Deploying to Cloud Run

### Using gcloud CLI

1. Build and push to Google Container Registry:

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Build using Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/fusor-api

# Or build locally and push
docker build -t gcr.io/YOUR_PROJECT_ID/fusor-api .
docker push gcr.io/YOUR_PROJECT_ID/fusor-api
```

2. Deploy to Cloud Run:

```bash
gcloud run deploy fusor-api \
  --image gcr.io/YOUR_PROJECT_ID/fusor-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars TARGET_IP=192.168.0.2 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10
```

### Using Dockerfile directly (Cloud Run buildpacks)

From the `src/Host_Codebase` directory:

```bash
gcloud run deploy fusor-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TARGET_IP=192.168.0.2 \
  --memory 512Mi \
  --timeout 300
```

Cloud Run will automatically:

- Detect the Dockerfile
- Build the container
- Deploy it

## Deploying to Other Platforms

### AWS ECS/Fargate

1. Build and push to Amazon ECR:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t fusor-api .
docker tag fusor-api:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/fusor-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/fusor-api:latest
```

2. Create ECS task definition and deploy (see AWS documentation)

### Azure Container Instances

```bash
# Login to Azure
az login

# Create resource group
az group create --name fusor-rg --location eastus

# Create container instance
az container create \
  --resource-group fusor-rg \
  --name fusor-api \
  --image fusor-api:latest \
  --dns-name-label fusor-api \
  --ports 8080 \
  --environment-variables TARGET_IP=192.168.0.2 PORT=8080
```

### Docker Compose (for local development)

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  fusor-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - TARGET_IP=192.168.0.2
      - TCP_COMMAND_PORT=2222
      - UDP_DATA_PORT=12345
      - UDP_STATUS_PORT=8888
      - CORS_ORIGINS=http://localhost:8080,https://lab-automation-web.web.app
    restart: unless-stopped
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import requests; requests.get('http://localhost:8080/api/status')",
        ]
      interval: 30s
      timeout: 3s
      retries: 3
```

Run with:

```bash
docker-compose up -d
```

## Testing the Container

```bash
# Check container logs
docker logs fusor-api

# Test health endpoint
curl http://localhost:8080/api/status

# Test connection
curl http://localhost:8080/api/telemetry
```

## Troubleshooting

### Container won't start

- Check logs: `docker logs fusor-api`
- Verify environment variables are set correctly
- Ensure port is not already in use

### Connection to Raspberry Pi fails

- Verify `TARGET_IP` is correct and accessible from the container
- Check firewall rules
- For Cloud Run, ensure the Pi is accessible over the internet or use VPN

### CORS errors

- Set `CORS_ORIGINS` environment variable with your Firebase domain
- Ensure the web interface URL is included in allowed origins

## Security Notes

- The container runs as non-root user (appuser)
- Exposed ports should be secured with firewall rules
- Consider adding authentication to API endpoints
- Use secrets management for sensitive environment variables
