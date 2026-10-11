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
    print("Grandparent attributes:", grandparent.attrs)
    # Check for data-href, data-url, etc.
    for key, val in grandparent.attrs.items():
        if 'href' in key.lower() or 'url' in key.lower() or 'link' in key.lower() or 'data' in key.lower():
            print(f"  {key}: {val}")
    # Also check great-grandparent
    great = grandparent.parent
    print("\nGreat-grandparent tag:", great.name if great else None)
    if great:
        print("Great-grandparent attributes:", great.attrs)
        for key, val in great.attrs.items():
            if 'href' in key.lower() or 'url' in key.lower() or 'link' in key.lower() or 'data' in key.lower():
                print(f"  {key}: {val}")
    # Let's also look at the parent's parent's parent's parent maybe
    # But first, let's see if there is an <a> anywhere nearby by searching for <a> that contains this img
    a_ancestor = img.find_parent('a')
    print("\nAny parent <a>:", a_ancestor)
    if a_ancestor:
        print("  href:", a_ancestor.get('href'))
    # Search for <a> that contains the grandparent
    a_ancestor2 = grandparent.find_parent('a')
    print("Parent grandparent <a>:", a_ancestor2)
    if a_ancestor2:
        print("  href:", a_ancestor2.get('href'))
    # Let's look at the siblings of grandparent maybe
    print("\nGrandparent's next siblings:")
    for sib in grandparent.next_siblings:
        if isinstance(sib, str):
            if sib.strip():
                print(f"  Text: {sib.strip()[:50]}")
        else:
            print(f"  Tag: {sib.name} classes={sib.get('class')}")
            break
    # Let's look at the grandparent's previous siblings
    print("\nGrandparent's previous siblings:")
    for sib in grandparent.previous_siblings:
        if isinstance(sib, str):
            if sib.strip():
                print(f"  Text: {sib.strip()[:50]}")
        else:
            print(f"  Tag: {sib.name} classes={sib.get('class')}")
            break
else:
    print("Img not found")