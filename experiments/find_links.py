import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

# Find all <a> tags
links = soup.find_all('a', href=True)
print(f"Found {len(links)} <a> tags with href")

# Filter for those that might be tractor links
tractor_links = []
for a in links:
    href = a['href']
    if href.startswith('/tractor/') and not href.endswith('/'):
        # Check if this <a> contains an img
        if a.find('img'):
            tractor_links.append((href, a.get_text(strip=True)[:50]))
        else:
            # Maybe the img is inside a div inside the a?
            if a.find(lambda tag: tag.name in ['div', 'img'] and tag.find('img')):
                tractor_links.append((href, a.get_text(strip=True)[:50]))

print(f"\nFound {len(tractor_links)} tractor-related <a> tags with img:")
for href, text in tractor_links[:20]:
    print(f"  {href} -> {text}")

# Also let's look for any <a> that contains text like "Sonalika" or "DI 50 RX"
print("\nLooking for <a> tags containing model text:")
for a in links:
    text = a.get_text(strip=True)
    if 'Sonalika' in text and 'DI 50' in text:
        print(f"  Found: {a['href']} -> {text[:100]}")