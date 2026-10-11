import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

# Find all img tags with alt containing tractor (case-insensitive)
imgs = soup.find_all('img', alt=re.compile(r'tractor', re.I))
print(f"Img tags with 'tractor' in alt: {len(imgs)}")
for i, img in enumerate(imgs[:20]):
    src = img.get('src', '')
    alt = img.get('alt', '')
    print(f"Img {i}: alt={alt}")
    print(f"  src={src[:100] if src else None}")
    # Check parent and siblings
    parent = img.parent
    print(f"  Parent tag: {parent.name if parent else None} (class={parent.get('class') if parent else None})")
    # Next siblings
    for sib in img.next_siblings:
        if isinstance(sib, str):
            text = sib.strip()
            if text:
                print(f"  Next sibling text: {text[:100]}")
                break
        else:
            if sib.name:
                text = sib.get_text(strip=True)
                if text:
                    print(f"  Next sibling tag {sib.name}: {text[:100]}")
                    break
    print()