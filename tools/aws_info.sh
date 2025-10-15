#!/bin/bash
# Helper script to gather AWS information for GitHub secrets

echo "=== CloudFront Distribution IDs ==="
echo ""
echo "For clintecker.com:"
aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'clintecker.com')].Id" \
  --output text 2>/dev/null || echo "AWS CLI not configured"

echo ""
echo "For i.clintecker.com:"
aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'i.clintecker.com')].Id" \
  --output text 2>/dev/null || echo "AWS CLI not configured"

echo ""
echo "=== S3 Buckets ==="
echo ""
echo "Checking clintecker.com bucket:"
aws s3 ls s3://clintecker.com/ 2>/dev/null || echo "Cannot access bucket"

echo ""
echo "Checking i.clintecker.com bucket:"
aws s3 ls s3://i.clintecker.com/ 2>/dev/null || echo "Cannot access bucket"

echo ""
echo "=== AWS Region ==="
aws configure get region 2>/dev/null || echo "Not configured"

echo ""
echo "=== GitHub Secrets Needed ==="
echo ""
echo "Add these to your GitHub repository secrets:"
echo "  - MB_USERNAME=clintecker"
echo "  - MB_APP_TOKEN=28738AEFB8B446703A10"
echo "  - SITE_BUCKET=clintecker.com"
echo "  - MEDIA_BUCKET=i.clintecker.com"
echo "  - CF_DIST_SITE=<distribution-id-from-above>"
echo "  - BASEURL=https://clintecker.com"
echo "  - AWS_REGION=<region-from-above>"
echo "  - AWS_ACCESS_KEY_ID=<your-access-key>"
echo "  - AWS_SECRET_ACCESS_KEY=<your-secret-key>"
