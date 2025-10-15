# Deployment Guide

This guide walks you through deploying your Micro.blog → Hugo → S3 pipeline.

## Current Status

✓ Infrastructure exists:
- S3 bucket: `clintecker.com` (fronted by CloudFront)
- S3 bucket: `i.clintecker.com` (fronted by CloudFront)
- Route53 DNS configured

✓ Micro.blog API configured:
- Username: `clintecker`
- App token saved to `.env`
- 25 posts fetched successfully

## Steps to Deploy

### 1. Get AWS Information

Run the helper script to gather CloudFront distribution IDs:

```bash
./tools/aws_info.sh
```

Or manually get CloudFront distribution IDs:

```bash
# For clintecker.com
aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'clintecker.com')].[Id,DomainName]" \
  --output table

# For i.clintecker.com
aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'i.clintecker.com')].[Id,DomainName]" \
  --output table
```

### 2. Install Hugo (for local testing)

**macOS:**
```bash
brew install hugo
```

**Linux:**
```bash
wget https://github.com/gohugoio/hugo/releases/download/v0.134.2/hugo_extended_0.134.2_Linux-64bit.tar.gz
tar -xzf hugo_extended_0.134.2_Linux-64bit.tar.gz
sudo mv hugo /usr/local/bin/
hugo version
```

### 3. Test Local Build

```bash
# Make sure posts are fetched
source .env
uv run python tools/fetch_microblog.py

# Build the site
hugo --minify --baseURL="https://clintecker.com"

# Check output
ls -la public/
```

### 4. Test S3 Sync (Dry Run)

```bash
# See what would be uploaded
aws s3 sync public/ s3://clintecker.com --dryrun

# Check current bucket contents
aws s3 ls s3://clintecker.com/
```

### 5. Manual Deploy (First Time)

```bash
# Build fresh
rm -rf public/
hugo --minify --baseURL="https://clintecker.com"

# Sync to S3
aws s3 sync public/ s3://clintecker.com --delete

# Invalidate CloudFront (replace DISTRIBUTION_ID)
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"

# Check your site
open https://clintecker.com
```

### 6. Configure GitHub Secrets

Go to your repository on GitHub:
`https://github.com/YOUR_USERNAME/clint-homepage/settings/secrets/actions`

Add these secrets:

| Secret                  | Value                           |
| ----------------------- | ------------------------------- |
| `MB_USERNAME`           | `clintecker`                    |
| `MB_APP_TOKEN`          | `28738AEFB8B446703A10`          |
| `SITE_BUCKET`           | `clintecker.com`                |
| `MEDIA_BUCKET`          | `i.clintecker.com`              |
| `CF_DIST_SITE`          | Get from step 1                 |
| `BASEURL`               | `https://clintecker.com`        |
| `AWS_REGION`            | `us-east-1` (or your region)    |
| `AWS_ACCESS_KEY_ID`     | Your AWS access key             |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key             |

### 7. Create IAM User for GitHub Actions

If you don't have an IAM user for deployments:

```bash
# Create user
aws iam create-user --user-name github-actions-homepage

# Create access key
aws iam create-access-key --user-name github-actions-homepage
```

Attach this policy (save as `github-deploy-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::clintecker.com/*",
        "arn:aws:s3:::clintecker.com",
        "arn:aws:s3:::i.clintecker.com/*",
        "arn:aws:s3:::i.clintecker.com"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "arn:aws:cloudfront::*:distribution/*"
    }
  ]
}
```

Attach the policy:

```bash
aws iam put-user-policy \
  --user-name github-actions-homepage \
  --policy-name DeploymentPolicy \
  --policy-document file://github-deploy-policy.json
```

### 8. Push to GitHub

```bash
git add .
git commit -m "Initial Micro.blog → Hugo → S3 pipeline"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/clint-homepage.git
git push -u origin main
```

### 9. Trigger GitHub Action

Go to Actions tab on GitHub and manually trigger the workflow, or wait for the next cron run (every 20 minutes).

## Troubleshooting

### Hugo build fails

Check that content is properly formatted:
```bash
hugo --debug
```

### S3 sync fails

Check AWS credentials:
```bash
aws sts get-caller-identity
```

### CloudFront not updating

Check invalidation status:
```bash
aws cloudfront list-invalidations --distribution-id YOUR_DIST_ID
```

### No posts showing up

Re-fetch from Micro.blog:
```bash
rm data/cache.json
source .env
uv run python tools/fetch_microblog.py
```

## Monitoring

### Check last build

```bash
# Check S3 last modified
aws s3 ls s3://clintecker.com/index.html

# Check CloudFront logs (if enabled)
aws cloudfront list-distributions --query "DistributionList.Items[?Aliases.Items[0]=='clintecker.com'].Logging"
```

### View GitHub Actions logs

https://github.com/YOUR_USERNAME/clint-homepage/actions

## Next Steps

Once deployed:
1. Test posting from Micro.blog
2. Wait 20 minutes (or trigger manually)
3. Check your site updates
4. Share photos to test gallery creation
5. Bookmark a link to test link-log
