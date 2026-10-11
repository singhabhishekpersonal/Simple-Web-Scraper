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
    """Extract links to individual tractor detail pages from listing page."""
    links = set()
    # Find all <a> tags with href containing /tractor/
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Make absolute
        full_url = urljoin(BASE_URL, href)
        # We want links that look like tractor detail pages: usually have a numeric ID at the end
        # e.g., /tractor/swaraj-855-fe/23
        # Also brand pages like /tractor/Vst-shakti (no numeric ID) may also be useful but less detailed.
        # We'll collect both, but later we can prioritize those with IDs.
        if href.startswith('/tractor/') and not href.endswith('/'):
            # Exclude obvious non-tractor links like /tractor-brands, /tractors, etc.
            if '/tractor-brands' in href or '/tractors' in href or '/latest-tractors' in href:
                continue
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
    # Try to get brand and model from breadcrumbs or title
    # Breadcrumbs often contain: Home > Tractor Brands > Brand > Model
    breadcrumb = soup.find('nav', attrs={'aria-label': 'breadcrumb'})
    if not breadcrumb:
        # Sometimes breadcrumbs are in a div with class
        breadcrumb = soup.find(class_=re.compile(r'breadcrumb', re.I))
    if breadcrumb:
        items = breadcrumb.find_all(['li', 'a', 'span'])
        texts = [item.get_text(strip=True) for item in items if item.get_text(strip=True)]
        # Filter out 'Home', 'Tractor Brands', 'Tractors', etc.
        # We want the last two non-generic items
        generic = {'Home', 'Tractor Brands', 'Tractors', 'Implements', 'All Tractor', 'Latest Tractor', 'Popular Tractors'}
        filtered = [t for t in texts if t not in generic and t]
        if len(filtered) >= 2:
            data['brand'] = filtered[-2]
            data['model'] = filtered[-1]
        elif len(filtered) == 1:
            data['model'] = filtered[0]
            # Try to extract brand from model text? Not reliable.
    # If still not set, try from h1
    if not data['brand'] and not data['model']:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            # Sometimes title is like "Brand Model" or "Model - Brand"
            parts = title.split()
            if len(parts) >= 2:
                data['brand'] = parts[0]
                data['model'] = ' '.join(parts[1:])
            else:
                data['model'] = title
    # Price: look for text containing ₹ or "Price"
    price_elem = soup.find(string=lambda t: t and ('₹' in t or 'Price' in t))
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
    # Images: collect all img src from the page that look like tractor images
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            src = urljoin(url, src)
            # Skip icons, logos, etc.
            if any(x in src.lower() for x in ['logo','icon','banner','whatsapp','facebook','twitter','instagram','linkedin','youtube','playbutton','arrow','search','menu','checkbox','radio','star']):
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
    
    # Load existing data to avoid re-scraping
    existing_file = 'data/tractors.json'
    existing_urls = set()
    if os.path.exists(existing_file):
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                for item in existing_data:
                    if 'url' in item:
                        existing_urls.add(item['url'])
            print(f"Loaded {len(existing_urls)} existing records.")
        except Exception as e:
            print(f"Could not load existing data: {e}")
    
    session = requests.Session()
    all_tractors = []
    
    # We'll scrape up to 42 pages, but stop early if no new links found on a page
    for page in range(1, 43):
        if page == 1:
            page_url = LISTING_URL
        else:
            page_url = f"{LISTING_URL}?page={page}"
        print(f"\n=== Processing page {page} ===")
        soup = get_soup(page_url, session=session)
        if not soup:
            print(f"Failed to fetch page {page}")
            break
        links = extract_tractor_links(soup)
        if not links:
            print(f"No tractor links found on page {page}")
            # Maybe we reached the end
            break
        print(f"Found {len(links)} tractor links on page {page}")
        new_links = [link for link in links if link not in existing_urls]
        print(f"New links to process: {len(new_links)}")
        if not new_links:
            print("All links on this page already scraped. Assuming we are up to date.")
            # Continue to next page in case there are new links further? But if pagination is chronological, we can break.
            # We'll continue for safety.
        for i, link in enumerate(new_links):
            print(f"  [{i+1}/{len(new_links)}] Processing {link}")
            detail_soup = get_soup(link, session=session)
            if not detail_soup:
                print(f"    Failed to fetch detail page")
                continue
            data = parse_detail_page(detail_soup, link)
            # Download images (limit to first 3 to save time/bandwidth)
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
            existing_urls.add(link)  # avoid re-downloading in same run
            # Be respectful
            time.sleep(1.5)
        # Delay between pages
        time.sleep(2.0)
    
    # Combine with existing data
    if os.path.exists(existing_file):
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            # Avoid duplicates by URL
            existing_dict = {item['url']: item for item in existing_data if 'url' in item}
            for item in all_tractors:
                existing_dict[item['url']] = item
            combined = list(existing_dict.values())
            print(f"Total after merging: {len(combined)}")
        except Exception as e:
            print(f"Error merging existing data: {e}")
            combined = all_tractors
    else:
        combined = all_tractors
    
    # Save to JSON
    with open(existing_file, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(combined)} tractors to {existing_file}")
    print(f"Images stored in tractor_images/")

if __name__ == '__main__':
    main()