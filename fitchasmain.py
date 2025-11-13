#!/usr/bin/env python3
"""
Booru to Szurubooru Uploader (Batch upload version)
Downloads images from booru sites and Twitter/X using gallery-dl and uploads them to Szurubooru after downloads complete
"""

import json
import os
import subprocess
import requests
from pathlib import Path
import time
import base64
import sys
import re

# Configuration (Placeholders - **USER MUST CONFIGURE**)
SZURU_URL = "https://your-szurubooru-url.com"  # Replace with your Szurubooru URL
SZURU_USER = "your_username"  # Replace with your Szurubooru username
SZURU_TOKEN = "your-api-token"  # Replace with your Szurubooru API Token
DOWNLOAD_DIR = "./booru_downloads"

# Rule34 API credentials (Placeholders - **USER MUST CONFIGURE**)
RULE34_API_KEY = "your-rule34-api-key"  # Replace with your Rule34 API Key
RULE34_USER_ID = "your-rule34-user-id"  # Replace with your Rule34 User ID

# Szurubooru API headers setup
auth_string = f"{SZURU_USER}:{SZURU_TOKEN}"
try:
    auth_token = base64.b64encode(auth_string.encode()).decode('ascii')
except:
    # Fallback for empty/invalid config during initial setup
    auth_token = "placeholder" 

headers = {
    "Authorization": f"Token {auth_token}",
    "Accept": "application/json"
}

# Track upload stats
upload_stats = {"uploaded": 0, "failed": 0, "total": 0}

def setup_gallery_dl_config(check_twitter=False):
    """Setup gallery-dl configuration with Rule34 API credentials"""
    config_dir = Path.home() / ".config" / "gallery-dl"
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('APPDATA', '')) / "gallery-dl"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    
    # Create or update config
    config = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except:
                config = {}
    
    # Add Rule34 credentials (using placeholders if not configured)
    if "extractor" not in config:
        config["extractor"] = {}
    if "rule34" not in config["extractor"]:
        config["extractor"]["rule34"] = {}
    
    # Only update if placeholders are used, otherwise let existing config prevail
    if config["extractor"]["rule34"].get("api-key") in [None, RULE34_API_KEY]:
         config["extractor"]["rule34"]["api-key"] = RULE34_API_KEY
    if config["extractor"]["rule34"].get("user-id") in [None, RULE34_USER_ID]:
        config["extractor"]["rule34"]["user-id"] = RULE34_USER_ID

    
    # Check Twitter configuration if requested
    if check_twitter:
        if "twitter" not in config["extractor"] or not config["extractor"]["twitter"]:
            print("\n" + "!"*50)
            print("⚠️  WARNING: Twitter cookies not configured!")
            print("!"*50)
            setup_twitter_cookies(config, config_file)
        else:
            print("✓ Twitter configuration found")
    
    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Gallery-dl config updated")

def setup_twitter_cookies(config, config_file):
    """Guide user through Twitter cookie setup"""
    print("\nTo download from Twitter, you need to provide authentication.")
    print("\nChoose a method:")
    print("  1. Use browser cookies (Easiest - reads from your browser)")
    print("  2. Use cookies.txt file (Manual export)")
    print("  3. Skip for now (download will likely fail)")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        print("\nAvailable browsers:")
        print("  1. Chrome")
        print("  2. Firefox")
        print("  3. Edge")
        print("  4. Opera")
        print("  5. Safari")
        browser_choice = input("Select browser (1-5): ").strip()
        
        browser_map = {
            "1": "chrome",
            "2": "firefox",
            "3": "edge",
            "4": "opera",
            "5": "safari"
        }
        
        browser = browser_map.get(browser_choice, "chrome")
        
        if "extractor" not in config:
            config["extractor"] = {}
        if "twitter" not in config["extractor"]:
            config["extractor"]["twitter"] = {}
        
        config["extractor"]["twitter"]["cookies-from-browser"] = browser
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configured to use {browser} cookies")
        print("  Make sure you're logged into Twitter in that browser!")
        
    elif choice == "2":
        print("\nHow to get cookies.txt:")
        print("  1. Install browser extension:")
        print("     Chrome: 'Get cookies.txt LOCALLY'")
        print("     Firefox: 'cookies.txt'")
        print("  2. Go to twitter.com (while logged in)")
        print("  3. Click extension and export cookies")
        print("  4. Save the file somewhere permanent")
        
        cookie_path = input("\nEnter full path to cookies.txt file: ").strip()
        
        if cookie_path and os.path.exists(cookie_path):
            if "extractor" not in config:
                config["extractor"] = {}
            if "twitter" not in config["extractor"]:
                config["extractor"]["twitter"] = {}
            
            # Convert to proper path format
            cookie_path = os.path.abspath(cookie_path)
            config["extractor"]["twitter"]["cookies"] = cookie_path
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✓ Configured to use cookies file: {cookie_path}")
        else:
            print("\n✗ File not found. Skipping Twitter configuration.")
    
    else:
        print("\n⚠️  Skipping Twitter setup. Downloads may fail without authentication.")
        print("    You can configure this later by editing:")
        print(f"    {config_file}")

