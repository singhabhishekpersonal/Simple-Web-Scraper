import requests
from bs4 import BeautifulSoup
import re
import time

BASE_URL = "https://tractorgyan.com"
LISTING_URL = "https://tractorgyan.com/agricultural-machinery-images-library"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_tractor_data(soup):
    data_list = []
    imgs = soup.find_all('img', alt=re.compile(r'tractor', re.I))
    for img in imgs:
        src = img.get('src')
        if not src:
            continue
        img_url = src if src.startswith('http') else BASE_URL + src
        alt = img.get('alt', '')
        # Find caption: parent div's next sibling div
        parent_div = img.find_parent('div')
        caption = ''
        if parent_div:
            for sib in parent_div.next_siblings:
                if sib.name == 'div':
                    text = sib.get_text(strip=True)
                    if text:
                        caption = text
                        break
        if not caption:
            for sib in img.next_siblings:
                if isinstance(sib, str):
                    text = sib.strip()
                    if text:
                        caption = text
                        break
                else:
                    if sib.name == 'br':
                        continue
                    else:
                        break
        if not caption:
            caption = alt
        print(f"Found: alt={alt[:30]}, caption={caption[:50]}")
        data_list.append({
            'img_url': img_url,
            'alt': alt,
            'caption': caption
        })
    # deduplicate
    seen = set()
    unique = []
    for d in data_list:
        if d['img_url'] not in seen:
            seen.add(d['img_url'])
            unique.append(d)
    return unique

for page in range(1, 3):
    print(f"\n--- Page {page} ---")
    if page == 1:
        url = LISTING_URL
    else:
        url = f"{LISTING_URL}?page={page}"
    soup = get_soup(url)
    if not soup:
        print("Failed to get soup")
        continue
    data = extract_tractor_data(soup)
    print(f"Found {len(data)} items")
    time.sleep(2)