# AWS Infrastructure Setup

This document describes the AWS resources needed to host your site.

## Architecture Overview

```
┌─────────────┐
│ Micro.blog  │
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│ GitHub Actions  │
└────────┬────────┘
         │
         ├──→ S3 (clintecker.com)       ──→ CloudFront (site)      ──→ Route53 (clintecker.com)
         │
         └──→ S3 (i.clintecker.com)     ──→ CloudFront (media)     ──→ Route53 (i.clintecker.com)
```

## Required AWS Resources

### 1. S3 Buckets

#### Site Bucket

**Name:** `clintecker.com`

**Configuration:**
- Static website hosting: **Enabled**
- Index document: `index.html`
- Error document: `404.html`
- Public access: **Blocked** (CloudFront only)
- Versioning: Optional but recommended

**Bucket Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::clintecker.com/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::ACCOUNT_ID:distribution/DISTRIBUTION_ID"
        }
      }
    }
  ]
}
```

#### Media Bucket

**Name:** `i.clintecker.com`

**Configuration:**
- Static website hosting: **Disabled** (use CloudFront)
- Public access: **Blocked** (CloudFront only)
- Versioning: Optional
- CORS: **Enabled** for cross-origin requests

**CORS Configuration:**
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["https://clintecker.com"],
    "ExposeHeaders": [],
    "MaxAgeSeconds": 3600
  }
]
```

**Bucket Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::i.clintecker.com/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::ACCOUNT_ID:distribution/MEDIA_DISTRIBUTION_ID"
        }
      }
    }
  ]
}
```

### 2. CloudFront Distributions

#### Site Distribution

**Origin:**
- Domain: `clintecker.com.s3.us-east-1.amazonaws.com`
- Origin Access: **Origin Access Control** (OAC)
- Protocol: HTTPS only

**Default Cache Behavior:**
- Viewer Protocol Policy: Redirect HTTP to HTTPS
- Allowed HTTP Methods: GET, HEAD, OPTIONS
- Cache Policy: CachingOptimized
- Compress Objects: Yes

**Settings:**
- Price Class: Use all edge locations (or as needed)
- Alternate Domain Names (CNAMEs): `clintecker.com`
- SSL Certificate: Custom SSL certificate from ACM
- Default Root Object: `index.html`

**Custom Error Responses:**
- 404 → /404.html (HTTP 404)
- 403 → /404.html (HTTP 404)

#### Media Distribution

**Origin:**
- Domain: `i.clintecker.com.s3.us-east-1.amazonaws.com`
- Origin Access: **Origin Access Control** (OAC)
- Protocol: HTTPS only

**Default Cache Behavior:**
- Viewer Protocol Policy: Redirect HTTP to HTTPS
- Allowed HTTP Methods: GET, HEAD, OPTIONS
- Cache Policy: CachingOptimized
- Compress Objects: Yes

**Settings:**
- Price Class: Use all edge locations (or as needed)
- Alternate Domain Names (CNAMEs): `i.clintecker.com`
- SSL Certificate: Custom SSL certificate from ACM

### 3. ACM Certificates

**Region:** `us-east-1` (required for CloudFront)

**Certificates needed:**
1. `clintecker.com` (and optionally `*.clintecker.com`)
2. `i.clintecker.com`

**Validation:** DNS validation (recommended)

### 4. Route53 Hosted Zone

**Domain:** `clintecker.com`

**DNS Records:**

```
A clintecker.com          ALIAS → CloudFront site distribution
A i.clintecker.com        ALIAS → CloudFront media distribution
AAAA clintecker.com       ALIAS → CloudFront site distribution (IPv6)
AAAA i.clintecker.com     ALIAS → CloudFront media distribution (IPv6)
```

### 5. IAM User for GitHub Actions

**User Name:** `github-actions-homepage-deploy`

**Policy:**
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
      "Resource": [
        "arn:aws:cloudfront::ACCOUNT_ID:distribution/SITE_DISTRIBUTION_ID",
        "arn:aws:cloudfront::ACCOUNT_ID:distribution/MEDIA_DISTRIBUTION_ID"
      ]
    }
  ]
}
```

**Access Keys:**
- Create access key for CLI/GitHub Actions
- Store `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in GitHub secrets

## Setup Checklist

- [ ] Create S3 bucket for site (`clintecker.com`)
- [ ] Create S3 bucket for media (`i.clintecker.com`)
- [ ] Request ACM certificate for `clintecker.com` in `us-east-1`
- [ ] Request ACM certificate for `i.clintecker.com` in `us-east-1`
- [ ] Validate certificates via DNS
- [ ] Create CloudFront distribution for site
- [ ] Create CloudFront distribution for media
- [ ] Configure Origin Access Control for both distributions
- [ ] Update S3 bucket policies with CloudFront ARNs
- [ ] Create Route53 A and AAAA records
- [ ] Create IAM user for GitHub Actions
- [ ] Create access keys and store in GitHub secrets
- [ ] Test deployment manually
- [ ] Enable GitHub Actions workflow

## Cost Estimates

**Monthly estimates (assuming moderate traffic):**

- S3 Storage (10 GB): ~$0.23
- S3 Requests: ~$0.50
- CloudFront Data Transfer (50 GB): ~$4.25
- CloudFront Requests: ~$0.10
- Route53 Hosted Zone: $0.50

**Total: ~$5-10/month** (will vary based on traffic)

## Troubleshooting

### CloudFront not serving updates

- Check if invalidation completed
- Verify correct distribution ID in GitHub secrets
- Check CloudFront cache policies

### 403 Forbidden errors

- Verify S3 bucket policy allows CloudFront OAC
- Check Origin Access Control settings
- Ensure files were uploaded to S3

### Images not loading

- Verify CORS configuration on media bucket
- Check CloudFront distribution is active
- Verify DNS records for i.clintecker.com

### GitHub Actions failing

- Check AWS credentials in secrets
- Verify IAM policy permissions
- Check CloudFront distribution IDs

## Security Best Practices

1. **Use Origin Access Control** (OAC) instead of legacy OAI
2. **Block all public S3 access** and serve only through CloudFront
3. **Use IAM roles with least privilege** for GitHub Actions
4. **Enable S3 versioning** for content recovery
5. **Use HTTPS only** - redirect HTTP to HTTPS
6. **Enable CloudFront logging** for security monitoring
7. **Rotate IAM access keys** regularly
8. **Use AWS Secrets Manager** for sensitive data if needed

## Maintenance

### Regular Tasks

- **Monitor AWS costs** in Cost Explorer
- **Review CloudFront logs** for suspicious activity
- **Update ACM certificates** (auto-renewal should work)
- **Check S3 storage usage** and clean up old versions if needed

### Updates

- Hugo version updates: modify `.github/workflows/build.yml`
- Python dependencies: update via `uv add package@version`
- AWS resource changes: update this document
