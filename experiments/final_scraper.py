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
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'html.parser')
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"Failed to fetch {url}: {e}")
                return None
    return None

def extract_tractor_links(soup):
    links = set()
    # Find all <a> tags that contain an <img> and have href starting with /tractor/
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/tractor/') and not href.endswith('/'):
            # Check if this a contains an img
            if a.find('img'):
                full_url = urljoin(BASE_URL, href)
                links.add(full_url)
    # Also find <img> tags, get parent <a> if exists
    for img in soup.find_all('img'):
        parent = img.find_parent('a')
        if parent and parent.get('href'):
            href = parent['href']
            if href.startswith('/tractor/') and not href.endswith('/'):
                full_url = urljoin(BASE_URL, href)
                links.add(full_url)
    return list(links)

def parse_detail_page(soup, url):
    data = {
        'url': url,
        'brand': '',
        'model': '',
        'price': '',
        'specifications': {},
        'description': '',
        'image_urls': []
    }
    # Title from h1
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        # Sometimes title includes extra words like "Tractor" or "Price" etc.
        # We'll try to split and take first two words as brand and model?
        # But better: look for pattern in alt text of images?
        # We'll just keep the whole title and later try to parse.
        parts = title.split()
        if len(parts) >= 2:
            data['brand'] = parts[0]
            data['model'] = ' '.join(parts[1:])
        else:
            data['model'] = title
    # Price: look for text containing ₹
    price_elem = soup.find(string=lambda t: t and '₹' in t)
    if price_elem:
        data['price'] = price_elem.strip()
    # Specifications: find a section with heading containing Specification
    spec_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Specification' in tag.get_text(strip=True))
    if spec_heading:
        # Get the next element that could contain a table/list/div
        spec_container = spec_heading.find_next(['table','ul','ol','div'])
        if spec_container:
            if spec_container.name == 'table':
                rows = spec_container.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td','th'])
                    if len(cols) >= 2:
                        key = cols[0].get_text(strip=True)
                        val = cols[1].get_text(strip=True)
                        if key and val:
                            data['specifications'][key] = val
            elif spec_container.name in ['ul','ol']:
                items = spec_container.find_all('li')
                for item in items:
                    txt = item.get_text(strip=True)
                    if ':' in txt:
                        key, val = txt.split(':',1)
                        data['specifications'][key.strip()] = val.strip()
            else:
                # div or other: get text and split by lines
                txt = spec_container.get_text(separator='\n', strip=True)
                for line in txt.split('\n'):
                    if ':' in line:
                        key, val = line.split(':',1)
                        data['specifications'][key.strip()] = val.strip()
    # Description: find heading with Description
    desc_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Description' in tag.get_text(strip=True))
    if desc_heading:
        desc_container = desc_heading.find_next(['div','p'])
        if desc_container:
            data['description'] = desc_container.get_text(strip=True)
    # Images: collect all img src from the page
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            src = urljoin(url, src)
            # Skip icons, logos, etc.
            if any(x in src.lower() for x in ['logo','icon','banner','whatsapp','facebook','twitter','instagram','linkedin','youtube','playbutton','arrow']):
                continue
            # Only keep images from tractorgyan domain (optional)
            if 'tractorgyan.com' in src:
                data['image_urls'].append(src)
    # Deduplicate
    data['image_urls'] = list(dict.fromkeys(data['image_urls']))
    return data

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

    print("Fetching listing page...")
    soup = get_soup(LISTING_URL, session=session)
    if not soup:
        print("Failed to fetch listing page")
        return

    tractor_links = extract_tractor_links(soup)
    print(f"Found {len(tractor_links)} tractor links")

    all_tractors = []
    for i, link in enumerate(tractor_links):
        print(f"[{i+1}/{len(tractor_links)}] Processing {link}")
        detail_soup = get_soup(link, session=session)
        if not detail_soup:
            print("  -> Failed to fetch detail page")
            continue
        data = parse_detail_page(detail_soup, link)
        # Download images (limit to first 5 to save time/bandwidth)
        if data['image_urls']:
            local_images = []
            for img_url in data['image_urls'][:5]:
                local_path = download_image(img_url, 'tractor_images', session=session)
                if local_path:
                    local_images.append(local_path)
            data['local_image_paths'] = local_images
        else:
            data['local_image_paths'] = []
        all_tractors.append(data)
        # Be respectful
        time.sleep(1.5)

    # Save to JSON
    with open('data/tractors.json', 'w', encoding='utf-8') as f:
        json.dump(all_tractors, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_tractors)} tractors to data/tractors.json")
    print(f"Images in tractor_images/")

if __name__ == '__main__':
    main()