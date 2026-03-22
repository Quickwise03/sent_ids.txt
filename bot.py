from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import asyncio
import re
import requests
from bs4 import BeautifulSoup

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")

if not session_string:
    raise ValueError("SESSION_STRING missing. Add in GitHub Secrets.")

client = TelegramClient(StringSession(session_string), api_id, api_hash)

SOURCE_CHANNELS = [
    -1001160330973,
    -1001256565029,
    -1001603220106,
    -1002594747501,
    -1001286809069,
    -1002049500142,
    -1001538889184,
    -1001433351995,
    -1001510857881
]

DEST_CHANNEL = -1003572048499

# ── SKIP DOMAINS ──────────────────────────────────────
SKIP_DOMAINS = [
    "youtube.com", "youtu.be",
    "t.me", "telegram.me", "telegram.dog",
    "chat.whatsapp.com", "wa.me",
    "instagram.com",
    "play.google.com",
    "facebook.com", "twitter.com", "x.com"
]

# ── JOB KEYWORDS ─────────────────────────────────────
JOB_KEYWORDS = [
    "apply", "hiring", "vacancy", "vacancies", "opening",
    "recruit", "opportunity", "fresher", "experience",
    "salary", "ctc", "lpa", "walk-in", "walkin", "off campus",
    "internship", "intern", "joining", "position", "role",
    "engineer", "developer", "analyst", "manager", "executive",
    "job", "careers", "qualification", "batch", "skills"
]

# ── PROMO LINES TO REMOVE ─────────────────────────────
PROMO_LINES = [
    "join telegram", "join our telegram", "join whatsapp",
    "join our whatsapp", "share with friends", "share this",
    "follow us", "subscribe", "click here to join",
    "join now", "join channel", "join group",
    "forward this", "tag your friends",
    "share with your", "besties", "drop a",
    "our channel", "our group"
]

# ── GOOD APPLY DOMAINS ────────────────────────────────
GOOD_DOMAINS = [
    "naukri.com", "linkedin.com", "indeed.com",
    "greenhouse.io", "lever.co", "workday.com",
    "careers.", "jobs.", "apply.", "hire."
]

# ── LOAD / SAVE SENT IDS ──────────────────────────────
def load_ids():
    try:
        with open("sent_ids.txt", "r") as f:
            return set(f.read().splitlines())
    except:
        return set()

def save_ids(ids):
    with open("sent_ids.txt", "w") as f:
        f.write("\n".join(ids))

# ── EXTRACT ALL URLS FROM TEXT ────────────────────────
def extract_urls(text):
    return re.findall(r'https?://[^\s\)\]]+', text)

# ── CHECK IF URL IS FROM SKIP DOMAIN ─────────────────
def is_skip_url(url):
    for domain in SKIP_DOMAINS:
        if domain in url:
            return True
    return False

# ── CHECK IF MESSAGE IS JOB RELATED ──────────────────
def is_job_message(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in JOB_KEYWORDS)

# ── CLEAN PROMO LINES FROM TEXT ───────────────────────
def clean_text(text):
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line_lower = line.lower().strip()
        if any(promo in line_lower for promo in PROMO_LINES):
            continue
        # Remove lines that are only URLs from skip domains
        if re.match(r'^https?://\S+$', line.strip()):
            if is_skip_url(line.strip()):
                continue
        cleaned.append(line)
    # Remove extra blank lines
    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

# ── FETCH BEST APPLY LINK FROM URL ───────────────────
def get_best_apply_link(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=6, headers=headers)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        best = None
        # Search all <a> tags
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text().lower()
            # Skip bad links
            if any(bad in href for bad in ["telegram", "whatsapp", "youtube", "share", "category", "instagram"]):
                continue
            # Check for good keywords in link or text
            if any(kw in href or kw in text for kw in ["apply", "job", "careers", "join", "hiring"]):
                full = a["href"]
                if not full.startswith("http"):
                    continue
                # Prefer good domains
                if any(gd in full for gd in GOOD_DOMAINS):
                    return full
                if not best:
                    best = full
        return best
    except Exception as e:
        print(f"Link fetch error: {e}")
        return None

# ── FORMAT FINAL MESSAGE ──────────────────────────────
def format_message(cleaned_text, apply_link):
    # Extract basic info using regex
    lines = cleaned_text.split("\n")

    company = ""
    role = ""
    location = ""

    for line in lines:
        l = line.lower()
        if not company and any(w in l for w in ["company", "org", "organisation", "organization"]):
            company = line.split(":", 1)[-1].strip() if ":" in line else ""
        if not role and any(w in l for w in ["role", "position", "title", "post", "designation"]):
            role = line.split(":", 1)[-1].strip() if ":" in line else ""
        if not location and any(w in l for w in ["location", "place", "city", "venue"]):
            location = line.split(":", 1)[-1].strip() if ":" in line else ""

    # Build formatted message
    msg = ""
    if company:
        msg += f"🏢 *Company:* {company}\n"
    if role:
        msg += f"💼 *Role:* {role}\n"
    if location:
        msg += f"📍 *Location:* {location}\n"

    # Add cleaned text if no structured info found
    if not company and not role:
        msg += cleaned_text + "\n"

    msg += f"\n🟢 *Apply Here:*\n{apply_link}"
    msg += "\n\n⚡ _Direct Apply Link_"

    return msg.strip()

# ── PROCESS ONE MESSAGE ───────────────────────────────
def process_message(text):
    # Step 1 — Check if job related
    if not is_job_message(text):
        print("Skipped: not a job message")
        return None

    # Step 2 — Extract all URLs
    urls = extract_urls(text)

    # Step 3 — Check if all URLs are from skip domains
    valid_urls = [u for u in urls if not is_skip_url(u)]

    if urls and not valid_urls:
        print("Skipped: only skip domain links found")
        return None

    # Step 4 — Clean text
    cleaned = clean_text(text)
    if not cleaned:
        return None

    # Step 5 — Find best apply link
    apply_link = None

    for url in valid_urls:
        better = get_best_apply_link(url)
        if better:
            apply_link = better
            break

    # Step 6 — Use original link if no better found
    if not apply_link and valid_urls:
        apply_link = valid_urls[0]

    # Step 7 — No link at all → use cleaned text only
    if not apply_link:
        # Still send if it has good job info
        return cleaned

    # Step 8 — Format final message
    return format_message(cleaned, apply_link)

# ── MAIN ──────────────────────────────────────────────
async def main():
    sent_ids = load_ids()
    new_ids = set(sent_ids)

    for channel in SOURCE_CHANNELS:
        try:
            messages = await client.get_messages(channel, limit=100)
            for msg in messages:
                if not msg.text:
                    continue
                msg_id = f"{channel}_{msg.id}"
                if msg_id in sent_ids:
                    continue

                # Process message
                result = process_message(msg.text)
                if not result:
                    new_ids.add(msg_id)  # Mark as seen even if skipped
                    continue

                print("Sending:", result[:60])
                await client.send_message(DEST_CHANNEL, result, parse_mode="md")
                new_ids.add(msg_id)

                # Small delay to avoid flood
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in channel {channel}: {e}")

    save_ids(new_ids)

with client:
    client.start()
    asyncio.get_event_loop().run_until_complete(main())
