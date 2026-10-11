import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse

BASE_URL = "https://tractorgyan.com"
LISTING_URL = "https://tractorgyan.com/agricultural-machinery-images-library"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    """Fetch URL and return BeautifulSoup object."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_tractor_links(soup):
    """Extract all tractor detail links from listing page."""
    links = []
    # Find all <a> tags with href containing '/tractor/'
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/tractor/') and not href.endswith('/'):  # avoid category links
            full_url = urljoin(BASE_URL, href)
            links.append(full_url)
    # Also maybe images are wrapped in <a>? We'll also find <a> that contain <img>
    for a in soup.find_all('a'):
        if a.find('img'):
            href = a.get('href')
            if href and href.startswith('/tractor/'):
                full_url = urljoin(BASE_URL, href)
                if full_url not in links:
                    links.append(full_url)
    return links

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
    spec_section = soup.find('section', string=lambda t: t and 'Specification' in t)
    if spec_section:
        # Find next table or list
        spec_table = spec_section.find_next('table')
        if spec_table:
            rows = spec_table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    if key and val:
                        data['specifications'][key] = val
    # Extract description
    desc_section = soup.find('section', string=lambda t: t and 'Description' in t)
    if desc_section:
        desc_div = desc_section.find_next('div')
        if desc_div:
            data['description'] = desc_div.get_text(strip=True)
    # Extract all images
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and ('tractorgyan.com' in src or src.startswith('http')):
            # Avoid icons, logos, etc.
            if any(x in src.lower() for x in ['logo', 'icon', 'banner', 'whatsapp', 'facebook']):
                continue
            data['image_urls'].append(src)
    return data

def download_image(img_url, folder):
    """Download image to folder, return local path."""
    try:
        resp = requests.get(img_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        # Extract filename from URL
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'image_' + str(hash(img_url)) + '.jpg'
        # Ensure filename is safe
        filename = filename.replace('%20', '_')
        local_path = os.path.join(folder, filename)
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

    all_tractors = []
    page = 1
    while True:
        print(f"Processing page {page}")
        if page == 1:
            page_url = LISTING_URL
        else:
            page_url = f"{LISTING_URL}?page={page}"
        soup = get_soup(page_url)
        if not soup:
            break
        links = extract_tractor_links(soup)
        if not links:
            print(f"No tractor links found on page {page}")
            break
        print(f"Found {len(links)} tractor links on page {page}")
        for link in links:
            print(f"  Processing {link}")
            detail_soup = get_soup(link)
            if not detail_soup:
                continue
            data = parse_detail_page(detail_soup, link)
            # Download images
            if data['image_urls']:
                local_images = []
                for img_url in data['image_urls']:
                    local_path = download_image(img_url, 'tractor_images')
                    if local_path:
                        local_images.append(local_path)
                data['local_image_paths'] = local_images
            all_tractors.append(data)
            time.sleep(0.5)  # be respectful
        # Check if there is a next page
        next_link = soup.find('a', string=lambda t: t and 'Next' in t)
        if not next_link:
            # Also check for pagination text
            if soup.find(string=lambda t: t and f'Page {page} of' in t):
                # We'll infer next page by incrementing until no links
                pass
            else:
                break
        page += 1
        if page > 50:  # safety break
            break
    # Save data to JSON
    with open('data/tractors.json', 'w', encoding='utf-8') as f:
        json.dump(all_tractors, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_tractors)} tractors to data/tractors.json")

if __name__ == '__main__':
    main()