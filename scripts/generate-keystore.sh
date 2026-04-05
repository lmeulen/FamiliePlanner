#!/bin/bash

# Generate Android keystore for signing APK
# This script creates a keystore file for signing the TWA Android APK
#
# Usage: ./scripts/generate-keystore.sh

set -e

KEYSTORE_DIR="./android"
KEYSTORE_FILE="$KEYSTORE_DIR/familieplanner.keystore"
ALIAS="familieplanner"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== FamiliePlanner Android Keystore Generator ===${NC}\n"

# Create android directory if it doesn't exist
mkdir -p "$KEYSTORE_DIR"

# Check if keystore already exists
if [ -f "$KEYSTORE_FILE" ]; then
    echo -e "${YELLOW}Keystore already exists at: $KEYSTORE_FILE${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted. Existing keystore preserved.${NC}"
        exit 1
    fi
    rm "$KEYSTORE_FILE"
fi

# Prompt for keystore details
echo "Enter details for your keystore:"
echo "(Press Enter to use default values shown in brackets)"
echo

read -p "Your name [FamiliePlanner Developer]: " name
name=${name:-"FamiliePlanner Developer"}

read -p "Organization [FamiliePlanner]: " org
org=${org:-"FamiliePlanner"}

read -p "City []: " city
city=${city:-"Unknown"}

read -p "State/Province []: " state
state=${state:-"Unknown"}

read -p "Country code (2 letters) [NL]: " country
country=${country:-"NL"}

echo
echo -e "${YELLOW}Choose a strong password for your keystore (min 6 characters)${NC}"
read -sp "Keystore password: " password
echo
read -sp "Confirm password: " password2
echo

if [ "$password" != "$password2" ]; then
    echo -e "${RED}Passwords do not match. Aborted.${NC}"
    exit 1
fi

if [ ${#password} -lt 6 ]; then
    echo -e "${RED}Password must be at least 6 characters. Aborted.${NC}"
    exit 1
fi

# Generate keystore using keytool
echo
echo -e "${GREEN}Generating keystore...${NC}"

keytool -genkey \
    -v \
    -keystore "$KEYSTORE_FILE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass "$password" \
    -keypass "$password" \
    -dname "CN=$name, OU=$org, L=$city, ST=$state, C=$country"

# Verify keystore
echo
echo -e "${GREEN}Verifying keystore...${NC}"
keytool -list -v -keystore "$KEYSTORE_FILE" -alias "$ALIAS" -storepass "$password"

# Generate SHA-256 fingerprint for Digital Asset Links
echo
echo -e "${GREEN}=== SHA-256 Fingerprint (for assetlinks.json) ===${NC}"
SHA256=$(keytool -list -v -keystore "$KEYSTORE_FILE" -alias "$ALIAS" -storepass "$password" | grep "SHA256:" | cut -d' ' -f3)
echo -e "${YELLOW}$SHA256${NC}"

# Create credentials file
CREDS_FILE="$KEYSTORE_DIR/keystore-credentials.txt"
cat > "$CREDS_FILE" <<EOF
# FamiliePlanner Android Keystore Credentials
# KEEP THIS FILE SECURE - DO NOT COMMIT TO GIT

Keystore file: $KEYSTORE_FILE
Alias: $ALIAS
Password: $password
SHA-256: $SHA256

Generated: $(date)
EOF

echo
echo -e "${GREEN}✓ Keystore generated successfully!${NC}"
echo
echo "Files created:"
echo "  - Keystore: $KEYSTORE_FILE"
echo "  - Credentials: $CREDS_FILE"
echo
echo -e "${RED}IMPORTANT: Keep these files secure and backed up!${NC}"
echo -e "${RED}Add to .gitignore: android/*.keystore android/*-credentials.txt${NC}"
echo
echo "Next steps:"
echo "  1. Update android/.gitignore to exclude sensitive files"
echo "  2. Add SHA-256 fingerprint to app/static/.well-known/assetlinks.json"
echo "  3. Build TWA APK with: cd android && bubblewrap build"
