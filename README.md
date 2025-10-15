# Clint Ecker's Personal Site

A static site generated from Micro.blog content and deployed to AWS S3/CloudFront.

## Overview

This site uses:
- **Micro.blog** as the authoring platform
- **Hugo** as the static site generator
- **GitHub Actions** for automated builds
- **AWS S3** for hosting
- **CloudFront** for CDN
- **Python** for content fetching and photo processing

## Project Structure

```
clint-homepage/
├── .github/workflows/build.yml  # Automated build pipeline
├── tools/
│   ├── fetch_microblog.py       # Fetch posts/bookmarks from Micro.blog
│   └── process_photos.py        # Generate responsive image variants
├── content/
│   ├── posts/                   # Blog posts and micro-posts
│   ├── galleries/               # Photo galleries
│   └── links/                   # Daily link logs
├── static/media/                # Generated image variants
├── layouts/
│   ├── partials/gallery.html    # Gallery rendering component
│   ├── galleries/single.html    # Gallery page template
│   └── links/list.html          # Links page template
├── data/cache.json              # Cache of processed items
└── config.toml                  # Hugo configuration
```

## Setup

### Prerequisites

- Python 3.12+
- Hugo (extended version)
- AWS account with S3 and CloudFront configured
- Micro.blog account

### Local Development

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set environment variables:**
   ```bash
   export MB_USERNAME="clintecker"
   export MB_APP_TOKEN="your-microblog-app-token"
   export MB_API_BASE="https://micro.blog"
   export MEDIA_BUCKET="i.clintecker.com"
   export BASEURL="https://clintecker.com"
   export AWS_REGION="us-east-1"
   ```

   Get your Micro.blog app token from: https://micro.blog/account/apps

3. **Fetch content:**
   ```bash
   uv run python tools/fetch_microblog.py
   ```

4. **Process photos:**
   ```bash
   uv run python tools/process_photos.py
   ```

5. **Build site:**
   ```bash
   hugo server -D
   ```

### GitHub Secrets

Configure these secrets in your GitHub repository settings:

| Secret                  | Description                                    |
| ----------------------- | ---------------------------------------------- |
| `MB_USERNAME`           | Your Micro.blog username (clintecker)          |
| `MB_APP_TOKEN`          | Micro.blog app token from micro.blog/account/apps |
| `AWS_ACCESS_KEY_ID`     | AWS IAM access key                             |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key                             |
| `AWS_REGION`            | AWS region (e.g., `us-east-1`)                 |
| `SITE_BUCKET`           | S3 bucket for site (e.g., `clintecker.com`)    |
| `MEDIA_BUCKET`          | S3 bucket for media (e.g., `i.clintecker.com`) |
| `CF_DIST_SITE`          | CloudFront distribution ID                     |
| `BASEURL`               | Site URL (e.g., `https://clintecker.com`)      |

## Workflow

### Automated Build

The GitHub Actions workflow runs:
- **Every 20 minutes** (via cron schedule)
- **On push to main branch**
- **Manual trigger** via workflow_dispatch

### Content Pipeline

```
Micro.blog → fetch_microblog.py → Hugo content files
                                 ↓
Gallery photos → process_photos.py → S3 media bucket → Manifest JSON
                                                      ↓
                                          Hugo build → S3 site bucket
                                                      ↓
                                          CloudFront invalidation
```

## Authoring

### Posts

Write posts in Micro.blog (web or iOS app). They will automatically appear on your site after the next build.

### Photo Galleries

Share photos from the iOS share sheet to Micro.blog. If the post contains primarily photos with minimal text, it will be converted to a gallery with responsive image variants.

### Links

Use Micro.blog's bookmark feature to save interesting links. They will be aggregated into daily link logs.

## AWS Infrastructure

See [AWS_SETUP.md](./AWS_SETUP.md) for detailed AWS configuration instructions.

## License

MIT

## Author

Clint Ecker
