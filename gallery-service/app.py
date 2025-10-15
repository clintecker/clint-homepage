#!/usr/bin/env python3
"""Gallery upload service for clintecker.com

Receives photos from iOS Share Sheet, optimizes them, uploads to S3,
creates gallery markdown, and commits to GitHub.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from gallery_processor import GalleryProcessor

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max (pre-resized images)

# Configuration from environment
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
S3_MEDIA_BUCKET = os.getenv('S3_MEDIA_BUCKET', 'i.clintecker.com')
GALLERY_API_KEY = os.getenv('GALLERY_API_KEY')

processor = GalleryProcessor(
    aws_access_key=AWS_ACCESS_KEY_ID,
    aws_secret_key=AWS_SECRET_ACCESS_KEY,
    aws_region=AWS_REGION,
    s3_bucket=S3_MEDIA_BUCKET
)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'gallery-service'})


@app.route('/gallery', methods=['POST'])
def create_gallery():
    """Create a new gallery from uploaded photos

    Expects:
    - X-API-Key header: API key for authentication
    - title: Gallery title
    - description: Optional description
    - tags: Optional comma-separated tags
    - photos: Multiple file uploads
    """
    try:
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != GALLERY_API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401

        # Validate request
        if 'photos' not in request.files:
            return jsonify({'error': 'No photos provided'}), 400

        title = request.form.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        description = request.form.get('description', '').strip()
        tags_str = request.form.get('tags', '').strip()
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]

        # Get uploaded files
        photos = request.files.getlist('photos')
        if not photos:
            return jsonify({'error': 'No photos provided'}), 400

        # Limit to 50 photos max (reasonable for pre-resized images)
        if len(photos) > 50:
            return jsonify({'error': f'Too many photos. Maximum 50, got {len(photos)}'}), 400

        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save uploaded files
            photo_paths = []
            for photo in photos:
                if photo.filename:
                    filename = secure_filename(photo.filename)
                    filepath = temp_path / filename
                    photo.save(filepath)
                    photo_paths.append(filepath)

            if not photo_paths:
                return jsonify({'error': 'No valid photos uploaded'}), 400

            # Process gallery (uploads photos + metadata to S3)
            gallery_data = processor.process_gallery(
                photos=photo_paths,
                title=title,
                description=description,
                tags=tags
            )

            return jsonify({
                'success': True,
                'gallery': {
                    'title': gallery_data['title'],
                    'slug': gallery_data['slug'],
                    'photo_count': len(gallery_data['photos']),
                    'url': f"https://clintecker.com/galleries/{gallery_data['slug']}/",
                    'pending': True,
                    'note': 'Gallery will be live in 2-3 minutes after GitHub Actions processes it'
                }
            })

    except Exception as e:
        app.logger.error(f"Error creating gallery: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'false').lower() == 'true')
