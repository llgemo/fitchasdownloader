# 🖼️ Booru to Szurubooru Uploader (Batch)

A Python script that automates the process of downloading images from popular booru sites (like Rule34, Danbooru, etc.) and Twitter/X using the powerful `gallery-dl` tool, and then batch uploading them to a Szurubooru instance with automatic tag and source extraction.

## ✨ Features

* **Batch Download:** Uses `gallery-dl` to download multiple images from a given URL or tag search.
* **Booru Support:** Downloads from sites like Rule34, Danbooru, Gelbooru, e621, and Safebooru.
* **Twitter/X Support:** Downloads from user accounts, hashtags, or direct tweet links (requires user configuration).
* **Metadata Integration:** Automatically extracts tags, source URLs, and safety ratings from the downloaded booru metadata (`.json` files).
* **Szurubooru API Upload:** Uploads files and creates posts with extracted tags and safety ratings.
* **Interactive CLI:** Guides the user through the download and upload process with clear prompts.

## ⚙️ Requirements

1.  **Python 3.x**
2.  **Required Python Libraries:** `requests`, `pathlib`, `base64` (These are usually standard or easily installed via pip).
    ```bash
    pip install requests
    ```
3.  **gallery-dl:** This tool must be installed and accessible in your system's PATH.
    * [gallery-dl Installation Guide](https://github.com/mikf/gallery-dl#installation)

## 🔧 Setup & Configuration

Before running the script, you **must** configure your credentials inside the `booru_uploader.py` file.

Open `booru_uploader.py` and replace the placeholder values in the **Configuration** section:

```python
# Configuration (Placeholders - **USER MUST CONFIGURE**)
SZURU_URL = "[https://your-szurubooru-url.com](https://your-szurubooru-url.com)"  # Replace with your Szurubooru URL
SZURU_USER = "your_username"  # Replace with your Szurubooru username
SZURU_TOKEN = "your-api-token"  # Replace with your Szurubooru API Token
DOWNLOAD_DIR = "./booru_downloads" # Local directory for temporary downloads

# Rule34 API credentials (Placeholders - **USER MUST CONFIGURE**)
RULE34_API_KEY = "your-rule34-api-key"  # Replace with your Rule34 API Key
RULE34_USER_ID = "your-rule34-user-id"  # Replace with your Rule34 User ID
