# iOS Shortcut Setup

This guide shows how to create the "Create Gallery" shortcut that pre-processes photos on your iPhone before uploading.

## Why Pre-process?

**Without pre-processing:**
- 20 photos × 12MB = 240MB upload
- 3-4 minute wait
- Limited to 20 photos

**With pre-processing:**
- 50 photos × 300KB = 15MB upload
- 30-60 second wait
- Can handle 50 photos easily

## Create the Shortcut

### Method 1: Import (Easiest)

1. Open this URL on your iPhone: `[Will provide after deployment]`
2. Tap "Get Shortcut"
3. Tap "Add Shortcut"
4. Done!

### Method 2: Manual Creation

1. Open **Shortcuts** app
2. Tap **+** (new shortcut)
3. Name it **"Create Gallery"**
4. Add these actions:

#### Actions List

```
1. Get File
   - From: Shortcut Input
   - Type: Images

2. Resize Image
   - Image: Get File
   - Width: 1200
   - Height: Auto

3. Convert Image
   - Image: Resized Image
   - Format: JPEG
   - Quality: 85%

4. Ask for Input
   - Prompt: "Gallery Title"
   - Input Type: Text
   - Default: ""

5. Ask for Input
   - Prompt: "Description (optional)"
   - Input Type: Text
   - Default: ""

6. Ask for Input
   - Prompt: "Tags (comma-separated, optional)"
   - Input Type: Text
   - Default: ""

7. Get Contents of URL
   - URL: https://clintecker-gallery.fly.dev/gallery
   - Method: POST
   - Headers: (none needed)
   - Request Body: Form
   - Form Fields:
     * title = Provided Input (from step 4)
     * description = Provided Input (from step 5)
     * tags = Provided Input (from step 6)
     * photos = Converted Image (from step 3)

8. Get Dictionary from Input
   - Input: Contents of URL

9. Get Dictionary Value
   - Key: success
   - Dictionary: Dictionary

10. If success equals 1
    Then:
      Get Dictionary Value
        Key: gallery.url
        Dictionary: Dictionary

      Show Alert
        Title: "Gallery Created!"
        Message: "View at: Dictionary Value"

    Otherwise:
      Get Dictionary Value
        Key: error
        Dictionary: Dictionary

      Show Alert
        Title: "Error Creating Gallery"
        Message: Dictionary Value
```

### Configure Shortcut Settings

1. Tap **⋮** (three dots)
2. Tap **Details**
3. Enable **Show in Share Sheet**
4. Under **Share Sheet Types:**
   - Enable: **Images**
   - Disable everything else
5. Tap **Done**

## Usage

### From Photos App

1. Select photos (1-50)
2. Tap Share button
3. Scroll down to "Create Gallery"
4. Enter title (required)
5. Enter description (optional)
6. Enter tags (optional, comma-separated)
7. Wait 30-60 seconds
8. See "Gallery Created!" alert

### From Files or Other Apps

Same process - any app that can share images will work.

## Troubleshooting

### "No photos provided"
- Make sure you selected images before tapping Share
- Try selecting fewer photos

### "Maximum 50 photos"
- Create two galleries: Part 1 and Part 2

### "Connection timeout"
- Check internet connection
- Try again (service might have been sleeping)

### "Error creating gallery"
- Check that title is not empty
- Check that photos are valid images
- Try with fewer photos

## How It Works

The shortcut pre-processes your photos on-device:

1. **Resize:** 12MP photo → 1200px wide (~300KB)
2. **Convert:** HEIC → JPEG at 85% quality
3. **Upload:** Only the processed versions

**Benefits:**
- 40x smaller uploads (12MB → 300KB per photo)
- Much faster (30 sec vs 3 min)
- More photos allowed (50 vs 20)
- Uses less data
- Works on slower connections

## Screenshot Example

[TODO: Add screenshot after testing]

## Advanced: Customize Compression

To adjust image quality in the shortcut:

1. Open shortcut
2. Find "Convert Image" action
3. Change **Quality** slider
   - 60%: Smaller files, lower quality
   - 85%: Balanced (recommended)
   - 100%: Larger files, max quality
