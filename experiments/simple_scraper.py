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
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_tractor_entries(soup):
    """Extract tractor entries from the listing page.
    Each entry is an <a> tag containing an <img> and text like 'TractorBrand Model'
    """
    entries = []
    # Find all <a> tags that contain an <img>
    for a in soup.find_all('a'):
        img = a.find('img')
        if img and img.get('src'):
            href = a.get('href')
            if not href:
                continue
            full_url = urljoin(BASE_URL, href)
            # Get the text after the img, which is like 'TractorBrand Model'
            # The img is inside the a, so we can get the a's text and remove the img's alt?
            # Actually the structure is: <a> <img ...> ... </a> TractorBrand Model
            # But the text after the img is outside the a? Let's look at the HTML from earlier:
            # <a href="/tractor/..."><img …>…</a> Tractor[Brand Model]
            # So the text is after the </a>? Actually the markdown showed:
            # ![Sonalika DI 50 RX tractor](...)
            # TractorSonalika DI 50 RX
            # That suggests the <a> contains only the <img>, and the text is outside the <a>.
            # Let's get the next sibling text.
            # We'll instead look for the pattern: <a>...<img...></a> followed by text.
            # We'll find all <a> with img, then get the next sibling.
            next_sibling = a.next_sibling
            # Navigate until we find a non-empty string that is not a tag.
            text = ""
            while next_sibling:
                if isinstance(next_sibling, str):
                    text += next_sibling
                elif next_sibling.name and next_sibling.name in ['br']:
                    # break at br?
                    pass
                else:
                    # If it's a tag, we might want its text too.
                    text += next_sibling.get_text()
                next_sibling = next_sibling.next_sibling
            text = text.strip()
            # The text often starts with 'Tractor' or the type like 'combine harvester'
            # We'll keep it as is.
            entries.append({
                'url': full_url,
                'img_url': urljoin(BASE_URL, img.get('src')),
                'img_alt': img.get('alt', ''),
                'text': text,
                'raw_html': str(a) + (str(next_sibling) if next_sibling else '')
            })
    return entries

def parse_detail_page(soup, url):
    """Parse detail page for more info."""
    data = {
        'url': url,
        'brand': '',
        'model': '',
        'price': '',
        'specifications': {},
        'description': '',
        'image_urls': []
    }
    # Title
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        parts = title.split()
        if len(parts) >= 2:
            data['brand'] = parts[0]
            data['model'] = ' '.join(parts[1:])
        else:
            data['model'] = title
    # Price
    price_tag = soup.find(string=lambda t: t and '₹' in t)
    if price_tag:
        data['price'] = price_tag.strip()
    # Specifications: look for a section with heading containing Specification
    spec_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Specification' in tag.get_text(strip=True))
    if spec_heading:
        # Get the next element that might contain a table or list
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
                # div: get text and split by newlines
                txt = spec_container.get_text(separator='\n', strip=True)
                for line in txt.split('\n'):
                    if ':' in line:
                        key, val = line.split(':',1)
                        data['specifications'][key.strip()] = val.strip()
    # Description
    desc_heading = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','h5','h6','section','div'] and
                             tag.get_text(strip=True) and 'Description' in tag.get_text(strip=True))
    if desc_heading:
        desc_container = desc_heading.find_next(['div','p'])
        if desc_container:
            data['description'] = desc_container.get_text(strip=True)
    # Images
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            src = urljoin(url, src)
            # filter out icons/logos
            if any(x in src.lower() for x in ['logo','icon','banner','whatsapp','facebook','twitter','instagram','linkedin','youtube']):
                continue
            if 'tractorgyan.com' in src:
                data['image_urls'].append(src)
    data['image_urls'] = list(dict.fromkeys(data['image_urls']))
    return data

def download_image(img_url, folder, session=None):
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(img_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = 'img_' + str(hash(img_url)) + '.jpg'
        filename = filename.replace('%20','_')
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

    # Get listing page
    print("Fetching listing page...")
    soup = get_soup(LISTING_URL)
    if not soup:
        print("Failed to fetch listing page")
        return

    entries = extract_tractor_entries(soup)
    print(f"Found {len(entries)} tractor entries on listing page")

    all_tractors = []
    for i, entry in enumerate(entries):
        print(f"Processing {i+1}/{len(entries)}: {entry['text'][:50]}")
        # Download the listing image
        if entry['img_url']:
            local_img = download_image(entry['img_url'], 'tractor_images', session=session)
            entry['local_image_path'] = local_img
        else:
            entry['local_image_path'] = None

        # Optionally fetch detail page for more info (but limit to avoid too many requests)
        # We'll fetch detail page for every tractor but with a timeout and maybe skip if fails.
        detail_soup = get_soup(entry['url'])
        if detail_soup:
            detail_data = parse_detail_page(detail_soup, entry['url'])
            # Merge detail data into entry, but keep the listing info
            combined = {**entry, **detail_data}
            # Avoid overwriting listing-specific fields
            combined['listing_text'] = entry['text']
            combined['listing_img_url'] = entry['img_url']
            combined['listing_url'] = entry['url']
            all_tractors.append(combined)
        else:
            # If detail page fails, still keep listing info
            entry['detail_failed'] = True
            all_tractors.append(entry)

        # Be respectful
        time.sleep(1.0)

    # Save to JSON
    with open('data/tractors.json', 'w', encoding='utf-8') as f:
        json.dump(all_tractors, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_tractors)} tractors to data/tractors.json")

if __name__ == '__main__':
    main()