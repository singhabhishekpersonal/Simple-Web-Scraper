# Agricultural Equipment Dataset Engine

A resilient web scraper that turns a paginated agricultural-equipment catalogue into a
**structured JSON dataset plus a labelled image corpus** — the kind of input you need before
you can train anything on agricultural imagery.

The reason it exists: there is no clean, downloadable dataset of tractors and implements with
consistent labels. So this builds one.

---

## What it produces

```json
{
  "url": "https://tractorgyan.com/tractor/swaraj-744-fe/141",
  "brand": "Swaraj",
  "model": "744 FE",
  "price": "...",
  "specifications": { "Engine": "...", "HP": "48", "...": "..." },
  "description": "...",
  "image_urls": ["..."],
  "local_image_paths": ["tractor_images/..."]
}
```

Plus downloaded equipment photographs on disk, ready for a classification pipeline.

A 3-record sample is committed at [`data/tractors.sample.json`](data/tractors.sample.json)
so the output shape is visible without running anything.

---

## Why this isn't just a `requests` loop

Naive scrapers break on the first hiccup and leave you with a half-populated dataset. This one
is built to survive a long run:

| Concern | How it's handled |
|---------|------------------|
| **Network reuse** | A single `requests.Session` across every page — connection pooling and keep-alive instead of a fresh TLS handshake per request |
| **Transient failures** | Exponential backoff (`2 ** attempt` seconds) with `raise_for_status()`, so 5xx and connection resets are retried instead of silently producing empty records |
| **Interruptions** | Reads `data/tractors.json` on startup and skips URLs already scraped — rerun and it picks up where it stopped |
| **Page exhaustion** | Stops cleanly when a listing page yields no model links, rather than hammering 404s |
| **Rate limiting** | 1.5 s between detail pages, 2.0 s between listing pages |
| **Timeouts** | Explicit 15 s (pages) and 20 s (images) so one dead socket can't hang the run |
| **Image noise** | Filters out logos, icons, banners, and social-media assets by URL substring; dedupes while preserving order |
| **No filenames** | Falls back to a content-addressed `md5` filename when the URL has no usable basename |

---

## Field extraction

Brand and model are recovered from the **breadcrumb trail**, not by guessing — with a
hardcoded stop-list for generic nodes (`Home`, `Tractor Brands`, `Latest Tractor`, …). If the
breadcrumb is absent or too short, it falls back to the `<h1>`, stripping trailing
`Price` / `Specifications` / `Reviews` / `Overview` words before splitting into brand + model.

Specifications are parsed from whichever structure the page uses: a `<table>` (key/value
`<tr>` pairs), a `<ul>`/`<ol>` (lines split on `:`), or a nested `<div>` (newline-separated,
split on `:`). One code path handles all three.

Model links are discovered with a regex anchored on the URL shape:

```python
re.match(r'^/tractor/[^/]+/\d+$', href)
```

which matches detail pages (`/tractor/swaraj-855-fe/23`) while ignoring category and index
pages.

---

## Usage

```bash
git clone https://github.com/singhabhishekpersonal/Simple-Web-Scraper.git
cd Simple-Web-Scraper

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate

pip install -r requirements.txt

python scraper.py
```

Writes:

- `data/tractors.json` — the merged dataset
- `tractor_images/` — downloaded equipment photographs

Both are git-ignored; re-running resumes incrementally rather than starting over.

Tune at the top of `scraper.py`:

```python
BASE_URL          = "https://tractorgyan.com"
LISTING_URL_BASE  = f"{BASE_URL}/agricultural-machinery-images-library"
for page in range(1, 43):     # page cap
time.sleep(1.5)               # delay between detail pages
time.sleep(2.0)               # delay between listing pages
```

---

## Project layout

```
Simple-Web-Scraper/
├── scraper.py                   # the scraper (production version)
├── data/
│   └── tractors.sample.json     # 3-record sample of the output shape
└── experiments/                 # earlier iterations, kept for reference
    ├── tractor_scraper.py       #   first attempt
    ├── simple_scraper.py
    ├── tractor_scraper_improved.py
    ├── scraper_fixed.py
    ├── scraper_final.py
    ├── final_scraper.py
    ├── scraper_models.py
    ├── complete_scraper.py
    ├── tractor_dataset.py
    ├── tractor_gallery_scraper.py
    ├── test_scraper.py
    ├── test_run.py
    ├── find_links.py
    ├── examine.py / examine2.py / examine3.py    # DOM inspection
    └── debug.py / debug2.py / debug3.py
```

`experiments/` is the honest record of how this got here: nineteen iterations of reading a
page's DOM, guessing wrong, and fixing. `scraper.py` is the version that survived. They're
kept because the failed approaches document *why* the final parser is shaped the way it is.

---

## Data source & responsible use

Scrapes **tractorgyan.com**, a public agricultural equipment reference site.

This repo is an educational exercise in HTML parsing and dataset construction. Before running
it against any site, confirm you are permitted to:

- check `robots.txt` for the paths you are hitting,
- read the site's Terms of Service,
- keep request rates low enough not to degrade the service for others,
- attribute the source, and not redistribute copyrighted images as your own.

The full scraped dataset and downloaded images are **not** committed here — the content is
third-party, and only a small sample is included to show the output format.

---

## Known limitations

- The price field is scraped as raw text and contains an encoding-dependent rupee glyph; it is
  **not** normalised to a number. Parsing it into a numeric field is the obvious next step.
- `specifications` is frequently empty — many pages render specs lazily, after the initial
  HTML. A headless-browser renderer (Playwright) would be needed to capture those reliably.
- HTML selectors are inherently brittle. This scraper is written to fail loudly and resume,
  not to survive a full redesign of the target site.
- Only the first 3 image URLs per model are downloaded, as a deliberate size/rate tradeoff.

---

## License

MIT — see [LICENSE](LICENSE). Scraped content belongs to its original owners and is not
distributed by this repository.