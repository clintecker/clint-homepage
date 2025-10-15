#!/usr/bin/env python3
"""Process gallery photos: download, resize, generate variants, upload to S3."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import boto3
import exifread
import frontmatter
import requests
from PIL import Image


class PhotoProcessor:
    """Processes gallery photos for responsive web display."""

    def __init__(self):
        self.galleries_dir = Path("content/galleries")
        self.static_media_dir = Path("static/media/galleries")
        self.static_media_dir.mkdir(parents=True, exist_ok=True)

        # AWS setup
        self.s3_client = boto3.client("s3")
        self.media_bucket = os.getenv("MEDIA_BUCKET")
        self.media_base_url = os.getenv("BASEURL", "https://i.clintecker.com")

        # Image sizes to generate
        self.sizes = [320, 768, 1200, 1600]

    def _get_file_hash(self, filepath: Path) -> str:
        """Generate SHA256 hash of a file for cache-busting."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:12]

    def _download_photo(self, url: str, output_path: Path) -> bool:
        """Download a photo from URL."""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    def _extract_exif(self, filepath: Path) -> Dict[str, str]:
        """Extract useful EXIF data from image."""
        exif_data = {}
        try:
            with open(filepath, "rb") as f:
                tags = exifread.process_file(f, details=False)
                if "EXIF DateTimeOriginal" in tags:
                    exif_data["date"] = str(tags["EXIF DateTimeOriginal"])
                if "Image Model" in tags:
                    exif_data["camera"] = str(tags["Image Model"])
                if "EXIF FocalLength" in tags:
                    exif_data["focal_length"] = str(tags["EXIF FocalLength"])
        except Exception as e:
            print(f"Error reading EXIF from {filepath}: {e}")
        return exif_data

    def _resize_image(
        self, input_path: Path, output_path: Path, width: int, quality: int = 85
    ) -> bool:
        """Resize image using Pillow."""
        try:
            with Image.open(input_path) as img:
                # Calculate height maintaining aspect ratio
                aspect_ratio = img.height / img.width
                height = int(width * aspect_ratio)

                # Only resize if image is larger than target
                if img.width > width:
                    img = img.resize((width, height), Image.Resampling.LANCZOS)

                # Save with optimization
                if output_path.suffix.lower() in [".jpg", ".jpeg"]:
                    img.save(output_path, "JPEG", quality=quality, optimize=True)
                elif output_path.suffix.lower() == ".avif":
                    # Pillow 10+ supports AVIF
                    img.save(output_path, "AVIF", quality=quality)
                else:
                    img.save(output_path, quality=quality, optimize=True)
            return True
        except Exception as e:
            print(f"Error resizing {input_path} to {width}px: {e}")
            return False

    def _convert_to_avif(self, input_path: Path, output_path: Path) -> bool:
        """Convert image to AVIF using Pillow."""
        try:
            with Image.open(input_path) as img:
                img.save(output_path, "AVIF", quality=80)
            return True
        except Exception as e:
            print(f"Error converting to AVIF: {e}")
            return False

    def _upload_to_s3(
        self, local_path: Path, s3_key: str, content_type: str, cache_control: str
    ) -> Optional[str]:
        """Upload file to S3 and return public URL."""
        if not self.media_bucket:
            print("Warning: MEDIA_BUCKET not set, skipping S3 upload")
            return None

        try:
            self.s3_client.upload_file(
                str(local_path),
                self.media_bucket,
                s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": cache_control,
                },
            )
            return f"{self.media_base_url}/{s3_key}"
        except Exception as e:
            print(f"Error uploading {s3_key} to S3: {e}")
            return None

    def _process_gallery_photos(
        self, gallery_slug: str, photo_urls: List[str]
    ) -> List[Dict]:
        """Process all photos in a gallery."""
        gallery_dir = self.static_media_dir / gallery_slug
        gallery_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = gallery_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        processed_photos = []

        for idx, url in enumerate(photo_urls):
            print(f"Processing photo {idx + 1}/{len(photo_urls)}: {url}")

            # Download original
            parsed_url = urlparse(url)
            ext = Path(parsed_url.path).suffix or ".jpg"
            original_path = temp_dir / f"original_{idx}{ext}"

            if not self._download_photo(url, original_path):
                continue

            # Extract EXIF
            exif = self._extract_exif(original_path)

            # Generate hash for cache-busting
            file_hash = self._get_file_hash(original_path)
            base_name = f"photo_{idx}_{file_hash}"

            variants = {}

            # Generate variants for each size
            for size in self.sizes:
                # JPEG variant
                jpeg_filename = f"{base_name}_{size}w.jpg"
                jpeg_path = gallery_dir / jpeg_filename
                if self._resize_image(original_path, jpeg_path, size):
                    s3_key = f"galleries/{gallery_slug}/{jpeg_filename}"
                    jpeg_url = self._upload_to_s3(
                        jpeg_path,
                        s3_key,
                        "image/jpeg",
                        "public, max-age=31536000, immutable",
                    )

                    # AVIF variant
                    avif_filename = f"{base_name}_{size}w.avif"
                    avif_path = gallery_dir / avif_filename
                    if self._convert_to_avif(jpeg_path, avif_path):
                        avif_s3_key = f"galleries/{gallery_slug}/{avif_filename}"
                        avif_url = self._upload_to_s3(
                            avif_path,
                            avif_s3_key,
                            "image/avif",
                            "public, max-age=31536000, immutable",
                        )

                        variants[f"{size}w"] = {
                            "jpg": jpeg_url or f"/media/galleries/{gallery_slug}/{jpeg_filename}",
                            "avif": avif_url
                            or f"/media/galleries/{gallery_slug}/{avif_filename}",
                        }
                    else:
                        variants[f"{size}w"] = {
                            "jpg": jpeg_url or f"/media/galleries/{gallery_slug}/{jpeg_filename}",
                        }

            processed_photos.append(
                {
                    "alt": f"Photo {idx + 1}",
                    "caption": "",
                    "exif": exif,
                    "variants": variants,
                }
            )

        return processed_photos

    def _create_manifest(self, gallery_slug: str, photos: List[Dict]):
        """Create and save manifest JSON for gallery."""
        manifest = {"gallery": gallery_slug, "items": photos}

        manifest_path = self.static_media_dir / gallery_slug / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Upload manifest to S3
        if self.media_bucket:
            s3_key = f"galleries/{gallery_slug}/manifest.json"
            self._upload_to_s3(
                manifest_path,
                s3_key,
                "application/json",
                "public, max-age=300",  # 5 minute cache
            )

        print(f"Created manifest: {manifest_path}")

    def process_all_galleries(self):
        """Process all galleries that have source_photos."""
        if not self.galleries_dir.exists():
            print("No galleries directory found")
            return

        for gallery_file in self.galleries_dir.glob("*.md"):
            with open(gallery_file, "r") as f:
                post = frontmatter.load(f)

            # Check if gallery needs processing
            if "source_photos" not in post.metadata:
                continue

            slug = post.get("slug", gallery_file.stem)
            photo_urls = post["source_photos"]

            print(f"\nProcessing gallery: {slug}")
            photos = self._process_gallery_photos(slug, photo_urls)

            if photos:
                self._create_manifest(slug, photos)

                # Remove source_photos from frontmatter (processed)
                del post.metadata["source_photos"]
                with open(gallery_file, "w") as f:
                    f.write(frontmatter.dumps(post))

                print(f"Completed gallery: {slug}")


if __name__ == "__main__":
    processor = PhotoProcessor()
    processor.process_all_galleries()
