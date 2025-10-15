#!/usr/bin/env python3
"""Process pending gallery manifests from S3

Checks s3://i.clintecker.com/pending-galleries/ for new JSON manifests,
creates gallery markdown files, and removes processed manifests.
"""

import json
import os
from pathlib import Path

import boto3
import frontmatter


def process_pending_galleries():
    """Check S3 for pending galleries and create markdown files"""
    s3 = boto3.client('s3')
    bucket = 'i.clintecker.com'
    prefix = 'pending-galleries/'

    # List pending manifests
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    if 'Contents' not in response:
        print("No pending galleries")
        return

    content_dir = Path('content/galleries')
    content_dir.mkdir(parents=True, exist_ok=True)

    for obj in response['Contents']:
        key = obj['Key']

        # Skip the directory marker
        if key == prefix:
            continue

        print(f"Processing {key}")

        # Download manifest
        manifest_obj = s3.get_object(Bucket=bucket, Key=key)
        gallery_data = json.loads(manifest_obj['Body'].read().decode('utf-8'))

        # Extract filename from key (e.g., pending-galleries/2025-01-15-slug.json)
        filename = key.replace(prefix, '')

        if not filename.endswith('.json'):
            continue

        # Create markdown filename
        md_filename = filename.replace('.json', '.md')
        md_path = content_dir / md_filename

        # Create frontmatter post
        post = frontmatter.Post(gallery_data.get('description', ''))
        post['title'] = gallery_data['title']
        post['date'] = gallery_data['date']
        post['slug'] = gallery_data['slug']
        post['tags'] = gallery_data.get('tags', [])
        post['type'] = 'gallery'
        post['photos'] = gallery_data['photos']

        # Write markdown file
        with open(md_path, 'w') as f:
            f.write(frontmatter.dumps(post))

        print(f"Created {md_path}")

        # Delete processed manifest
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"Deleted {key}")


if __name__ == '__main__':
    process_pending_galleries()
