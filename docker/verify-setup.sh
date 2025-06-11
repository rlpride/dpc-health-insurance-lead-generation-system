#!/bin/bash

# Docker Setup Verification Script for Lead Generation System
# This script verifies that all Docker configuration files and dependencies are in place

echo "🐳 Lead Generation System - Docker Setup Verification"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

# Function to check if a directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

# Check Docker and Docker Compose
echo "🔍 Checking Docker Dependencies:"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker installed ($(docker --version))"
else
    echo -e "${RED}✗${NC} Docker not installed or not in PATH"
fi

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose installed ($(docker-compose --version))"
else
    echo -e "${RED}✗${NC} Docker Compose not installed or not in PATH"
fi

echo ""

# Check main Docker files
echo "📁 Checking Main Docker Files:"
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file ".env.docker"
check_file ".dockerignore"
check_file "DOCKER_SETUP.md"

echo ""

# Check docker configuration directory
echo "⚙️  Checking Docker Configuration Files:"
check_dir "docker"
check_file "docker/init-db.sql"
check_file "docker/rabbitmq.conf"
check_file "docker/prometheus.yml"

echo ""

# Check volume directories
echo "📂 Checking Volume Directories:"
check_dir "logs"
check_dir "results"
check_dir "data"

echo ""

# Check Python dependencies
echo "🐍 Checking Python Files:"
check_file "requirements.txt"
check_file "cli.py"
check_file "setup.py"

echo ""

# Check environment configuration
echo "🔧 Checking Environment Configuration:"
if [ -f ".env.docker" ]; then
    echo -e "${GREEN}✓${NC} .env.docker exists"
    
    # Check for placeholder values that need to be replaced
    echo -e "${YELLOW}⚠️${NC}  Please verify these API keys in .env.docker:"
    grep -E "(API_KEY|SECRET_KEY)" .env.docker | head -5
    echo "   ... (update with your actual values)"
else
    echo -e "${RED}✗${NC} .env.docker missing"
fi

echo ""

# Final recommendation
echo "🚀 Next Steps:"
echo "1. Update .env.docker with your actual API keys"
echo "2. Run: docker-compose up -d postgres redis rabbitmq"
echo "3. Run: docker-compose --profile setup up db-init"
echo "4. Run: docker-compose up -d app"
echo "5. Check: docker-compose ps"
echo ""
echo "For detailed instructions, see DOCKER_SETUP.md"
echo ""
echo "Happy containerizing! 🎉"