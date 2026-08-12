# mupler-x-bot

Posts about [Mupler](https://mupler.com/) to X on a schedule. Runs entirely on
GitHub Actions — no server, no hosting bill.

Mon / Wed / Fri at 14:00 UTC, one post: Gemini writes the text from a brief in
this repo, an image is picked from `images/` in rotation, both go to X, and the
result is appended to `log.json` so the next post does not repeat itself.

```
.github/workflows/post.yml   schedule + manual trigger
scripts/post.py              the whole thing
content/brief.json           product facts, pains, tone of voice
content/topics.json          24 topics, cycled least-recently-used
images/                      your images, rotated one per post
log.json                     every post published, feeds the anti-repeat prompt
```

## Cost

Free. GitHub Actions gives 2000 minutes/month on private repos and this uses
about one minute per month. Gemini and X both run on their free tiers, well
under the limits at 13 posts/month (X free tier allows 500).

---

## Setup

### 1. Gemini API key

Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey), sign in
with a Google account, create an API key. Free tier, no card.

### 2. X developer account

**Start this first — it is the only step with a wait.**

1. [developer.x.com](https://developer.x.com/) → sign up for the Free tier.
2. Create a Project and an App inside it.
3. In the App's **User authentication settings**, set App permissions to
   **Read and Write**. Type of App: *Web App, Automated App or Bot*. Callback
   URL can be `https://mupler.com/` — it is unused but the form requires one.
4. **Keys and tokens** tab → generate all four:
   - API Key and API Key Secret
   - Access Token and Access Token Secret

   If you generated the access token *before* switching permissions to Read and
   Write, regenerate it. Otherwise it stays read-only and posting fails with 403.

### 3. Repository secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `GEMINI_API_KEY` | from step 1 |
| `X_API_KEY` | API Key |
| `X_API_SECRET` | API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |
| `GH_PAT` | optional, see below |

**`GH_PAT`** — GitHub disables scheduled workflows in repos with no activity for
60 days. Commits made by the built-in token do not reset that clock; commits
authenticated with a personal access token do. Create a fine-grained PAT with
**Contents: Read and write** on this repo only, and add it as `GH_PAT`. Without
it everything still works, you will just get a "workflow disabled" email
eventually and have to click re-enable.

### 4. Images

Drop 10–15 files into `images/` — see [images/README.md](images/README.md) for
what works. Posts go out without media if the folder is empty.

### 5. Test before going live

Repo → Actions → **Post to X** → Run workflow, leave **dry run** checked.
Nothing publishes; the generated post is printed in the job log. Run it a few
times to check the voice, then edit `content/brief.json` until you like it.

When the text reads right, run once with dry run **unchecked** to confirm the
whole chain including media upload and the log commit.

---

## Local runs

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
python scripts/post.py --dry-run
```

`--dry-run` generates and prints without publishing or writing the log.
`--no-image` publishes text only.
`--list-models` prints the Gemini models this key can use, and which one the
auto-picker would choose.

---

## Tuning the output

**Voice and facts** live in `content/brief.json`. `voice.dont` is the list that
strips out LLM tells; add to it whenever you spot a phrase you dislike. Prices
and plan limits are in `proof_points` — update them when they change.

**Topics** live in `content/topics.json`. The script picks the least recently
used one, so all 24 cycle before anything repeats — roughly six months at three
posts a week. Add topics whenever you publish a new blog post.

**Post shapes** (question, mini story, contrast, ...) are the `FORMATS` list in
`scripts/post.py`, balanced so no shape runs twice in a row.

**Schedule** is the cron line in `.github/workflows/post.yml`. Note that
scheduled runs on GitHub can be delayed 5–30 minutes under load.

---

## Known failure modes

**403 on `POST /2/tweets`** — access token was issued before Read and Write
permissions. Regenerate it.

**Media upload fails on both endpoints** — free-tier access to X's media
endpoints has changed more than once. The script tries v2 then v1.1 and prints
both errors. If both refuse, run with `--no-image` until it is sorted; text
posts are unaffected.

**404 from Gemini, "no longer available to new users"** — Google retires models
on its own schedule. The script catches this, lists what your key can actually
use, picks the newest stable flash model and carries on, printing which one it
chose. Nothing to do unless you want to pin it: add a repository *variable*
(not a secret) named `GEMINI_MODEL`.

To see the list yourself:

```bash
GEMINI_API_KEY=... python scripts/post.py --list-models
```

**Empty response from Gemini** — usually a safety filter. The error prints
`finishReason`; `SAFETY` means the prompt tripped a filter, anything else is
worth reading in full.

**Post is too long or too short** — the script retries four times, then trims at
a word boundary. Persistent trimming means the length rules in the prompt need
tightening.
