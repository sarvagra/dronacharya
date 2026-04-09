#!/bin/bash
# Deployment startup script for Career Intelligence Platform

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Career Intelligence Platform - Deployment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
echo -e "${YELLOW}Checking Python...${NC}"
python3 --version

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt -q

# Load environment
if [ -f .env ]; then
    echo -e "${YELLOW}Loading configuration from .env...${NC}"
    export $(cat .env | xargs)
else
    echo -e "${YELLOW}⚠️  .env file not found. Using system environment.${NC}"
fi

# Verify Groq API key
if [ -z "$GROQ_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  WARNING: GROQ_API_KEY not set. LLM features will not work.${NC}"
else
    echo -e "${GREEN}✅ Groq API configured${NC}"
fi

# Kill any existing processes on ports
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend
echo -e "${BLUE}Starting Backend (Flask) on :5000...${NC}"
nohup python3 backend.py > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend PID: $BACKEND_PID${NC}"

# Wait for backend to start
sleep 3
if curl -s http://127.0.0.1:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Backend not responding yet${NC}"
fi

# Start frontend
echo -e "${BLUE}Starting Frontend (HTTP Server) on :8000...${NC}"
nohup python3 -m http.server 8000 --directory html > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend PID: $FRONTEND_PID${NC}"

# Wait for frontend to start
sleep 2
if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend not responding yet${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo ""
echo "📍 Access the platform:"
echo -e "   ${BLUE}Frontend: http://127.0.0.1:8000${NC}"
echo -e "   ${BLUE}Backend API: http://127.0.0.1:5000/api${NC}"
echo -e "   ${BLUE}Health Check: http://127.0.0.1:5000/api/health${NC}"
echo ""
echo "📋 Logs:"
echo -e "   Backend: ${PROJECT_DIR}/backend.log"
echo -e "   Frontend: ${PROJECT_DIR}/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Keep this terminal running to maintain services."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Keep processes running
wait
