#!/usr/bin/env python3
"""Generate one X post about Mupler and publish it.

Run modes:
    python scripts/post.py --dry-run     generate only, publish nothing, log nothing
    python scripts/post.py --no-image    publish text only
    python scripts/post.py               full run: generate, upload image, post, log

Required environment variables:
    GEMINI_API_KEY
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
Optional:
    GEMINI_MODEL   (default: gemini-2.5-flash)
"""

import argparse
import datetime as dt
import json
import mimetypes
import os
import random
import re
import sys
from pathlib import Path

import requests
from requests_oauthlib import OAuth1

ROOT = Path(__file__).resolve().parent.parent
BRIEF_PATH = ROOT / "content" / "brief.json"
TOPICS_PATH = ROOT / "content" / "topics.json"
LOG_PATH = ROOT / "log.json"
IMAGES_DIR = ROOT / "images"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# Post shapes. The generator rotates through these so the timeline does not
# read like the same sentence rewritten twenty times.
FORMATS = [
    ("question", "Open with a question the reader will silently answer 'yes' to, then land the point."),
    ("fact", "State one concrete, checkable fact about immigration intake, then its consequence."),
    ("mini_story", "Two or three sentences of a recognizable scene from a practice. No named people."),
    ("advice", "One actionable tip an attorney could apply this week, whether or not they buy anything."),
    ("pain_point", "Name the frustration plainly and precisely. Do not resolve it in the first sentence."),
    ("benefit", "Describe the after state: what the workflow looks like once intake stops leaking time."),
    ("contrast", "Before versus after, or the old way versus the current way. Keep both halves short."),
    ("observation", "A short opinionated take on how immigration intake actually works in small firms."),
]

MIN_LEN, MAX_LEN, HARD_LIMIT = 150, 275, 280


# --------------------------------------------------------------------------- io


def load_json(path, default=None):
    if not path.exists():
        if default is None:
            sys.exit(f"missing required file: {path}")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_log(log):
    LOG_PATH.write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------- planning


def pick_topic(topics, log):
    """Least recently used topic, so the full list cycles before anything repeats."""
    used_at = {}
    for i, entry in enumerate(log["posts"]):
        used_at[entry.get("topic")] = i

    unused = [t for t in topics if t["id"] not in used_at]
    if unused:
        return random.choice(unused)
    return min(topics, key=lambda t: used_at[t["id"]])


def pick_format(log):
    counts = {name: 0 for name, _ in FORMATS}
    for entry in log["posts"][-len(FORMATS) :]:
        if entry.get("format") in counts:
            counts[entry["format"]] += 1

    previous = log["posts"][-1].get("format") if log["posts"] else None
    candidates = [f for f in FORMATS if f[0] != previous] or list(FORMATS)
    fewest = min(counts[f[0]] for f in candidates)
    return random.choice([f for f in candidates if counts[f[0]] == fewest])


