#!/usr/bin/env python3
"""
Booru to Szurubooru Uploader (Batch upload version)
Downloads images from booru sites using gallery-dl and uploads them to Szurubooru after downloads complete
"""

import json
import os
import subprocess
import requests
from pathlib import Path
import time
import base64
import sys

# Configuration
SZURU_URL = "https://lboorus.lmms.wtf"
SZURU_USER = "bossdawg"
SZURU_TOKEN = "396ec236-80b6-4232-861e-39d613db3ffc"
DOWNLOAD_DIR = "./booru_downloads"

# Rule34 API credentials
RULE34_API_KEY = "de27807b669f210b834cfa99a8b2846bf2805a1d07d29d0c708a008c4b0d998e64350ad922a3448207c04e592a8e352f4d60c211cfa396cebc387373eae3518a"
RULE34_USER_ID = "5346603"

# Szurubooru API headers
auth_string = f"{SZURU_USER}:{SZURU_TOKEN}"
auth_token = base64.b64encode(auth_string.encode()).decode('ascii')

headers = {
    "Authorization": f"Token {auth_token}",
    "Accept": "application/json"
}

# Track upload stats
upload_stats = {"uploaded": 0, "failed": 0, "total": 0}

def setup_gallery_dl_config():
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
    
    # Add Rule34 credentials
    if "extractor" not in config:
        config["extractor"] = {}
    if "rule34" not in config["extractor"]:
        config["extractor"]["rule34"] = {}
    
    config["extractor"]["rule34"]["api-key"] = RULE34_API_KEY
    config["extractor"]["rule34"]["user-id"] = RULE34_USER_ID
    
    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Gallery-dl config updated")

def print_progress_bar(current, total, bar_length=40):
    """Print a progress bar"""
    percent = float(current) / total
    arrow = '█' * int(round(percent * bar_length))
    spaces = '░' * (bar_length - len(arrow))
    
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

def upload_file(filepath, metadata_path):
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
                
                # Extract tags
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
                
                # Determine safety rating
                rating = metadata.get('rating', 's')
                if rating in ['e', 'explicit']:
                    safety = "unsafe"
                elif rating in ['q', 'questionable']:
                    safety = "sketchy"
        except Exception as e:
            pass
    
    # Upload file
    token = get_file_token(filepath)
    
    if not token:
        upload_stats['failed'] += 1
        print(f"\n✗ Failed to upload: {filename}")
        return False
    
    # Create post
    post = create_post(token, tags, safety, source)
    
    if post:
        upload_stats['uploaded'] += 1
        return True
    else:
        upload_stats['failed'] += 1
        print(f"\n✗ Failed to create post: {filename}")
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
                files_to_upload.append((filepath, metadata_path))
    
    return files_to_upload

def upload_all_files(directory, delay=0.5):
    """Upload all downloaded files with delay between uploads"""
    print("\n" + "="*50)
    print("📦 Starting batch upload process...")
    print("="*50)
    
    # Collect all files
    files_to_upload = collect_files_to_upload(directory)
    upload_stats['total'] = len(files_to_upload)
    
    if upload_stats['total'] == 0:
        print("\n⚠️  No files found to upload!")
        return
    
    print(f"\nFound {upload_stats['total']} files to upload\n")
    
    # Upload each file with delay
    for i, (filepath, metadata_path) in enumerate(files_to_upload):
        upload_file(filepath, metadata_path)
        
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

def download_from_booru(url, limit=None, download_dir=DOWNLOAD_DIR, write_metadata=True):
    """Download images using gallery-dl"""
    print(f"Downloading from: {url}")
    print(f"Download directory: {download_dir}")
    print(f"Metadata: {'Enabled' if write_metadata else 'Disabled'}")
    
    # Reset stats
    upload_stats['uploaded'] = 0
    upload_stats['failed'] = 0
    upload_stats['total'] = 0
    
    # Setup gallery-dl config
    setup_gallery_dl_config()
    
    # Create download directory
    os.makedirs(download_dir, exist_ok=True)
    
    # gallery-dl command
    cmd = [
        sys.executable, "-m", "gallery_dl",
        "--destination", download_dir,
        url
    ]
    
    # Add metadata flag if enabled
    if write_metadata:
        cmd.insert(3, "--write-metadata")
    
    if limit:
        cmd.extend(["--range", f"1-{limit}"])
    
    try:
        print("\n⬇️  Starting download...")
        
        # Start the download process
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Show a spinner while downloading
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        
        while process.poll() is None:
            # Count files downloaded so far
            file_count = len(collect_files_to_upload(download_dir))
            sys.stdout.write(f'\r{spinner[i % len(spinner)]} Downloading... ({file_count} files so far)')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        
        # Clear the spinner line
        sys.stdout.write('\r' + ' ' * 50 + '\r')
        sys.stdout.flush()
        
        if process.returncode == 0:
            file_count = len(collect_files_to_upload(download_dir))
            print(f"✓ Download complete! ({file_count} files downloaded)\n")
            return True
        else:
            print(f"Error: gallery-dl exited with code {process.returncode}")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user!")
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        return False

def main():
    print("Booru to Szurubooru Uploader (Batch Upload)")
    print("="*50)
    
    # Ask for input mode
    print("\nInput mode:")
    print("  1. Enter full URL")
    print("  2. Enter tags only")
    mode = input("Select mode (1 or 2): ").strip()
    
    url = None
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
            print("\n✓ Download complete! Skipping upload.")
    else:
        print("\n⚠️  Download failed.")

if __name__ == "__main__":
    main()
