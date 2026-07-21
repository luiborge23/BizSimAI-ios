# BizSimAI Production Deployment Guide

## Prerequisites

- Domain name (e.g., `bizsimai.com`)
- AWS EC2 instance (t3.micro or larger)
- Let's Encrypt SSL certificate
- Docker installed on EC2

## Step 1: Configure Domain DNS

1. Point your domain's A record to your EC2 instance's public IP
2. Wait for DNS propagation (5-30 minutes)

## Step 2: Deploy Backend to EC2

### SSH into EC2
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-public-ip
```

### Install Docker
```bash
sudo apt update
sudo apt install docker.io -y
sudo usermod -aG docker ubuntu
```

### Clone Repository
```bash
cd ~
git clone https://github.com/luiborge23/BizSimAI-ios.git
cd BizSimAI-ios/BizSimAI
```

### Build and Run Backend
```bash
docker build -t bizsimai-backend .
docker run -d -p 8000:8000 --name bizsimai-backend bizsimai-backend
```

### Setup Nginx with HTTPS

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name bizsimai.com www.bizsimai.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name bizsimai.com www.bizsimai.com;

    ssl_certificate /etc/ssl/certs/bizsimai.crt;
    ssl_certificate_key /etc/ssl/private/bizsimai.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Obtain SSL Certificate with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d bizsimai.com -d www.bizsimai.com
```

### Start Nginx
```bash
sudo cp nginx.conf /etc/nginx/sites-available/bizsimai
sudo ln -s /etc/nginx/sites-available/bizsimai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 3: Update iOS App

### Update Debug.xcconfig
```
BIZSIMAI_BACKEND_URL = https://bizsimai.com
```

### Update Release.xcconfig
```
BIZSIMAI_BACKEND_URL = https://bizsimai.com
```

### Update NetworkService.swift
```swift
#if DEBUG
let BASE_URL = "https://bizsimai.com"
#else
let BASE_URL = "https://bizsimai.com"
#endif
```

## Step 4: Test Deployment

1. Build and run iOS app on simulator
2. Test login flow
3. Test session creation
4. Test student submission flow

## Step 5: Monitor

```bash
# Check backend logs
docker logs -f bizsimai-backend

# Check Nginx status
sudo systemctl status nginx

# Check SSL certificate
sudo certbot certificates
```

## Rollback Plan

If issues occur:
```bash
# Stop backend
docker stop bizsimai-backend
docker rm bizsimai-backend

# Restart with previous version
docker run -d -p 8000:8000 --name bizsimai-backend bizsimai-backend:previous
```
