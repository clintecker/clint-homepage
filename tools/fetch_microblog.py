#!/usr/bin/env python3
"""Fetch posts and bookmarks from Micro.blog JSON feeds and convert to Hugo content."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
import requests
from slugify import slugify


class MicroblogFetcher:
    """Fetches and processes Micro.blog content into Hugo markdown files."""

    def __init__(self, cache_path: str = "data/cache.json"):
        self.cache_path = Path(cache_path)
        self.cache = self._load_cache()
        self.content_dir = Path("content")
        self.posts_dir = self.content_dir / "posts"
        self.galleries_dir = self.content_dir / "galleries"
        self.links_dir = self.content_dir / "links"

        # Micro.blog API configuration
        self.api_base = os.getenv("MB_API_BASE", "https://micro.blog")
        self.username = os.getenv("MB_USERNAME", "")
        self.token = os.getenv("MB_APP_TOKEN", "")

        # Ensure directories exist
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.galleries_dir.mkdir(parents=True, exist_ok=True)
        self.links_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache of previously processed items."""
        if self.cache_path.exists():
            with open(self.cache_path, "r") as f:
                return json.load(f)
        return {"posts": [], "bookmarks": []}

    def _save_cache(self):
        """Save cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f, indent=2)

    def fetch_api(self, endpoint: str) -> List[Dict[str, Any]]:
        """Fetch data from Micro.blog API with authentication."""
        if not self.token:
            print("Error: MB_APP_TOKEN not set")
            return []

        url = f"{self.api_base}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return []

    def _strip_html(self, html: str) -> str:
        """Simple HTML tag removal."""
        return re.sub(r"<[^>]+>", "", html)

    def _html_to_markdown(self, html: str) -> str:
        """Convert basic HTML to Markdown."""
        # This is a simple conversion; you may want to use a library like html2text
        text = html
        # Convert links
        text = re.sub(r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>', r"[\2](\1)", text)
        # Convert images
        text = re.sub(r'<img\s+src="([^"]+)"[^>]*alt="([^"]*)"[^>]*>', r"![\2](\1)", text)
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def _extract_photos(self, item: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract photo attachments from an item."""
        photos = []
        for attachment in item.get("attachments", []):
            if attachment.get("mime_type", "").startswith("image/"):
                photos.append(
                    {
                        "url": attachment.get("url", ""),
                        "alt": attachment.get("title", ""),
                    }
                )
        return photos

    def _is_photo_post(self, item: Dict[str, Any]) -> bool:
        """Determine if an item is primarily a photo post."""
        photos = self._extract_photos(item)
        content_html = item.get("content_html", "")
        content_text = self._strip_html(content_html).strip()

        # Photo post if it has photos and minimal text
        return len(photos) > 0 and len(content_text) < 200

    def _create_post(self, item: Dict[str, Any]):
        """Create a Hugo post from a Micro.blog item."""
        item_id = item.get("id")
        if item_id in self.cache["posts"]:
            return

        date_str = item.get("date_published", "")
        if not date_str:
            return

        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        title = item.get("title", "")
        content_html = item.get("content_html", "")
        content_text = item.get("content_text", "")

        # Use content_text if available, otherwise convert HTML
        if content_text:
            content = content_text
        else:
            content = self._html_to_markdown(content_html)

        # Generate slug
        if title:
            slug = slugify(title)
        else:
            # Use first few words for untitled posts
            words = content.split()[:5]
            slug = slugify(" ".join(words))

        # Create frontmatter
        post = frontmatter.Post(content)
        post["title"] = title or ""
        post["date"] = date.isoformat()
        post["slug"] = slug
        post["tags"] = item.get("tags", [])
        if not title:
            post["type"] = "micro"

        # Photos
        photos = self._extract_photos(item)
        if photos:
            post["photos"] = photos

        # Write to file
        filename = f"{date.strftime('%Y-%m-%d')}-{slug}.md"
        filepath = self.posts_dir / filename
        with open(filepath, "w") as f:
            f.write(frontmatter.dumps(post))

        print(f"Created post: {filepath}")
        self.cache["posts"].append(item_id)

    def _create_gallery(self, item: Dict[str, Any]):
        """Create a Hugo gallery page from a photo post."""
        item_id = item.get("id")
        if item_id in self.cache["posts"]:
            return

        date_str = item.get("date_published", "")
        if not date_str:
            return

        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        title = item.get("title", "")
        content_html = item.get("content_html", "")
        content_text = item.get("content_text", "")

        # Use content_text if available, otherwise convert HTML
        if content_text:
            content = content_text
        else:
            content = self._html_to_markdown(content_html)

        # Generate slug
        if title:
            slug = slugify(title)
        else:
            slug = f"gallery-{date.strftime('%Y%m%d-%H%M%S')}"

        # Create frontmatter
        gallery = frontmatter.Post(content)
        gallery["title"] = title or f"Gallery {date.strftime('%Y-%m-%d')}"
        gallery["date"] = date.isoformat()
        gallery["slug"] = slug
        gallery["tags"] = item.get("tags", [])
        gallery["type"] = "gallery"
        gallery["gallery_manifest"] = f"/media/galleries/{slug}/manifest.json"

        # Store photo URLs for processing
        photos = self._extract_photos(item)
        gallery["source_photos"] = [p["url"] for p in photos]

        # Write to file
        filename = f"{date.strftime('%Y-%m-%d')}-{slug}.md"
        filepath = self.galleries_dir / filename
        with open(filepath, "w") as f:
            f.write(frontmatter.dumps(gallery))

        print(f"Created gallery: {filepath}")
        self.cache["posts"].append(item_id)

    def _create_link(self, item: Dict[str, Any]):
        """Add a bookmark to the daily links file."""
        item_id = item.get("id")
        if item_id in self.cache["bookmarks"]:
            return

        date_str = item.get("date_published", "")
        if not date_str:
            return

        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        url = item.get("url", "")
        title = item.get("title", "")
        content_html = item.get("content_html", "")

        # Convert HTML to markdown
        content = self._html_to_markdown(content_html) if content_html else ""

        # Daily links file
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        filepath = self.links_dir / filename

        # Load existing or create new
        if filepath.exists():
            with open(filepath, "r") as f:
                links_page = frontmatter.load(f)
        else:
            links_page = frontmatter.Post("")
            links_page["title"] = f"Links for {date.strftime('%B %d, %Y')}"
            links_page["date"] = date.replace(hour=0, minute=0, second=0).isoformat()
            links_page["type"] = "links"

        # Append link
        link_entry = f"\n\n### [{title}]({url})\n\n{content}"
        links_page.content += link_entry

        # Write to file
        with open(filepath, "w") as f:
            f.write(frontmatter.dumps(links_page))

        print(f"Added link to: {filepath}")
        self.cache["bookmarks"].append(item_id)

    def process_posts(self):
        """Process posts from Micro.blog API."""
        if not self.username:
            print("Error: MB_USERNAME not set")
            return

        endpoint = f"/posts/{self.username}"
        items = self.fetch_api(endpoint)
        print(f"Found {len(items)} posts")

        for item in items:
            if self._is_photo_post(item):
                self._create_gallery(item)
            else:
                self._create_post(item)

    def process_bookmarks(self):
        """Process bookmarks from Micro.blog API."""
        endpoint = "/posts/bookmarks"
        items = self.fetch_api(endpoint)
        print(f"Found {len(items)} bookmarks")

        for item in items:
            self._create_link(item)

    def run(self):
        """Run the fetcher with environment variables."""
        if not self.username or not self.token:
            print("Error: MB_USERNAME and MB_APP_TOKEN must be set")
            return

        print(f"Processing posts for @{self.username}")
        self.process_posts()

        print(f"Processing bookmarks for @{self.username}")
        self.process_bookmarks()

        self._save_cache()
        print("Done!")


if __name__ == "__main__":
    fetcher = MicroblogFetcher()
    fetcher.run()
