import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

img = soup.find('img', alt=re.compile(r'Sonalika DI 50 RX tractor', re.I))
if img:
    parent = img.parent
    grandparent = parent.parent
    print("Grandparent tag:", grandparent.name)
    print("All attributes of grandparent:")
    for key, val in grandparent.attrs.items():
        print(f"  {key}: {val}")
    # Check if there's a data-href or similar
    # Also check if the grandparent has an onclick or data-url
    # Let's also look at the great-grandparent
    great = grandparent.parent
    print("\nGreat-grandparent tag:", great.name)
    print("All attributes of great-grandparent:")
    for key, val in great.attrs.items():
        print(f"  {key}: {val}")
    # Let's see if there's a pattern: maybe the grandparent's parent has a data-href?
    # Or maybe we need to look for an <a> that wraps the grandparent?
    # Actually, looking at the classes: 'group', 'cursor-pointer' - this suggests the grandparent is clickable
    # In Tailwind CSS, 'group' is often used with 'group-hover' etc.
    # The actual link might be implemented via JavaScript on click.
    # But for scraping, we need to find where the URL is stored.
    # Let's check if there's a data-href attribute anywhere in the ancestors.
    print("\nChecking ancestors for data-href or data-url:")
    ancestor = img
    for i in range(10):
        ancestor = ancestor.parent
        if ancestor is None:
            break
        for key, val in ancestor.attrs.items():
            if 'href' in key.lower() or 'url' in key.lower():
                print(f"  Level {i+1} ({ancestor.name}): {key} = {val}")
    # Also check for data-* attributes that might contain a path
    print("\nChecking for data-* attributes:")
    ancestor = img
    for i in range(10):
        ancestor = ancestor.parent
        if ancestor is None:
            break
        for key, val in ancestor.attrs.items():
            if key.startswith('data-'):
                print(f"  Level {i+1} ({ancestor.name}): {key} = {val}")
else:
    print("Img not found")