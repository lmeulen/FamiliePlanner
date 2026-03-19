#!/usr/bin/env python3
"""
List all recipe names from Mealie server.
Fetches recipes from configured Mealie instance and displays them.

Run:  python -m tools.list_mealie_recipes
Options:
  --detailed    Show additional info (slug, categories, tags, rating)
  --page N      Show page N (default: all pages)
"""

import argparse
import asyncio
import sys

import httpx

from app.database import AsyncSessionLocal, init_db
from app.models.settings import AppSetting


async def get_mealie_config():
    """Get Mealie server URL and API token from settings."""
    async with AsyncSessionLocal() as db:
        url_row = await db.get(AppSetting, "mealie_server_url")
        token_row = await db.get(AppSetting, "mealie_api_token")

        url = url_row.value.strip() if url_row else ""
        token = token_row.value.strip() if token_row else ""

        if not url:
            print("❌ Error: Mealie server URL not configured")
            print("   Configure in Settings page or run:")
            print("   python -c \"from tools.list_mealie_recipes import configure; configure()\"")
            sys.exit(1)

        if not token:
            print("❌ Error: Mealie API token not configured")
            print("   Configure in Settings page")
            sys.exit(1)

        return url, token


async def fetch_recipes(mealie_url: str, token: str, page: int = 1, per_page: int = 100):
    """Fetch recipes from Mealie API."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{mealie_url.rstrip('/')}/api/recipes"

    params = {
        "page": page,
        "perPage": per_page,
        "orderBy": "name",
        "orderDirection": "asc",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 401:
                print("❌ Error: Invalid Mealie API token")
                print("   Check your token in Settings")
                sys.exit(1)

            if response.status_code == 404:
                print("❌ Error: Mealie API endpoint not found")
                print("   Check your Mealie server URL")
                sys.exit(1)

            if response.status_code != 200:
                print(f"❌ Error: Mealie API returned status {response.status_code}")
                sys.exit(1)

            return response.json()

        except httpx.TimeoutException:
            print("❌ Error: Mealie server timeout")
            print("   Check if Mealie server is running")
            sys.exit(1)

        except httpx.ConnectError:
            print("❌ Error: Cannot connect to Mealie server")
            print(f"   Check URL: {mealie_url}")
            sys.exit(1)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)


def format_categories(categories: list) -> str:
    """Format category list for display."""
    if not categories:
        return ""
    return f"[{', '.join(categories[:3])}{'...' if len(categories) > 3 else ''}]"


def format_tags(tags: list) -> str:
    """Format tag list for display."""
    if not tags:
        return ""
    return f"#{', #'.join(tags[:3])}{'...' if len(tags) > 3 else ''}"


async def list_recipes(detailed: bool = False, page: int | None = None):
    """List all recipes from Mealie."""
    await init_db()

    print("🔍 Fetching Mealie configuration...")
    mealie_url, token = await get_mealie_config()
    print(f"📡 Connected to: {mealie_url}\n")

    all_recipes = []
    current_page = page if page else 1
    total_pages = 1

    while current_page <= total_pages:
        print(f"📄 Fetching page {current_page}...", end=" ")
        data = await fetch_recipes(mealie_url, token, current_page)

        recipes = data.get("items", [])
        all_recipes.extend(recipes)

        total_pages = data.get("total_pages", 1)
        total_count = data.get("total", 0)

        print(f"({len(recipes)} recipes)")

        # If specific page requested, stop after that page
        if page:
            break

        current_page += 1

    print(f"\n📖 Found {len(all_recipes)} recipe(s) in total\n")
    print("=" * 80)

    if not all_recipes:
        print("No recipes found in Mealie")
        return

    # Display recipes
    for i, recipe in enumerate(all_recipes, 1):
        name = recipe.get("name", "Untitled")
        slug = recipe.get("slug", "")
        rating = recipe.get("rating")
        categories = recipe.get("recipeCategory", [])
        tags = recipe.get("tags", [])

        if detailed:
            # Detailed view
            print(f"{i:3d}. {name}")
            print(f"     Slug: {slug}")
            if categories:
                print(f"     Categories: {format_categories(categories)}")
            if tags:
                print(f"     Tags: {format_tags(tags)}")
            if rating:
                print(f"     Rating: {'⭐' * rating}")
            print()
        else:
            # Simple list
            rating_str = f" {'⭐' * rating}" if rating else ""
            print(f"{i:3d}. {name}{rating_str}")

    print("=" * 80)
    print(f"\nTotal: {len(all_recipes)} recipes")


async def configure():
    """Interactive configuration helper."""
    print("⚙️  Mealie Configuration")
    print("=" * 50)

    url = input("Enter Mealie server URL (e.g., http://localhost:9000): ").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        print("❌ Error: URL must start with http:// or https://")
        sys.exit(1)

    token = input("Enter Mealie API token: ").strip()
    if not token:
        print("❌ Error: Token cannot be empty")
        sys.exit(1)

    await init_db()
    async with AsyncSessionLocal() as db:
        # Store URL
        url_row = await db.get(AppSetting, "mealie_server_url")
        if url_row:
            url_row.value = url
        else:
            db.add(AppSetting(key="mealie_server_url", value=url))

        # Store token
        token_row = await db.get(AppSetting, "mealie_api_token")
        if token_row:
            token_row.value = token
        else:
            db.add(AppSetting(key="mealie_api_token", value=token))

        await db.commit()

    print("\n✅ Configuration saved!")
    print("   Run: python -m tools.list_mealie_recipes")


def main():
    parser = argparse.ArgumentParser(
        description="List all recipe names from Mealie server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.list_mealie_recipes                  # List all recipes
  python -m tools.list_mealie_recipes --detailed       # Show detailed info
  python -m tools.list_mealie_recipes --page 2         # Show page 2 only
  python -m tools.list_mealie_recipes --configure      # Configure Mealie settings
        """,
    )

    parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    parser.add_argument("--page", type=int, help="Show specific page only (1-based)")
    parser.add_argument("--configure", action="store_true", help="Configure Mealie settings")

    args = parser.parse_args()

    try:
        if args.configure:
            asyncio.run(configure())
        else:
            asyncio.run(list_recipes(detailed=args.detailed, page=args.page))
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
