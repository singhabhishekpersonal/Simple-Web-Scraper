import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse
import hashlib
import re

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

def extract_tractor_data(soup):
    """
    Extract tractor data from the page.
    Returns list of dicts with keys: img_url, alt, caption, brand, model, local_image_path.
    """
    data_list = []
    # Find all img tags where alt contains tractor (case-insensitive) and src is from tractorgyan
    imgs = soup.find_all('img', alt=re.compile(r'tractor', re.I))
    for img in imgs:
        src = img.get('src')
        if not src:
            continue
        img_url = urljoin(BASE_URL, src)
        # Skip icons, logos, etc.
        if any(x in img_url.lower() for x in ['logo', 'icon', 'banner', 'whatsapp', 'facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'playbutton', 'arrow']):
            continue
        # Only keep images from tractorgyan domain (should be true)
        if 'tractorgyan.com' not in img_url:
            continue
        alt = img.get('alt', '')
        # Find caption: the parent div's next sibling div (as observed)
        parent_div = img.find_parent('div')
        caption = ''
        if parent_div:
            # Find next sibling that is a div and contains text (the caption)
            for sib in parent_div.next_siblings:
                if sib.name == 'div':
                    text = sib.get_text(strip=True)
                    if text:
                        caption = text
                        break
                # If we encounter another div that is not the caption? We'll break after first div with text.
                elif sib.name is not None:
                    # Stop at any other tag (like another div that might be the next item)
                    # Actually the structure is: parent div (contains img), then sibling div (caption), then maybe another parent div for next item.
                    # So we break when we hit a div that has class indicating a new item? Simpler: break after first div with text.
                    if sib.name == 'div' and sib.get_text(strip=True):
                        # Already handled above
                        pass
                    else:
                        # If it's not a div, we might still want to continue? Let's break.
                        break
        # If we didn't find caption via parent_div, try to find the next sibling text directly after img (as seen in markdown)
        if not caption:
            for sib in img.next_siblings:
                if isinstance(sib, str):
                    text = sib.strip()
                    if text:
                        caption = text
                        break
                else:
                    # If we hit a tag, maybe it's a <br> or something; continue?
                    if sib.name == 'br':
                        continue
                    else:
                        # Stop at first non-br tag
                        break
        # If still no caption, fallback to alt
        if not caption:
            caption = alt
        # Try to extract brand and model from caption
        # Caption examples: "TractorSonalika DI 50 RX", "combine harvesterVishal 366 TDC", "rotavatorDasmesh 1072 Rotavator"
        # Pattern: [type][Brand Model] or [type][Brand] [Model]? Actually there's no space between type and brand.
        # We'll split by checking if caption starts with known types.
        brand = ''
        model = ''
        # Remove known prefixes
        prefix_patterns = [
            r'^Tractor',
            r'^combine harvester',
            r'^rotavator',
            r'^cultivator',
            r'^seed drill',
            r'^plough',
            r'^sprayer',
            r'^thresher',
            r'^harrow',
            r'^trailer',
            r'^loader',
            r'^backhoe',
            r'^excavator',
            r'^forklift',
        ]
        cleaned = caption
        for pat in prefix_patterns:
            if re.match(pat, cleaned, re.I):
                cleaned = re.sub(pat, '', cleaned, flags=re.I)
                break
        # Now cleaned should be something like "Sonalika DI 50 RX" or "Vishal 366 TDC"
        parts = cleaned.strip().split()
        if len(parts) >= 2:
            brand = parts[0]
            model = ' '.join(parts[1:])
        elif len(parts) == 1:
            brand = parts[0]
            model = ''
        else:
            brand = ''
            model = ''
        data_list.append({
            'img_url': img_url,
            'alt': alt,
            'caption': caption,
            'brand': brand,
            'model': model,
            'local_image_path': None  # to be filled after download
        })
    # Remove duplicates by img_url
    seen = set()
    unique = []
    for d in data_list:
        if d['img_url'] not in seen:
            seen.add(d['img_url'])
            unique.append(d)
    return unique

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
        # Ensure filename is not too long
        if len(filename) > 200:
            filename = hashlib.md5(img_url.encode()).hexdigest() + os.path.splitext(filename)[1]
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
    all_data = []
    page = 1
    while True:
        print(f"\n=== Processing page {page} ===")
        if page == 1:
            page_url = LISTING_URL
        else:
            page_url = f"{LISTING_URL}?page={page}"
        soup = get_soup(page_url, session=session)
        if not soup:
            print(f"Failed to fetch page {page}")
            break
        data = extract_tractor_data(soup)
        if not data:
            print(f"No tractor data found on page {page}")
            # If no data, maybe we've reached the end? But continue a bit more.
            # We'll break after 2 consecutive empty pages.
            pass
        print(f"Found {len(data)} tractors on page {page}")
        for i, entry in enumerate(data):
            print(f"  [{i+1}/{len(data)}] {entry['caption'][:50]}")
            # Download image
            if entry['img_url']:
                local_path = download_image(entry['img_url'], 'tractor_images', session=session)
                entry['local_image_path'] = local_path
            else:
                entry['local_image_path'] = None
            all_data.append(entry)
            # Be respectful
            time.sleep(0.5)
        # Check for next page
        next_link = soup.find('a', string=lambda t: t and 'Next' in t)
        if not next_link:
            # Also check for pagination text
            if not soup.find(string=lambda t: t and f'Page {page} of' in t):
                print("No next page indicator found, stopping.")
                break
        page += 1
        if page > 50:  # safety break
            print("Reached safety page limit.")
            break
        # Delay between pages
        time.sleep(2.0)

    # Save to JSON
    with open('data/tractor_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_data)} total tractors to data/tractor_dataset.json")
    print(f"Images stored in tractor_images/")

if __name__ == '__main__':
    main()