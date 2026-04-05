#!/bin/bash

# Icon Generation Script for FamiliePlanner Android APK
# Generates all required icon sizes for TWA/PWA from a source image

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== FamiliePlanner Icon Generator ===${NC}\n"

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
  echo -e "${RED}Error: ImageMagick is not installed${NC}"
  echo "Please install ImageMagick:"
  echo "  Ubuntu/Debian: sudo apt-get install imagemagick"
  echo "  macOS: brew install imagemagick"
  echo "  Windows: Download from https://imagemagick.org/script/download.php"
  exit 1
fi

# Check if source icon exists
SOURCE_ICON="./app/static/icon-source.png"

if [ ! -f "$SOURCE_ICON" ]; then
  echo -e "${YELLOW}Source icon not found at: $SOURCE_ICON${NC}"
  echo ""
  echo "Please create a source icon (recommended: 1024x1024 PNG)"
  echo "You can use an emoji or custom logo"
  echo ""
  echo "Quick emoji-to-PNG option:"
  echo "  1. Visit https://emojipedia.org/house"
  echo "  2. Download high-res emoji image"
  echo "  3. Save as app/static/icon-source.png"
  echo ""
  echo "Or create a custom logo in any design tool"
  exit 1
fi

# Get source icon dimensions
DIMENSIONS=$(identify -format "%wx%h" "$SOURCE_ICON")
echo "Source icon: $SOURCE_ICON ($DIMENSIONS)"

# Verify square aspect ratio
WIDTH=$(identify -format "%w" "$SOURCE_ICON")
HEIGHT=$(identify -format "%h" "$SOURCE_ICON")

if [ "$WIDTH" != "$HEIGHT" ]; then
  echo -e "${YELLOW}Warning: Icon is not square ($DIMENSIONS)${NC}"
  echo "Cropping to square..."
  MIN_DIM=$((WIDTH < HEIGHT ? WIDTH : HEIGHT))
  convert "$SOURCE_ICON" -gravity center -crop ${MIN_DIM}x${MIN_DIM}+0+0 +repage /tmp/icon-square.png
  SOURCE_ICON="/tmp/icon-square.png"
  echo -e "${GREEN}✓ Icon cropped to square${NC}"
fi

OUTPUT_DIR="./app/static"

echo ""
echo -e "${BLUE}Generating icon sizes...${NC}"

# PWA/Android icon sizes
declare -A SIZES=(
  ["icon-72.png"]=72
  ["icon-96.png"]=96
  ["icon-128.png"]=128
  ["icon-144.png"]=144
  ["icon-152.png"]=152
  ["icon-192.png"]=192
  ["icon-384.png"]=384
  ["icon-512.png"]=512
)

for filename in "${!SIZES[@]}"; do
  size=${SIZES[$filename]}
  echo "  Generating ${filename} (${size}x${size})"
  convert "$SOURCE_ICON" -resize ${size}x${size} "$OUTPUT_DIR/$filename"
done

echo ""
echo -e "${BLUE}Generating maskable icon (with safe zone)...${NC}"
# Maskable icon: 80% of content in center, 20% safe zone around edges
convert "$SOURCE_ICON" -resize 410x410 -gravity center -extent 512x512 -background transparent "$OUTPUT_DIR/icon-maskable-512.png"
echo "  Generated icon-maskable-512.png"

echo ""
echo -e "${BLUE}Generating monochrome icon (for Android 13+)...${NC}"
# Monochrome icon: grayscale with transparency
convert "$SOURCE_ICON" -resize 512x512 -colorspace gray -background transparent "$OUTPUT_DIR/icon-monochrome-512.png"
echo "  Generated icon-monochrome-512.png"

echo ""
echo -e "${BLUE}Generating shortcut icons...${NC}"
# Shortcut icons for app shortcuts (192x192 recommended)
for shortcut in "agenda" "tasks" "grocery"; do
  # For now, use the main icon for shortcuts
  # In the future, could use emoji-specific icons
  convert "$SOURCE_ICON" -resize 192x192 "$OUTPUT_DIR/shortcut-${shortcut}.png"
  echo "  Generated shortcut-${shortcut}.png"
done

echo ""
echo -e "${BLUE}Generating favicon...${NC}"
# Favicon (32x32 for compatibility)
convert "$SOURCE_ICON" -resize 32x32 "$OUTPUT_DIR/favicon.png"
echo "  Generated favicon.png"

# Also create .ico file for old browsers
if command -v icotool &> /dev/null; then
  icotool -c -o "$OUTPUT_DIR/favicon.ico" "$OUTPUT_DIR/favicon.png"
  echo "  Generated favicon.ico"
else
  convert "$OUTPUT_DIR/favicon.png" "$OUTPUT_DIR/favicon.ico"
  echo "  Generated favicon.ico (using ImageMagick)"
fi

# Clean up temp file if created
if [ -f "/tmp/icon-square.png" ]; then
  rm /tmp/icon-square.png
fi

echo ""
echo -e "${GREEN}✓ All icons generated successfully!${NC}"
echo ""
echo "Generated files in $OUTPUT_DIR:"
ls -lh "$OUTPUT_DIR"/icon-*.png "$OUTPUT_DIR"/shortcut-*.png "$OUTPUT_DIR"/favicon.* 2>/dev/null || true

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Update manifest.json to reference new icons"
echo "2. Update assetlinks.json with your domain"
echo "3. Deploy to HTTPS server"
echo "4. Build Android APK with: cd android && ./build.sh"
