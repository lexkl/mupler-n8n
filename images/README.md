# Images

The posting script sorts this folder by filename and rotates through it, one
image per post. If the folder is empty, posts still go out, just without media.

Supported: `.png` `.jpg` `.jpeg` `.webp` `.gif`. Keep each file under 5 MB.

## The generated cards

The 12 PNGs here are built from [`../content/cards.json`](../content/cards.json)
by [`../scripts/make_images.py`](../scripts/make_images.py). To change the lines,
add cards, or restyle:

```bash
pip install -r requirements-images.txt
python scripts/make_images.py
```

Then commit the PNGs. The Actions workflow never runs the generator, it only
reads what is committed.

Output is 1600x900, the 16:9 ratio X shows uncropped for a single image. Colours
are sampled from mupler.com: sage `#6A815C`, cream `#FDF2E7`, pale sage
`#E4EAD1`, sand `#CD945B`. Backgrounds cycle through three themes so a run of
posts does not look like one long block.

The site uses Inter. If Inter is installed the cards use it; otherwise the
generator falls back to Segoe UI, Arial, or DejaVu, and prints which one it
picked. Installing Inter from [rsms.me/inter](https://rsms.me/inter/) makes the
cards match the site exactly.

## What to add beyond text cards

Text cards are the reliable floor, not the ceiling. These do better:

- Product screenshots: the client-facing form, the theme picker, a generated PDF
  next to the web form it came from.
- Before/after: a page of raw USCIS PDF beside the Mupler version of the same
  question.
- Simple flow diagrams: client link, filled form, exported PDF.

Avoid stock photos of handshakes and gavels, and avoid AI-generated art. This
audience reads it as a signal that nobody was home.
