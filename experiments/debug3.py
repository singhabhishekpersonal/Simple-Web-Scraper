import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

# Find one img with alt containing tractor
img = soup.find('img', alt=re.compile(r'tractor', re.I))
if img:
    print("Img alt:", img.get('alt'))
    print("Img src:", img.get('src'))
    print("\nParent:", img.parent.name, img.parent.get('class'))
    print("Parent's parent:", img.parent.parent.name, img.parent.parent.get('class'))
    print("Parent's parent's parent:", img.parent.parent.parent.name if img.parent.parent.parent else None)
    # Let's see the siblings of the parent
    print("\nParent's siblings:")
    for sib in img.parent.next_siblings:
        if isinstance(sib, str):
            if sib.strip():
                print("  Text sibling:", sib.strip()[:50])
        else:
            print("  Tag sibling:", sib.name, sib.get('class') if hasattr(sib, 'get') else None)
            # break after first tag sibling
            break
    # Also check if the parent is inside an <a>
    a_parent = img.find_parent('a')
    if a_parent:
        print("\nFound parent <a>: href=", a_parent.get('href'))
    else:
        print("\nNo parent <a> found.")
    # Let's look at the next sibling div (the caption)
    caption_div = img.find_next_sibling('div')
    if caption_div:
        print("\nCaption div:", caption_div.get_text(strip=True))
        print("Caption div classes:", caption_div.get('class'))
        # Check if caption div is inside an <a>
        a_caption = caption_div.find_parent('a')
        if a_caption:
            print("Caption's parent <a>: href=", a_caption.get('href'))
        else:
            print("Caption has no parent <a>")
else:
    print("No img found")