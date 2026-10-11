import requests
from bs4 import BeautifulSoup
import re

url = "https://tractorgyan.com/agricultural-machinery-images-library"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

# Find the img with alt containing Sonalika DI 50 RX tractor
img = soup.find('img', alt=re.compile(r'Sonalika DI 50 RX tractor', re.I))
if img:
    print("Found img:")
    print("  alt:", img.get('alt'))
    print("  src:", img.get('src'))
    print("\nParent:")
    parent = img.parent
    print("  tag:", parent.name)
    print("  classes:", parent.get('class'))
    print("  parent's parent:", parent.parent.name if parent.parent else None)
    print("  parent's parent's classes:", parent.parent.get('class') if parent.parent else None)
    # Let's go up a few levels
    print("\nAncestors:")
    anc = img
    for i in range(5):
        anc = anc.parent
        if anc is None:
            break
        print(f"  Level {i+1}: {anc.name} classes={anc.get('class')}")
    # Now check siblings of img
    print("\nNext siblings of img:")
    for sib in img.next_siblings:
        if isinstance(sib, str):
            if sib.strip():
                print(f"  Text: {sib.strip()[:100]}")
        else:
            print(f"  Tag: {sib.name} classes={sib.get('class')}")
            # break after first tag sibling
            break
    # Check siblings of parent
    print("\nNext siblings of parent:")
    for sib in parent.next_siblings:
        if isinstance(sib, str):
            if sib.strip():
                print(f"  Text: {sib.strip()[:100]}")
        else:
            print(f"  Tag: {sib.name} classes={sib.get('class')}")
            break
    # Check if there is a link wrapping the parent or the img's parent's parent
    print("\nChecking for <a> ancestors:")
    a = img.find_parent('a')
    if a:
        print(f"Found parent <a>: href={a.get('href')}")
    else:
        print("No parent <a> found.")
    # Check for <a> around the caption? The caption is likely a sibling div.
    # Let's find the caption div: next sibling div of parent with text.
    caption_div = None
    for sib in parent.next_siblings:
        if sib.name == 'div':
            text = sib.get_text(strip=True)
            if text:
                caption_div = sib
                break
    if caption_div:
        print("\nCaption div:")
        print("  text:", caption_div.get_text(strip=True)[:100])
        print("  classes:", caption_div.get('class'))
        # Check if caption div is inside an <a>
        a_caption = caption_div.find_parent('a')
        if a_caption:
            print(f"  Parent <a>: href={a_caption.get('href')}")
        else:
            print("  No parent <a>.")
else:
    print("Img not found")