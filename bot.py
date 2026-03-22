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
    "instagram.com", "facebook.com",
    "twitter.com", "x.com",
    "play.google.com",
    "docs.google.com",
    "linktr.ee"
]

# ── BEST / REAL JOB DOMAINS ───────────────────────────
BEST_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "careers.", "career.",
    "jobs.",
    "hire.",
    "apply.",
    "smartrecruiters.com",
    "icims.com",
    "taleo.net",
    "bamboohr.com",
    "recruitee.com",
    "jobvite.com"
]

GOOD_DOMAINS = [
    "linkedin.com/jobs",
    "naukri.com/job",
    "indeed.com/viewjob",
    "glassdoor.com/job"
]

# ── BAD LINK PATTERNS ─────────────────────────────────
BAD_LINK_PATTERNS = [
    "registration", "signup", "sign-up",
    "login", "log-in", "referral",
    "register", "telegram", "whatsapp",
    "youtube", "instagram", "share",
    "subscribe", "follow"
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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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
    return re.findall(r'https?://[^\s\)\]\,\"\']+', text)

# ── CHECK IF URL IS FROM SKIP DOMAIN ─────────────────
def is_skip_url(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in SKIP_DOMAINS)

# ── CHECK IF URL IS BAD LINK ──────────────────────────
def is_bad_link(url):
    url_lower = url.lower()
    return any(bad in url_lower for bad in BAD_LINK_PATTERNS)

# ── CHECK IF URL IS BEST REAL JOB LINK ───────────────
def is_best_domain(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in BEST_DOMAINS)

def is_good_domain(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in GOOD_DOMAINS)

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
        if re.match(r'^https?://\S+$', line.strip()):
            if is_skip_url(line.strip()):
                continue
        cleaned.append(line)
    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

# ── DEEP APPLY LINK EXTRACTION ────────────────────────
def get_best_apply_link(url, depth=0, max_depth=2):
    if depth > max_depth:
        return None
    if is_skip_url(url) or is_bad_link(url):
        return None
    try:
        r = requests.get(url, timeout=6, headers=HEADERS, allow_redirects=True)
        if not r.ok:
            return None

        # Check final redirected URL
        final_url = r.url
        if is_best_domain(final_url) and not is_bad_link(final_url):
            return final_url
        if is_good_domain(final_url) and not is_bad_link(final_url):
            return final_url

        soup = BeautifulSoup(r.text, "html.parser")

        best_link = None
        candidate_link = None

        for a in soup.find_all("a", href=True):
            href = a["href"]
            anchor_text = a.get_text().lower().strip()
            href_lower = href.lower()

            if is_bad_link(href_lower):
                continue
            if is_skip_url(href_lower):
                continue
            if not href.startswith("http"):
                continue

            # Priority 1 — Best domain
            if is_best_domain(href) and not is_bad_link(href):
                return href

            # Priority 2 — Good domain
            if is_good_domain(href) and not is_bad_link(href):
                if not best_link:
                    best_link = href

            # Priority 3 — Apply keyword
            if any(kw in href_lower or kw in anchor_text for kw in ["apply", "careers", "job", "position", "opening", "hiring"]):
                if not best_link:
                    best_link = href

            # Candidate for deeper search
            if any(kw in href_lower for kw in ["job", "career", "hiring", "apply", "opening"]):
                if not candidate_link:
                    candidate_link = href

        if best_link:
            return best_link

        # Go deeper
        if candidate_link and depth < max_depth:
            deeper = get_best_apply_link(candidate_link, depth + 1, max_depth)
            if deeper:
                return deeper

        return None

    except Exception as e:
        print(f"Link fetch error (depth {depth}): {e}")
        return None

# ── EXTRACT JOB FIELDS FROM TEXT ─────────────────────
def extract_fields(text):
    lines = text.split("\n")
    company = role = location = salary = last_date = ""

    for line in lines:
        l = line.lower().strip()
        clean = re.sub(r'[*_]', '', line).strip()
        value = clean.split(":", 1)[-1].strip() if ":" in clean else ""

        if not company:
            if any(w in l for w in ["company", "organisation", "organization", "employer"]):
                company = value
            elif re.search(r'([A-Z][a-z]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group))', line):
                m = re.search(r'([A-Z][a-z]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group))', line)
                if m:
                    company = m.group(0)
            elif "is hiring" in l:
                company = clean.split("is hiring")[0].strip()

        if not role:
            if any(w in l for w in ["role", "position", "title", "post", "designation", "hiring for", "job title"]):
                role = value

        if not location:
            if any(w in l for w in ["location", "place", "city", "venue", "work location"]):
                location = value

        if not salary:
            if any(w in l for w in ["salary", "ctc", "lpa", "per annum", "stipend", "package"]):
                salary = value

        if not last_date:
            if any(w in l for w in ["last date", "apply before", "deadline", "apply by", "closing date"]):
                last_date = value

    return company, role, location, salary, last_date

# ── FORMAT FINAL MESSAGE ──────────────────────────────
def format_message(cleaned_text, apply_link):
    company, role, location, salary, last_date = extract_fields(cleaned_text)

    msg = ""
    if company:
        msg += f"🏢 *Company:* {company}\n"
    if role:
        msg += f"💼 *Role:* {role}\n"
    if location:
        msg += f"📍 *Location:* {location}\n"
    if salary:
        msg += f"💰 *Salary:* {salary}\n"
    if last_date:
        msg += f"⏳ *Last Date:* {last_date}\n"

    # No fields found — use full cleaned text
    if not any([company, role, location, salary, last_date]):
        msg += cleaned_text + "\n"

    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += f"🟢 *Apply Here:*\n{apply_link}\n"
    msg += f"⚡ _Direct Apply Link_"

    return msg.strip()

# ── PROCESS ONE MESSAGE ───────────────────────────────
def process_message(text):
    # Step 1 — Check if job related
    if not is_job_message(text):
        print("Skipped: not a job message")
        return None

    # Step 2 — Extract all URLs
    urls = extract_urls(text)

    # Step 3 — Filter skip/bad URLs
    valid_urls = [u for u in urls if not is_skip_url(u) and not is_bad_link(u)]

    if urls and not valid_urls:
        print("Skipped: only skip domain links found")
        return None

    # Step 4 — Clean text
    cleaned = clean_text(text)
    if not cleaned:
        return None

    # Step 5 — Find best apply link
    final_link = None

    # Check if already a best domain link
    for url in valid_urls:
        if is_best_domain(url) and not is_bad_link(url):
            final_link = url
            break

    # Check good domain
    if not final_link:
        for url in valid_urls:
            if is_good_domain(url) and not is_bad_link(url):
                final_link = url
                break

    # Deep extraction
    if not final_link:
        for url in valid_urls:
            deeper = get_best_apply_link(url, depth=0, max_depth=2)
            if deeper:
                final_link = deeper
                break

    # Fallback to first valid URL
    if not final_link and valid_urls:
        final_link = valid_urls[0]

    # No link at all — send cleaned text only
    if not final_link:
        return cleaned

    # Step 6 — Format and return
    return format_message(cleaned, final_link)

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

                result = process_message(msg.text)
                if not result:
                    new_ids.add(msg_id)
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
