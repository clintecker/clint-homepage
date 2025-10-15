"""Gallery photo processing and S3 upload"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote

import boto3
from PIL import Image
from slugify import slugify


class GalleryProcessor:
    """Processes photos for gallery: optimizes and uploads to S3"""

    def __init__(self, aws_access_key: str, aws_secret_key: str, aws_region: str, s3_bucket: str):
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

    def optimize_image(self, input_path: Path, output_path: Path, max_width: int = 1600) -> None:
        """Optimize image: resize and compress if needed

        Note: iOS Shortcut should pre-resize to 1200px, so this is mostly a safety check
        """
        with Image.open(input_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Only resize if photo is still too large (safety check)
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save with optimization (lightweight compression)
            img.save(output_path, 'JPEG', quality=90, optimize=True)

    def upload_to_s3(self, file_path: Path, s3_key: str, content_type: str = 'image/jpeg') -> str:
        """Upload file to S3 and return public URL"""
        self.s3_client.upload_file(
            str(file_path),
            self.s3_bucket,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'CacheControl': 'public, max-age=31536000',
            }
        )
        # Return public URL
        return f"https://{self.s3_bucket}/{quote(s3_key)}"

    def process_gallery(
        self,
        photos: List[Path],
        title: str,
        description: str = "",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Process photos for gallery

        Uploads photos to S3 and creates a pending gallery manifest
        GitHub Actions will pick this up and create the markdown file
        """
        slug = slugify(title)
        date = datetime.now()
        date_path = date.strftime('%Y/%b').lower()

        # S3 path: galleries/2025/jan/gallery-slug/
        s3_base_path = f"galleries/{date_path}/{slug}"

        processed_photos = []

        for i, photo_path in enumerate(photos, 1):
            # Generate filenames
            ext = photo_path.suffix
            base_name = f"photo-{i:02d}"

            # Create optimized version
            optimized_path = photo_path.parent / f"{base_name}_optimized.jpg"
            self.optimize_image(photo_path, optimized_path, max_width=1200)

            # Upload both versions
            full_s3_key = f"{s3_base_path}/{base_name}{ext}"
            optimized_s3_key = f"{s3_base_path}/{base_name}_optimized.jpg"

            full_url = self.upload_to_s3(photo_path, full_s3_key, 'image/jpeg')
            optimized_url = self.upload_to_s3(optimized_path, optimized_s3_key, 'image/jpeg')

            processed_photos.append({
                'url': optimized_url,
                'full': full_url,
                'alt': f"{title} - Photo {i}"
            })

        gallery_data = {
            'title': title,
            'slug': slug,
            'date': date.isoformat(),
            'description': description,
            'tags': tags or [],
            'photos': processed_photos
        }

        # Write pending gallery manifest to S3
        # GitHub Actions will pick this up and create the markdown file
        manifest_key = f"pending-galleries/{date.strftime('%Y-%m-%d')}-{slug}.json"
        manifest_json = json.dumps(gallery_data, indent=2)

        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=manifest_key,
            Body=manifest_json.encode('utf-8'),
            ContentType='application/json'
        )

        return gallery_data
