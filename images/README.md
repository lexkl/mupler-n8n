# Images

Supported: `.png` `.jpg` `.jpeg` `.webp` `.gif`. Keep each file under 5 MB.

## How an image gets chosen

**Filename decides.** A file named after a topic id from
[`../content/topics.json`](../content/topics.json) — `i864-stall.png` — is that
topic's card, and is used only on posts about it. Any other filename is generic
and rotates in order across topics that have no card of their own.

So a post about the Affidavit of Support cannot end up carrying the encryption
card. If a topic has no card and there are no generic images, the post goes out
as text rather than with something unrelated.

Rename a card and you break its pairing. Drop in `screenshot-client-form.png`
and it joins the generic rotation.

## The generated cards

All 24 topics have a card, built from
[`../content/cards.json`](../content/cards.json) by
[`../scripts/make_images.py`](../scripts/make_images.py). Card `id` must match a
topic `id`; the generator refuses to run otherwise and lists any topic left
without a card. To change the lines, add cards, or restyle:

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

Name those after a topic id to pin them to that topic, or give them any other
name to put them in the generic rotation.

Avoid stock photos of handshakes and gavels, and avoid AI-generated art. This
audience reads it as a signal that nobody was home.
