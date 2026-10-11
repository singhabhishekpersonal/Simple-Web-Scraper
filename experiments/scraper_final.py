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

def extract_brand_links(soup):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/tractor/') and not href.endswith('/'):
            if a.find('img'):
                full_url = urljoin(BASE_URL, href)
                links.append(full_url)
    for img in soup.find_all('img'):
        parent = img.find_parent('a')
        if parent and parent.get('href'):
            href = parent['href']
            if href.startswith('/tractor/') and not href.endswith('/'):
                full_url = urljoin(BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
    return links

def extract_model_links_from_brand(soup, brand_url):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if re.match(r'^/tractor/[^/]+/\d+$', href):
            full_url = urljoin(BASE_URL, href)
            links.append(full_url)
    for img in soup.find_all('img'):
        parent = img.find_parent('a')
        if parent and parent.get('href'):
            href = parent['href']
            if re.match(r'^/tractor/[^/]+/\d+$', href):
                full_url = urljoin(BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
    return links

def extract_tractor_data(soup, url):
    data = {
        'url': url,
        'title': '',
        'brand': '',
        'model': '',
        'price': '',
        'specifications': {},
        'description': '',
        'image_urls': []
    }
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        data['title'] = title
        parts = title.split()
        if len(parts) >= 2:
            data['brand'] = parts[0]
            data['model'] = ' '.join(parts[1:])
        else:
            data['model'] = title
    price_elem = soup.find(string=lambda t: t and '₹' in t)
    if price_elem:
        data['price'] = price_elem.strip()
    spec_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Specification' in tag.get_text(strip=True))
    if spec_heading:
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
                txt = spec_container.get_text(separator='\n', strip=True)
                for line in txt.split('\n'):
                    if ':' in line:
                        key, val = line.split(':',1)
                        data['specifications'][key.strip()] = val.strip()
    desc_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Description' in tag.get_text(strip=True))
    if desc_heading:
        desc_container = desc_heading.find_next(['div','p'])
        if desc_container:
            data['description'] = desc_container.get_text(strip=True)
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            src = urljoin(url, src)
            if any(x in src.lower() for x in ['logo','icon','banner','whatsapp','facebook','twitter','instagram','linkedin','youtube','playbutton','arrow','button']):
                continue
            if 'tractorgyan.com' in src:
                data['image_urls'].append(src)
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
    print("Fetching listing page...")
    soup = get_soup(LISTING_URL, session=session)
    if not soup:
        print("Failed to fetch listing page")
        return
    brand_links = extract_brand_links(soup)
    print(f"Found {len(brand_links)} brand links")
    all_tractors = []
    for i, brand_url in enumerate(brand_links):
        print(f"\n[{i+1}/{len(brand_links)}] Processing brand: {brand_url}")
        brand_soup = get_soup(brand_url, session=session)
        if not brand_soup:
            print("  -> Failed to fetch brand page")
            continue
        model_links = extract_model_links_from_brand(brand_soup, brand_url)
        print(f"  Found {len(model_links)} model links")
        for j, model_url in enumerate(model_links):
            print(f"    [{j+1}/{len(model_links)}] Processing model: {model_url}")
            model_soup = get_soup(model_url, session=session)
            if not model_soup:
                print("      -> Failed to fetch model page")
                continue
            data = extract_tractor_data(model_soup, model_url)
            if data['image_urls']:
                local_images = []
                for img_url in data['image_urls'][:3]:
                    local_path = download_image(img_url, 'tractor_images', session=session)
                    if local_path:
                        local_images.append(local_path)
                data['local_image_paths'] = local_images
            else:
                data['local_image_paths'] = []
            all_tractors.append(data)
            time.sleep(1.0)
        time.sleep(2.0)
    with open('data/tractor_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(all_tractors, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_tractors)} total tractors to data/tractor_dataset.json")
    print(f"Images stored in tractor_images/")

if __name__ == '__main__':
    main()