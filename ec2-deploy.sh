#!/bin/bash

# BizSimAI EC2 Deployment Script
# This script deploys the backend to EC2 and handles password resets

set -e  # Exit on any error

EC2_IP="18.215.180.58"
SSH_KEY="$HOME/.ssh/bizsimai"
LOCAL_BACKEND="/Users/luisborges/2026/BizSimAI-ios/BizSimAI/backend"
REMOTE_DIR="/home/ec2-user/bizsimai"

echo "=========================================="
echo "🚀 BizSimAI EC2 Deployment"
echo "=========================================="

# Step 1: Sync backend code
echo ""
echo "Step 1: Syncing backend code..."
rsync -avz -e "ssh -i $SSH_KEY" \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  "$LOCAL_BACKEND/" ec2-user@$EC2_IP:$REMOTE_DIR/backend/

echo "✅ Code synced"

# Step 2: Rebuild Docker container
echo ""
echo "Step 2: Rebuilding Docker container..."
ssh -i $SSH_KEY ec2-user@$EC2_IP "cd $REMOTE_DIR && docker-compose build bizsim-backend"
echo "✅ Docker container rebuilt"

# Step 3: Restart container
echo ""
echo "Step 3: Restarting container..."
ssh -i $SSH_KEY ec2-user@$EC2_IP "cd $REMOTE_DIR && docker-compose restart bizsim-backend"
echo "✅ Container restarted"

# Step 4: Wait for container to be healthy
echo ""
echo "Step 4: Waiting for container to be healthy..."
sleep 10

# Step 5: Reset passwords (critical step!)
echo ""
echo "Step 5: Resetting default passwords..."
ssh -i $SSH_KEY ec2-user@$EC2_IP "cd $REMOTE_DIR && python3 backend/reset_passwords.py"
echo "✅ Passwords reset"

# Step 6: Verify deployment
echo ""
echo "Step 6: Verifying deployment..."
curl -s http://$EC2_IP/api/health | python3 -m json.tool
echo "✅ Deployment verified"

echo ""
echo "=========================================="
echo "🎉 Deployment Complete!"
echo "=========================================="
