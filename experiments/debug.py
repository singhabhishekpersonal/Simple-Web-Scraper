import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

# Find all img tags
imgs = soup.find_all('img')
print(f"Total img tags: {len(imgs)}")
for i, img in enumerate(imgs[:10]):
    src = img.get('src', '')
    alt = img.get('alt', '')
    print(f"Img {i}: src={src[:80] if src else None}, alt={alt}")
    # Check parent and siblings
    parent = img.parent
    print(f"  Parent tag: {parent.name if parent else None}")
    # Next siblings
    for sib in img.next_siblings:
        if isinstance(sib, str):
            text = sib.strip()
            if text:
                print(f"  Next sibling text: {text[:50]}")
                break
        else:
            # If it's a tag, maybe we want its text?
            if sib.name:
                text = sib.get_text(strip=True)
                if text:
                    print(f"  Next sibling tag {sib.name}: {text[:50]}")
                    break
    print()