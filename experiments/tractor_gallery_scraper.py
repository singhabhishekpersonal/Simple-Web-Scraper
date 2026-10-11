import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse
import hashlib

BASE_URL = "https://tractorgyan.com"
LISTING_URL = "https://tractorgyan.com/agricultural-machinery-images-library"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url, session=None, retries=2):
    if session is None:
        session = requests.Session()
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'html.parser')
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"Failed to fetch {url}: {e}")
                return None
    return None

def extract_tractor_entries(soup):
    """
    Extract tractor entries from the page.
    Each entry consists of an <img> tag followed by a text node that contains the caption.
    Returns list of dicts with keys: img_url, alt, caption.
    """
    entries = []
    images = soup.find_all('img')
    for img in images:
        src = img.get('src')
        if not src:
            continue
        # Make absolute URL
        img_url = urljoin(BASE_URL, src)
        # Skip icons, logos, etc.
        if any(x in img_url.lower() for x in ['logo', 'icon', 'banner', 'whatsapp', 'facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'playbutton', 'arrow']):
            continue
        # Only keep images from tractorgyan domain (optional)
        if 'tractorgyan.com' not in img_url:
            continue
        alt = img.get('alt', '')
        # Find caption: navigate forward siblings to find a text node that is not empty and not just whitespace.
        caption = ''
        for sibling in img.next_siblings:
            if isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    # Heuristic: if text looks like a caption (contains letters and maybe 'Tractor' or known types)
                    # We'll accept any non-empty text that is not just a single word like 'Tractor'?
                    # But we'll take the first non-empty text after the img.
                    caption = text
                    break
            else:
                # If we hit another tag, maybe it's the next img or a div, stop.
                # However, sometimes there might be <br> tags; we can skip them.
                if sibling.name in ['br']:
                    continue
                else:
                    # Stop at next tag that is not a br
                    break
        if caption:
            entries.append({
                'img_url': img_url,
                'alt': alt,
                'caption': caption
            })
    # Remove duplicates based on img_url
    seen = set()
    unique_entries = []
    for entry in entries:
        if entry['img_url'] not in seen:
            seen.add(entry['img_url'])
            unique_entries.append(entry)
    return unique_entries

def download_image(img_url, folder, session=None):
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(img_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'img_' + hashlib.md5(img_url.encode()).hexdigest() + '.jpg'
        filename = filename.replace('%20', '_')
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
        with open(path, 'wb') as f:
            f.write(resp.content)
        return path
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")
        return None

def main():
    os.makedirs('tractor_images', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    session = requests.Session()

    all_entries = []
    for page in range(1, 43):  # 1 to 42 inclusive
        print(f"\n=== Processing page {page} ===")
        if page == 1:
            page_url = LISTING_URL
        else:
            page_url = f"{LISTING_URL}?page={page}"
        soup = get_soup(page_url, session=session)
        if not soup:
            print(f"Failed to fetch page {page}")
            continue
        entries = extract_tractor_entries(soup)
        if not entries:
            print(f"No tractor entries found on page {page}")
            # If no entries, maybe we've reached the end? But continue just in case.
            # We'll break after 2 consecutive empty pages.
            pass
        print(f"Found {len(entries)} entries on page {page}")
        for i, entry in enumerate(entries):
            print(f"  [{i+1}/{len(entries)}] {entry['caption'][:60]}")
            # Download image
            if entry['img_url']:
                local_path = download_image(entry['img_url'], 'tractor_images', session=session)
                entry['local_image_path'] = local_path
            else:
                entry['local_image_path'] = None
            all_entries.append(entry)
            # Be respectful
            time.sleep(0.5)
        # Delay between pages
        time.sleep(2.0)

    # Save to JSON
    with open('data/tractor_gallery.json', 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_entries)} total entries to data/tractor_gallery.json")
    print(f"Images stored in tractor_images/")

if __name__ == '__main__':
    main()