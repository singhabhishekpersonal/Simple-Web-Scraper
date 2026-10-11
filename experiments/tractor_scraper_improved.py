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

def get_soup(url, session=None, retries=3):
    """Fetch URL and return BeautifulSoup object with retries."""
    if session is None:
        session = requests.Session()
    for attempt in range(retries):
        try:
            print(f"Fetching {url} (attempt {attempt+1})")
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
            else:
                return None
    return None

def extract_tractor_links(soup):
    """Extract all tractor detail links from listing page."""
    links = set()
    # Find all <a> tags with href containing '/tractor/'
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/tractor/') and not href.endswith('/'):
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)
    # Also find <a> that contain <img>
    for a in soup.find_all('a'):
        if a.find('img'):
            href = a.get('href')
            if href and href.startswith('/tractor/'):
                full_url = urljoin(BASE_URL, href)
                links.add(full_url)
    return list(links)

def parse_detail_page(soup, url):
    """Parse tractor detail page and return dict of data."""
    data = {
        'url': url,
        'brand': '',
        'model': '',
        'price': '',
        'specifications': {},
        'description': '',
        'image_urls': []
    }
    # Extract title from h1 or similar
    title_tag = soup.find('h1')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Assuming format like "Brand Model" or similar
        parts = title.split()
        if len(parts) >= 2:
            data['brand'] = parts[0]
            data['model'] = ' '.join(parts[1:])
        else:
            data['model'] = title
    # Extract price if available
    price_tag = soup.find(string=lambda text: text and '₹' in text)
    if price_tag:
        data['price'] = price_tag.strip()
    # Extract specifications from a table or list
    # Look for section with heading containing Specification
    spec_section = soup.find(lambda tag: tag.name in ['section', 'div', 'h2', 'h3', 'h4'] and
                             tag.get_text(strip=True) and 'Specification' in tag.get_text(strip=True))
    if spec_section:
        # Find next table or list
        spec_table = spec_section.find_next(['table', 'ul', 'ol', 'div'])
        if spec_table:
            if spec_table.name == 'table':
                rows = spec_table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        key = cols[0].get_text(strip=True)
                        val = cols[1].get_text(strip=True)
                        if key and val:
                            data['specifications'][key] = val
            elif spec_table.name in ['ul', 'ol']:
                items = spec_table.find_all('li')
                for item in items:
                    text = item.get_text(strip=True)
                    if ':' in text:
                        key, val = text.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        if key and val:
                            data['specifications'][key] = val
            else:
                # Assume div with paragraphs or spans
                text = spec_table.get_text(separator='\n', strip=True)
                for line in text.split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        if key and val:
                            data['specifications'][key] = val
    # Extract description
    desc_section = soup.find(lambda tag: tag.name in ['section', 'div', 'h2', 'h3', 'h4'] and
                             tag.get_text(strip=True) and 'Description' in tag.get_text(strip=True))
    if desc_section:
        desc_div = desc_section.find_next(['div', 'p'])
        if desc_div:
            data['description'] = desc_div.get_text(strip=True)
    # Extract all images
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Make absolute
            src = urljoin(url, src)
            # Filter out icons, logos, etc.
            if any(x in src.lower() for x in ['logo', 'icon', 'banner', 'whatsapp', 'facebook', 'twitter', 'instagram', 'linkedin', 'youtube']):
                continue
            # Ensure it's from tractorgyan domain (optional)
            if 'tractorgyan.com' in src:
                data['image_urls'].append(src)
    # Deduplicate
    data['image_urls'] = list(dict.fromkeys(data['image_urls']))
    return data

def download_image(img_url, folder, session=None):
    """Download image to folder, return local path."""
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(img_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        # Extract filename from URL
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'image_' + hashlib.md5(img_url.encode()).hexdigest() + '.jpg'
        # Ensure filename is safe
        filename = filename.replace('%20', '_')
        local_path = os.path.join(folder, filename)
        # Avoid re-downloading if exists
        if os.path.exists(local_path):
            return local_path
        with open(local_path, 'wb') as f:
            f.write(resp.content)
        return local_path
    except Exception as e:
        print(f"Failed to download image {img_url}: {e}")
        return None

def main():
    # Create output directories
    os.makedirs('tractor_images', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    session = requests.Session()
    all_tractors = []
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
        links = extract_tractor_links(soup)
        if not links:
            print(f"No tractor links found on page {page}")
            break
        print(f"Found {len(links)} tractor links on page {page}")
        for i, link in enumerate(links):
            print(f"  [{i+1}/{len(links)}] Processing {link}")
            detail_soup = get_soup(link, session=session)
            if not detail_soup:
                print(f"    Failed to fetch detail page")
                continue
            data = parse_detail_page(detail_soup, link)
            # Download images (optional: limit to first 3 to save time)
            # Uncomment below to download all images; but we'll download all for completeness.
            # To speed up, we can download only the first image.
            if data['image_urls']:
                local_images = []
                for img_url in data['image_urls']:  # download all
                    local_path = download_image(img_url, 'tractor_images', session=session)
                    if local_path:
                        local_images.append(local_path)
                data['local_image_paths'] = local_images
            else:
                data['local_image_paths'] = []
            all_tractors.append(data)
            # Be respectful: delay between tractor requests
            time.sleep(1.0)
        # Check for next page
        next_link = soup.find('a', string=lambda t: t and 'Next' in t)
        if not next_link:
            # Also check for pagination text
            if not soup.find(string=lambda t: t and f'Page {page} of' in t):
                print("No next page indicator found, stopping.")
                break
        page += 1
        # Safety break
        if page > 100:
            print("Reached safety page limit.")
            break
        # Delay between pages
        time.sleep(2.0)
    # Save data to JSON
    with open('data/tractors.json', 'w', encoding='utf-8') as f:
        json.dump(all_tractors, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_tractors)} tractors to data/tractors.json")
    print(f"Images stored in tractor_images/")

if __name__ == '__main__':
    main()