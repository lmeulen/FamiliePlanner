#!/bin/bash

# TWA Android APK Build Script for FamiliePlanner
# This script automates the process of building a signed Android APK using Bubblewrap

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== FamiliePlanner TWA Build Script ===${NC}\n"

# Check if we're in the android directory
if [ ! -f "twa-manifest.json" ]; then
  echo -e "${RED}Error: twa-manifest.json not found${NC}"
  echo "Please run this script from the android/ directory"
  exit 1
fi

# Check if bubblewrap is installed
if ! command -v bubblewrap &> /dev/null; then
  echo -e "${YELLOW}Bubblewrap CLI not found. Installing...${NC}"
  npm install -g @bubblewrap/cli
  echo -e "${GREEN}✓ Bubblewrap CLI installed${NC}\n"
fi

# Check if keystore exists
if [ ! -f "familieplanner.keystore" ]; then
  echo -e "${YELLOW}Keystore not found. Please generate it first:${NC}"
  echo -e "${BLUE}  cd .. && ./scripts/generate-keystore.sh${NC}"
  exit 1
fi

# Check if Java is installed
if ! command -v java &> /dev/null; then
  echo -e "${RED}Error: Java is not installed${NC}"
  echo "Please install Java 11 or higher"
  exit 1
fi

echo -e "${BLUE}Step 1: Validating TWA manifest...${NC}"
if ! bubblewrap validate; then
  echo -e "${RED}✗ Manifest validation failed${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Manifest is valid${NC}\n"

echo -e "${BLUE}Step 2: Checking Digital Asset Links...${NC}"
DOMAIN=$(grep -o '"host": "[^"]*' twa-manifest.json | cut -d'"' -f4)
ASSETLINKS_URL="https://${DOMAIN}/.well-known/assetlinks.json"

echo "Checking: $ASSETLINKS_URL"
if curl -sf "$ASSETLINKS_URL" > /dev/null 2>&1; then
  echo -e "${GREEN}✓ assetlinks.json is accessible${NC}\n"
else
  echo -e "${YELLOW}⚠ Warning: assetlinks.json not accessible at $ASSETLINKS_URL${NC}"
  echo "The app will show a browser bar until Digital Asset Links verification completes (24-48h)"
  echo ""
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo -e "${BLUE}Step 3: Initializing TWA project...${NC}"
if [ ! -d "app" ]; then
  bubblewrap init --manifest=./twa-manifest.json
  echo -e "${GREEN}✓ TWA project initialized${NC}\n"
else
  echo -e "${YELLOW}TWA project already exists, updating...${NC}"
  bubblewrap update --manifest=./twa-manifest.json
  echo -e "${GREEN}✓ TWA project updated${NC}\n"
fi

echo -e "${BLUE}Step 4: Building signed APK...${NC}"
bubblewrap build

if [ $? -eq 0 ]; then
  echo -e "\n${GREEN}✓ Build successful!${NC}\n"

  # Find the APK
  APK_PATH=$(find app/build/outputs/apk -name "*.apk" | head -n 1)

  if [ -n "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "${GREEN}=== Build Summary ===${NC}"
    echo "APK Location: $APK_PATH"
    echo "APK Size: $APK_SIZE"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Install on Android device:"
    echo -e "   ${YELLOW}adb install \"$APK_PATH\"${NC}"
    echo ""
    echo "2. Or transfer APK to device and install manually"
    echo ""
    echo "3. Wait 24-48 hours for Digital Asset Links verification"
    echo "   (browser bar will disappear after verification)"
  fi
else
  echo -e "\n${RED}✗ Build failed${NC}"
  exit 1
fi
