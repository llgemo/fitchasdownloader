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
# =====================================================================
# SENSITIVE DATA REPLACED WITH PLACEHOLDERS
SZURU_URL = "https://your.szurubooru.url"  # Placeholder URL
SZURU_USER = "your_username"  # Placeholder Username
SZURU_TOKEN = "your-api-token-placeholder-0000-0000-000000000000"  # Placeholder Token
DOWNLOAD_DIR = "./booru_downloads"

# Rule34 API credentials
RULE34_API_KEY = "placeholder_rule34_api_key_0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"  # Placeholder API Key
RULE34_USER_ID = "0000000"  # Placeholder User ID
# =====================================================================

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

def collect