def pick_image(log):
    if not IMAGES_DIR.is_dir():
        return None
    images = sorted(p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        return None
    return images[log.get("image_cursor", 0) % len(images)]


# -------------------------------------------------------------- generation


def build_prompt(brief, topic, fmt_name, fmt_hint, recent_texts):
    p = brief["product"]
    voice = brief["voice"]
    cta = random.choice(brief["cta_variants"])

    recent_block = (
        "\n".join(f"- {t}" for t in recent_texts)
        if recent_texts
        else "(none yet, this is the first post)"
    )

    return f"""You write posts on X for {p['name']} ({p['url']}).

PRODUCT
{p['one_liner']}
{p['positioning']}
Audience: {p['audience']}

RELEVANT PAINS
{chr(10).join('- ' + s for s in brief['pains'])}

RELEVANT CAPABILITIES
{chr(10).join('- ' + s for s in brief['features'])}

PROOF POINTS YOU MAY USE
{chr(10).join('- ' + s for s in brief['proof_points'])}

TOPIC FOR THIS POST
{topic['angle']}

REQUIRED FORMAT: {fmt_name}
{fmt_hint}

TONE
{voice['tone']}
Do: {' '.join(voice['do'])}
Do not: {' '.join(voice['dont'])}

ALREADY POSTED, DO NOT REPEAT THESE OPENINGS, PHRASINGS OR ANGLES
{recent_block}

RULES
- Between {MIN_LEN} and {MAX_LEN} characters total, including any link. Hard maximum {HARD_LIMIT}.
- Plain text only. No markdown, no quotation marks around the post, no preamble.
- Line breaks are allowed and encouraged for readability.
- {"End with this call to action, verbatim: " + cta if cta else "Do not include a call to action or a link in this one."}
- Never give legal advice. Never claim anything about USCIS decisions or timelines.

Output only the post text, nothing else."""


def clean(text):
    text = text.strip()
    if len(text) > 1 and text[0] in "\"'“" and text[-1] in "\"'”":
        text = text[1:-1].strip()
    text = re.sub(r"^(post|tweet)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"[*_`#]", "", text)              # stray markdown
    text = re.sub(r"\s*[—–]\s*", ", ", text)        # dashes the model slipped in
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)    # space before punctuation
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate(prompt, api_key, model):
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.1,
                "topP": 0.95,
                "maxOutputTokens": 1024,
                # Without this, 2.5 models spend the token budget on reasoning
                # and can return an empty candidate.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        timeout=90,
    )
    if not resp.ok:
        raise RuntimeError(f"Gemini {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini returned no usable candidate: {json.dumps(data)[:500]}")
    return clean("".join(part.get("text", "") for part in parts))


def generate_with_retry(prompt, api_key, model, attempts=4):
    last = ""
    for i in range(attempts):
        text = generate(prompt, api_key, model)
        last = text
        if MIN_LEN <= len(text) <= HARD_LIMIT:
            return text
        print(f"  attempt {i + 1}: {len(text)} chars, out of range, retrying")
    if len(last) > HARD_LIMIT:
        trimmed = last[:HARD_LIMIT].rsplit(" ", 1)[0].rstrip(" ,.;:")
        print(f"  trimming {len(last)} -> {len(trimmed)} chars")
        return trimmed
    raise RuntimeError(f"could not produce a usable post after {attempts} attempts")


# ------------------------------------------------------------------- x api


def x_auth():
    missing = [
        k
        for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
        if not os.environ.get(k)
    ]
    if missing:
        sys.exit("missing X credentials: " + ", ".join(missing))
    return OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def upload_media(path, auth):
    """Upload an image and return its media id.

    Tries the v2 endpoint first, then falls back to v1.1. Free-tier access to
    these two has moved around more than once, so we try both before failing.
    """
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    blob = path.read_bytes()

    endpoints = [
        ("v2", "https://api.x.com/2/media/upload"),
        ("v1.1", "https://upload.twitter.com/1.1/media/upload.json"),
    ]
    errors = []
    for label, url in endpoints:
        resp = requests.post(
            url, auth=auth, files={"media": (path.name, blob, mime)}, timeout=120
        )
        if resp.ok:
            body = resp.json()
            media_id = body.get("data", {}).get("id") or body.get("media_id_string")
            if media_id:
                print(f"  media uploaded via {label}: {media_id}")
                return str(media_id)
            errors.append(f"{label}: 200 but no media id in {json.dumps(body)[:200]}")
        else:
            errors.append(f"{label}: {resp.status_code} {resp.text[:200]}")

    raise RuntimeError("media upload failed.\n  " + "\n  ".join(errors))


def create_tweet(text, media_id, auth):
    payload = {"text": text}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

    resp = requests.post(
        "https://api.x.com/2/tweets", auth=auth, json=payload, timeout=60
    )
    if not resp.ok:
        raise RuntimeError(f"POST /2/tweets {resp.status_code}: {resp.text[:500]}")
    return resp.json()["data"]["id"]


# -------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="generate only, publish nothing")
    ap.add_argument("--no-image", action="store_true", help="publish without an image")
    args = ap.parse_args()

    brief = load_json(BRIEF_PATH)
    topics = load_json(TOPICS_PATH)
    log = load_json(LOG_PATH, {"image_cursor": 0, "posts": []})
    log.setdefault("image_cursor", 0)
    log.setdefault("posts", [])

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        sys.exit("missing GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    topic = pick_topic(topics, log)
    fmt_name, fmt_hint = pick_format(log)
    recent = [entry["text"] for entry in log["posts"][-10:]]

    print(f"topic:  {topic['id']}")
    print(f"format: {fmt_name}")

    text = generate_with_retry(
        build_prompt(brief, topic, fmt_name, fmt_hint, recent), gemini_key, model
    )

    image = None if args.no_image else pick_image(log)
    print(f"image:  {image.name if image else 'none'}")
    print(f"\n--- {len(text)} chars ---\n{text}\n---------------------\n")

    if args.dry_run:
        print("dry run, nothing published, log untouched")
        return

    auth = x_auth()
    media_id = upload_media(image, auth) if image else None
    tweet_id = create_tweet(text, media_id, auth)
    print(f"published: https://x.com/i/web/status/{tweet_id}")

    log["posts"].append(
        {
            "date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "topic": topic["id"],
            "format": fmt_name,
            "image": image.name if image else None,
            "text": text,
            "tweet_id": tweet_id,
        }
    )
    if image:
        log["image_cursor"] += 1
    save_log(log)
    print(f"logged, {len(log['posts'])} posts total")


if __name__ == "__main__":
    main()