def print_progress_bar(current, total, bar_length=40):
    """Print a progress bar"""
    percent = float(current) / total
    filled = int(round(percent * bar_length))
    arrow = '=' * filled
    spaces = ' ' * (bar_length - filled)
    
    sys.stdout.write(f'\r[{arrow}{spaces}] {current}/{total} ({int(percent * 100)}%)')
    sys.stdout.flush()

def get_file_token(filepath):
    """Upload file and get token from Szurubooru"""
    try:
        with open(filepath, 'rb') as f:
            files = {'content': f}
            response = requests.post(
                f"{SZURU_URL}/api/uploads",
                headers=headers,
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()['token']
            else:
                return None
    except Exception as e:
        return None

def create_post(token, tags, safety="safe", source=None):
    """Create a post in Szurubooru"""
    try:
        data = {
            "tags": tags,
            "safety": safety,
            "contentToken": token
        }
        
        if source:
            data["source"] = source
        
        response = requests.post(
            f"{SZURU_URL}/api/posts",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None

def extract_twitter_tags(metadata):
    """Extract tags from Twitter/X metadata including hashtags and username"""
    tags = []
    
    try:
        # Add username as a tag (remove @ symbol)
        if 'author' in metadata and isinstance(metadata['author'], dict):
            if 'name' in metadata['author'] and metadata['author']['name']:
                username = str(metadata['author']['name']).strip()
                if username:
                    # Clean username and add it
                    username_tag = username.lower().replace(' ', '_')
                    tags.append(f"user_{username_tag}")
        
        # Add hashtags from the tweet text
        if 'content' in metadata and metadata['content']:
            content = str(metadata['content'])
            # Find all hashtags in the content
            hashtags = re.findall(r'#(\w+)', content)
            for tag in hashtags:
                tags.append(tag.lower())
        
        # Also check description field
        if 'description' in metadata and metadata['description']:
            description = str(metadata['description'])
            hashtags = re.findall(r'#(\w+)', description)
            for tag in hashtags:
                tag_clean = tag.lower()
                if tag_clean not in tags:
                    tags.append(tag_clean)
        
        # Check for tweet text field (alternative field name)
        if 'tweet' in metadata and isinstance(metadata['tweet'], dict):
            if 'full_text' in metadata['tweet'] and metadata['tweet']['full_text']:
                tweet_text = str(metadata['tweet']['full_text'])
                hashtags = re.findall(r'#(\w+)', tweet_text)
                for tag in hashtags:
                    tag_clean = tag.lower()
                    if tag_clean not in tags:
                        tags.append(tag_clean)
        
        # Add a general twitter tag
        tags.append('twitter')
        
    except Exception as e:
        # Silent fail - just add twitter tag
        if 'twitter' not in tags:
            tags.append('twitter')
    
    return tags

def upload_file(filepath, metadata_path, silent=False, is_twitter=False):
    """Upload a single file to Szurubooru"""
    filename = filepath.name
    
    # Read metadata if available
    tags = []
    source = None
    safety = "safe"
    
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
                # Check if this is Twitter content
                if is_twitter or 'twitter' in str(metadata_path) or metadata.get('subcategory') == 'tweets':
                    # Extract Twitter-specific tags
                    tags = extract_twitter_tags(metadata)
                    
                    # Get source URL from Twitter metadata
                    if 'tweet_id' in metadata and 'author' in metadata:
                        username = metadata['author'].get('name', '').strip()
                        tweet_id = metadata['tweet_id']
                        source = f"https://twitter.com/{username}/status/{tweet_id}"
                    elif 'url' in metadata:
                        source = metadata['url']
                else:
                    # Standard booru tag extraction
                    if 'tags' in metadata:
                        if isinstance(metadata['tags'], list):
                            tags = metadata['tags']
                        elif isinstance(metadata['tags'], str):
                            tags = metadata['tags'].split()
                    elif 'tag_string' in metadata:
                        tags = metadata['tag_string'].split()
                    
                    # Get source URL
                    if 'source' in metadata:
                        source = metadata['source']
                    elif 'file_url' in metadata:
                        source = metadata['file_url']
                    
                    # Determine safety rating for booru content
                    rating = metadata.get('rating', 's')
                    if rating in ['e', 'explicit']:
                        safety = "unsafe"
                    elif rating in ['q', 'questionable']:
                        safety = "sketchy"
        except Exception as e:
            if not silent:
                print(f"Error reading metadata: {e}")
    
    # Upload file
    token = get_file_token(filepath)
    
    if not token:
        upload_stats['failed'] += 1
        if not silent:
            print(f"\nFailed to upload: {filename}")
        return False
    
    # Create post
    post = create_post(token, tags, safety, source)
    
    if post:
        upload_stats['uploaded'] += 1
        return True
    else:
        upload_stats['failed'] += 1
        if not silent:
            print(f"\nFailed to create post: {filename}")
        return False

def collect_files_to_upload(directory):
    """Collect all files that need to be uploaded"""
    files_to_upload = []
    
    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory):
            for filename in files:
                # Skip metadata files
                if filename.endswith('.json'):
                    continue
                
                filepath = Path(root) / filename
                metadata_path = filepath.with_suffix(filepath.suffix + '.json')
                
                # Check if this is Twitter content based on path
                is_twitter = 'twitter' in root.lower() or 'tweets' in root.lower()
                
                files_to_upload.append((filepath, metadata_path, is_twitter))
    
    return files_to_upload

def upload_all_files(directory, delay=0.5):
    """Upload all downloaded files with delay between uploads"""
    print("\n" + "="*50)
    print("Starting batch upload process...")
    print("="*50)
    
    # Collect all files
    files_to_upload = collect_files_to_upload(directory)
    upload_stats['total'] = len(files_to_upload)
    
    if upload_stats['total'] == 0:
        print("\nNo files found to upload!")
        return
    
    print(f"\nFound {upload_stats['total']} files to upload\n")
    
    # Upload each file with delay (silent mode - no individual error messages)
    for i, (filepath, metadata_path, is_twitter) in enumerate(files_to_upload):
        upload_file(filepath, metadata_path, silent=True, is_twitter=is_twitter)
        
        # Update progress bar
        print_progress_bar(i + 1, upload_stats['total'])
        
        # Add delay between uploads (except after the last one)
        if i < len(files_to_upload) - 1:
            time.sleep(delay)
    
    # Print final stats
    print("\n\n" + "="*50)
    print("Upload complete!")
    print(f"  Uploaded: {upload_stats['uploaded']}")
    print(f"  Failed: {upload_stats['failed']}")
    print(f"  Total: {upload_stats['total']}")
    print("="*50)

def build_url_from_tags(tags, site="rule34"):
    """Build a booru URL from tags"""
    tags_formatted = "+".join(tags.split())
    
    site_urls = {
        "rule34": f"https://rule34.xxx/index.php?page=post&s=list&tags={tags_formatted}",
        "danbooru": f"https://danbooru.donmai.us/posts?tags={tags_formatted}",
        "gelbooru": f"https://gelbooru.com/index.php?page=post&s=list&tags={tags_formatted}",
        "e621": f"https://e621.net/posts?tags={tags_formatted}",
        "safebooru": f"https://safebooru.org/index.php?page=post&s=list&tags={tags_formatted}"
    }
    
    return site_urls.get(site, site_urls["rule34"])

def build_twitter_url(search_query):
    """Build a Twitter/X URL from search query (supports @username and #hashtags)"""
    # Clean up the query
    query = search_query.strip()
    
    # Check if it's a username (starts with @)
    if query.startswith('@'):
        username = query[1:]  # Remove @ symbol
        return f"https://twitter.com/{username}"
    
    # Check if it's a hashtag search
    elif query.startswith('#'):
        hashtag = query[1:]  # Remove # symbol
        return f"https://twitter.com/hashtag/{hashtag}"
    
    # Check if it's a direct Twitter URL
    elif 'twitter.com' in query or 'x.com' in query:
        return query
    
    # Otherwise treat it as a username without @
    else:
        return f"https://twitter.com/{query}"

def download_from_booru(url, limit=None, download_dir=DOWNLOAD_DIR, write_metadata=True):
    """Download images using gallery-dl - OPTIMIZED VERSION"""
    print(f"Downloading from: {url}")
    print(f"Download directory: {download_dir}")
    print(f"Metadata: {'Enabled' if write_metadata else 'Disabled'}")
    
    # Reset stats
    upload_stats['uploaded'] = 0
    upload_stats['failed'] = 0
    upload_stats['total'] = 0
    
    # Check if this is a Twitter URL
    is_twitter = 'twitter.com' in url.lower() or 'x.com' in url.lower()
    
    # Setup gallery-dl config (check Twitter config if needed)
    setup_gallery_dl_config(check_twitter=is_twitter)
    
    # Create download directory
    os.makedirs(download_dir, exist_ok=True)
    
    # Build gallery-dl command - try direct executable first
    cmd = ["gallery-dl", "--destination", download_dir]
    
    # Add metadata flag if enabled
    if write_metadata:
        cmd.append("--write-metadata")
    
    if limit:
        cmd.extend(["--range", f"1-{limit}"])
    
    cmd.append(url)
    
    try:
        print("\nStarting download...")
        
        # Run with live output for better performance
        # gallery-dl handles its own progress display
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            # Count files only once after download completes
            file_count = len(collect_files_to_upload(download_dir))
            print(f"\nDownload complete! ({file_count} files total)\n")
            return True
        else:
            print(f"Error: gallery-dl exited with code {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        return False
    except FileNotFoundError:
        # gallery-dl not in PATH, try module approach
        print("Gallery-dl executable not found, trying Python module...")
        cmd = [sys.executable, "-m", "gallery_dl", "--destination", download_dir]
        
        if write_metadata:
            cmd.append("--write-metadata")
        
        if limit:
            cmd.extend(["--range", f"1-{limit}"])
        
        cmd.append(url)
        
        try:
            result = subprocess.run(cmd, check=False)
            
            if result.returncode == 0:
                file_count = len(collect_files_to_upload(download_dir))
                print(f"\nDownload complete! ({file_count} files total)\n")
                return True
            else:
                print(f"Error: gallery-dl exited with code {result.returncode}")
                return False
        except Exception as e:
            print(f"\nError during download: {e}")
            return False
    except Exception as e:
        print(f"\nError during download: {e}")
        return False

def main():
    print("Booru/Twitter to Szurubooru Uploader (Batch Upload)")
    print("="*50)
    
    # Ask for source type
    print("\nSelect source:")
    print("  1. Booru sites (Rule34, Danbooru, etc.)")
    print("  2. Twitter/X")
    source_type = input("Select source (1 or 2): ").strip()
    
    url = None
    
    if source_type == "2":
        # Twitter mode
        print("\n" + "="*50)
        print("Twitter/X Download Mode")
        print("="*50)
        print("\nYou can search by:")
        print("  - Username: @username or just username")
        print("  - Hashtag: #hashtag")
        print("  - Direct URL: https://twitter.com/username")
        
        twitter_query = input("\nEnter Twitter search (username/hashtag/URL): ").strip()
        url = build_twitter_url(twitter_query)
        print(f"\nGenerated URL: {url}")
        
        print("\n📝 Note: Gallery-dl will extract hashtags and username as tags")
        print("    Make sure you have Twitter cookies configured in gallery-dl")
        print("    See: https://github.com/mikf/gallery-dl#cookies\n")
        
    else:
        # Booru mode
        print("\nInput mode:")
        print("  1. Enter full URL")
        print("  2. Enter tags only")
        mode = input("Select mode (1 or 2): ").strip()
        
        if mode == "2":
            # Tag-based input
            print("\nAvailable sites:")
            print("  1. Rule34 (default)")
            print("  2. Danbooru")
            print("  3. Gelbooru")
            print("  4. e621")
            print("  5. Safebooru")
            site_choice = input("Select site (1-5, press Enter for Rule34): ").strip()
            
            site_map = {
                "1": "rule34",
                "2": "danbooru",
                "3": "gelbooru",
                "4": "e621",
                "5": "safebooru",
                "": "rule34"
            }
            site = site_map.get(site_choice, "rule34")
            
            tags = input("Enter tags (space-separated): ").strip()
            url = build_url_from_tags(tags, site)
            print(f"\nGenerated URL: {url}")
        else:
            # URL-based input
            url = input("Enter booru URL: ").strip()
    
    # Get download directory from user
    download_dir_input = input(f"\nEnter download directory (press Enter for default '{DOWNLOAD_DIR}'): ").strip()
    download_dir = download_dir_input if download_dir_input else DOWNLOAD_DIR
    
    # Optional: limit number of downloads
    limit_input = input("Limit number of downloads? (press Enter for no limit, or enter a number): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else None
    
    # Ask about metadata
    metadata_input = input("Download metadata JSON files? (y/n, default: y): ").strip().lower()
    write_metadata = metadata_input != 'n'
    
    # Ask about upload
    upload_input = input("Upload to Szurubooru after download? (y/n, default: y): ").strip().lower()
    should_upload = upload_input != 'n'
    
    # Download all files first
    if download_from_booru(url, limit, download_dir, write_metadata):
        if should_upload:
            # Then upload them all with 0.5 second delay
            upload_all_files(download_dir, delay=0.5)
        else:
            print("\nDownload complete! Skipping upload.")
    else:
        print("\nDownload failed.")

if __name__ == "__main__":
    main()
