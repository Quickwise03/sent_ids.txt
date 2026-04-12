from datetime import datetime, timezone, timedelta
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
    -1001510857881,
    -1001538889184,
    -1001309472884,
    -1001545054165
]


DEST_CHANNEL = -1003572048499

SKIP_DOMAINS = [
    "youtube.com", "youtu.be",
    "t.me", "telegram.me", "telegram.dog",
    "chat.whatsapp.com", "wa.me",
    "whatsapp.com/channel",
    "instagram.com", "facebook.com",
    "twitter.com", "x.com",
    "play.google.com",
    "docs.google.com",
    "linktr.ee",
    "addtoany.com",
    "sharethis.com"
]

BEST_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "icims.com",
    "taleo.net",
    "bamboohr.com",
    "recruitee.com",
    "jobvite.com",
    "successfactors.com",
    "keka.com",
    "darwinbox.com"
]

GOOD_DOMAINS = [
    "linkedin.com/jobs",
    "linkedin.com/job",
    "naukri.com/job-listings",
    "indeed.com",
    "internshala.com",
    "instahyre.com",
    "shine.com",
    "hirist.com",
    "foundit.in",
    "wellfound.com",
    "cutshort.io",
    "unstop.com"
]

JOB_BLOGS = [
    # Aggregator/blog sites — scrape for direct link
    "fresheroffcampus.com",
    "fresheroffcampus.in",
    "vacancyquick.com",
    "foundthejob.com",
    "jobphobia.com",
    "placementpreparation.io",
    "placementstore.com",
    "freejobalert.com",
    "sarkariresult.com",
    "rojgarresult.com",
    "freshersworld.com",
    "freshersnow.com",
    "freshersrecruitment.co.in",
    "freshershunt.in",
    "letsdojob.in",
    "careesma.in",
    "jobsarkari.com",
    "govtjobguru.in",
    "recruitment.guru",
    "hiringalert.in",
    "jobnotification.in",
    "careerwill.com",
    "rojgaralert.com",
    "sarkariwallahjob.com",
    "freshersjobsaadda.blogspot.com",
    "foundit.in",          # affiliate redirect — never direct
    "tinyurl.com",
    "bit.ly",
    "freshersdunia.in"
]

BAD_LINK_PATTERNS = [
    "t.me/",
    "telegram.me/",
    "telegram.dog/",
    "chat.whatsapp.com",
    "whatsapp.com/channel",
    "wa.me/",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com/",
    "play.google.com",
    "addtoany.com",
    "sharethis.com",
    # Email disguised as URL
    "@gmail.com",
    "@yahoo.com",
    "@hotmail.com",
    "@outlook.com",
    # Spam / non-job sites
    "getrevue.co",
    "tinyurl.com",
    "bit.ly",
    "forms.gle",       # Google Forms = usually spam course registration
    "linktr.ee",
    # Wildcard / broken links
    "/**",
    "/*"
]

JOB_KEYWORDS = [
    "apply", "hiring", "vacancy", "vacancies", "opening",
    "recruit", "opportunity", "fresher", "experience",
    "salary", "ctc", "lpa", "walk-in", "walkin", "off campus",
    "internship", "intern", "joining", "position", "role",
    "engineer", "developer", "analyst", "manager", "executive",
    "job", "careers", "qualification", "batch", "skills"
]

PROMO_LINES = [
    "join telegram", "join our telegram", "join whatsapp",
    "join our whatsapp", "share with friends", "share this",
    "follow us", "subscribe", "click here to join",
    "join now", "join channel", "join group",
    "forward this", "tag your friends",
    "share with your", "besties", "drop a",
    "our channel", "our group", "follow jobphobia",
    "follow vacancy", "whatsapp channel", "daily job alerts"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def load_ids():
    try:
        with open("sent_ids.txt", "r") as f:
            return set(f.read().splitlines())
    except:
        return set()


def save_ids(ids):
    with open("sent_ids.txt", "w") as f:
        f.write("\n".join(ids))


def extract_urls(text):
    return re.findall(r'https?://[^\s\)\]\,\"\']+', text)


def is_skip_url(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in SKIP_DOMAINS)


def is_bad_link(url):
    url_lower = url.lower()
    # Check pattern list
    if any(bad in url_lower for bad in BAD_LINK_PATTERNS):
        return True
    # Block email-as-URLs (contain @)
    if "@" in url:
        return True
    # Block URLs ending with wildcard patterns
    if url.rstrip("/").endswith("**") or url.rstrip("/").endswith("*"):
        return True
    # Block academic / personal pages that are not job portals
    academic_patterns = [".ac.in/", ".edu/", "blogger.com", "blogspot.com",
                         "getrevue.co", "substack.com"]
    if any(p in url_lower for p in academic_patterns):
        return True
    return False


def is_best_domain(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in BEST_DOMAINS)


def is_good_domain(url):
    url_lower = url.lower()
    return any(domain in url_lower for domain in GOOD_DOMAINS)


def is_job_blog(url):
    url_lower = url.lower()
    return any(blog in url_lower for blog in JOB_BLOGS)


def is_job_message(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in JOB_KEYWORDS)


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


# Apply button text patterns — case insensitive
APPLY_TEXTS = [
    "apply now", "apply here", "apply online",
    "click here to apply", "official link", "apply link",
    "official website", "direct link", "apply directly",
    "click to apply", "application link", "register now",
    "apply for this job", "apply for this role"
]

def scrape_apply_link_from_blog(url):
    # Clean up wildcard/broken URLs from fresheroffcampus etc.
    # e.g. https://www.fresheroffcampus.com/hcltech-off-campus/** -> remove /**
    clean_url = re.sub(r'/\*+$', '', url).rstrip("/")
    if is_bad_link(clean_url) or not clean_url.startswith("http"):
        return None  # Return None so caller skips it

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.get(clean_url, timeout=10, headers=headers, allow_redirects=True)
        if not r.ok:
            print(f"  Fetch failed {r.status_code}: {clean_url}")
            return None  # Page doesn't exist, skip

        # Check if redirect already landed on a good/best domain
        final_url = r.url
        if is_best_domain(final_url) and not is_job_blog(final_url):
            return final_url
        if is_good_domain(final_url) and not is_job_blog(final_url):
            return final_url

        soup = BeautifulSoup(r.text, "html.parser")
        source_domain = re.search(r'https?://([^/]+)', clean_url)
        source_host = source_domain.group(1) if source_domain else ""

        # ── PASS 1: Best domain (ATS systems) ────────────────
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if is_bad_link(href) or is_job_blog(href):
                continue
            if is_best_domain(href):
                print(f"  Found BEST domain: {href[:80]}")
                return href

        # ── PASS 2: Good domain (Naukri, LinkedIn, etc.) ─────
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if is_bad_link(href) or is_job_blog(href):
                continue
            if is_good_domain(href):
                print(f"  Found GOOD domain: {href[:80]}")
                return href

        # ── PASS 3: Apply button text match ──────────────────
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(" ", strip=True).lower()
            if not href.startswith("http"):
                continue
            if is_bad_link(href) or is_job_blog(href):
                continue
            aria = (a.get("aria-label") or "").lower()
            title_attr = (a.get("title") or "").lower()
            combined = text + " " + aria + " " + title_attr
            if any(kw in combined for kw in APPLY_TEXTS):
                print(f"  Found via apply text: {href[:80]}")
                return href

        # ── PASS 4: CSS class hints ────────────────────────
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            classes = " ".join(a.get("class") or []).lower()
            if not href.startswith("http"):
                continue
            if is_bad_link(href) or is_job_blog(href):
                continue
            if any(kw in classes for kw in ["apply", "btn-primary", "cta", "apply-btn", "job-apply"]):
                link_host = re.search(r'https?://([^/]+)', href)
                if link_host and link_host.group(1) != source_host:
                    print(f"  Found via CSS class: {href[:80]}")
                    return href

        # ── PASS 5: First external link not from same domain ───
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if is_bad_link(href) or is_job_blog(href):
                continue
            link_host = re.search(r'https?://([^/]+)', href)
            if link_host and link_host.group(1) != source_host:
                print(f"  Found external fallback: {href[:80]}")
                return href

        print(f"  No direct link found for: {clean_url[:80]}")
        return None  # Return None — better to skip than post a blog link

    except Exception as e:
        print(f"Blog scrape error for {clean_url[:60]}: {e}")
        return None


# Strips emojis and markdown formatting from a line
def strip_line(line):
    # Remove markdown bold/italic/code
    line = re.sub(r'[*_`]', '', line)
    # Remove emojis by encoding to ASCII ignoring non-ASCII chars
    # Then decode back — keeps letters, numbers, punctuation
    line = line.encode('ascii', 'ignore').decode('ascii')
    return line.strip()


def extract_fields(text):
    lines = text.split("\n")
    company = role = location = salary = last_date = ""
    qualification = experience = batch = ""

    # Try to extract company + role from headline (first line)
    # e.g. "HCLTech Off Campus 2026 Hiring Freshers – Associate IT Engineer"
    first_line = strip_line(lines[0]).strip() if lines else ""
    headline_match = re.search(
        r'([A-Z][a-zA-Z0-9& ]+?)\s+(?:off campus|hiring|recruitment|internship|walk.?in)',
        first_line, re.IGNORECASE
    )
    if headline_match and not company:
        company = headline_match.group(1).strip()

    # Role from headline: text after last dash/em dash
    dash_split = re.split(r'[–—\-]{1,2}', first_line)
    if len(dash_split) > 1 and not role:
        candidate = dash_split[-1].strip()
        if len(candidate) > 5 and not candidate.startswith("http"):
            role = candidate

    for line in lines:
        l = strip_line(line).lower().strip()
        clean = strip_line(line).strip()
        # Value is everything after the first colon
        value = clean.split(":", 1)[-1].strip() if ":" in clean else ""

        if value.startswith("http") or value.startswith("//"):
            continue
        if not value or len(value) < 2:
            continue

        # Company
        if not company:
            if any(w in l for w in ["company", "organisation", "organization", "employer"]):
                company = value
            elif re.search(r'([A-Z][a-zA-Z0-9& ]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group|Data|Global|Tech))', clean):
                m = re.search(r'([A-Z][a-zA-Z0-9& ]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group|Data|Global|Tech))', clean)
                if m:
                    company = m.group(0).strip()
            elif "is hiring" in l:
                company = clean.split("is hiring")[0].strip()

        # Role
        if not role:
            if any(w in l for w in ["role", "position", "title", "post", "designation", "hiring for", "job title"]):
                role = value

        # Location
        if not location:
            if any(w in l for w in ["location", "place", "city", "venue", "work location"]):
                location = value

        # Salary / CTC
        if not salary:
            if any(w in l for w in ["salary", "ctc", "lpa", "per annum", "stipend", "package"]):
                salary = value

        # Qualification / Education
        if not qualification:
            if any(w in l for w in ["qualification", "eligibility", "education", "degree", "graduates"]):
                qualification = value

        # Experience
        if not experience:
            if any(w in l for w in ["experience", "exp", "work experience"]):
                # Make sure it's not a salary line
                if not any(w in l for w in ["salary", "ctc", "lpa"]):
                    experience = value

        # Batch year
        if not batch:
            if "batch" in l or re.search(r'\b20(2[3-9]|3[0-9])\b.*\b20(2[3-9]|3[0-9])\b', value):
                batch = value

        # Last date
        if not last_date:
            if any(w in l for w in ["last date", "apply before", "deadline", "apply by", "closing date"]):
                last_date = value

    return company, role, location, salary, qualification, experience, batch, last_date


def format_message(cleaned_text, apply_link):
    company, role, location, salary, qualification, experience, batch, last_date = extract_fields(cleaned_text)

    # Skip useless messages that have only company name and nothing else
    # e.g. "🏢 Company: HCL Tech" with no role/location/salary
    useful_fields = [role, location, salary, qualification, experience]
    if not company and not role:
        print(f"Skipped: no company or role — skipping")
        return None

    msg = ""
    if company:
        msg += f"🏢 *Company:* {company}\n"
    if company and not role:
        role = company + " Job Opening"
    if role:
        msg += f"💼 *Role:* {role}\n"
    if role:
        msg += f"💼 *Role:* {role}\n"
    if location:
        msg += f"📍 *Location:* {location}\n"
    if salary:
        msg += f"💰 *Salary:* {salary}\n"
    if qualification:
        msg += f"🎓 *Qualification:* {qualification}\n"
    if experience:
        msg += f"💼 *Experience:* {experience}\n"
    if batch:
        msg += f"🥇 *Batch:* {batch}\n"
    if last_date:
        msg += f"⏳ *Last Date:* {last_date}\n"

    # If nothing extracted at all, fall back to cleaned text
    if not any([company, role, location, salary, qualification, experience, batch, last_date]):
        msg += cleaned_text + "\n"

    msg += f"\n━━━━━━━━━━━━━━━\n"
    msg += f"🟢 *Apply Here:*\n{apply_link}\n"
    msg += f"⚡ _Direct Apply Link_"

    return msg.strip()


def process_message(text):
    if not is_job_message(text):
        print("Skipped: not a job message")
        return None

    urls = extract_urls(text)
    valid_urls = [u for u in urls if not is_skip_url(u) and not is_bad_link(u)]

    if urls and not valid_urls:
        print("Skipped: only skip domain links found")
        return None

    cleaned = clean_text(text)
    if not cleaned:
        return None

    # Collect ALL links — one per job
    final_links = []
    for url in valid_urls:
        if is_best_domain(url) and not is_job_blog(url):
            final_links.append(url)
        elif is_good_domain(url) and not is_job_blog(url):
            final_links.append(url)
        elif is_job_blog(url) or not (is_best_domain(url) or is_good_domain(url)):
            scraped = scrape_apply_link_from_blog(url)
            if scraped:  # None means skip
                # Only add if it's not a blog/bad link itself
                if not is_job_blog(scraped) and not is_bad_link(scraped):
                    final_links.append(scraped)
                else:
                    print(f"  Scraped link still a blog/bad: {scraped[:60]} — skipped")

    if not final_links:
        print("Skipped: no apply link found")
        return None

    # Single link — return one message
    if len(final_links) == 1:
        return format_message(cleaned, final_links[0])

    # Multiple links — return list of messages
    messages = []
    for link in final_links:
        messages.append(format_message(cleaned, link))
    return messages


async def main():
    sent_ids = load_ids()
    new_ids = set(sent_ids)

    since = datetime.now(timezone.utc) - timedelta(hours=24)

    for channel in SOURCE_CHANNELS:
        try:
            messages = await client.get_messages(channel, limit=100)
            recent = [m for m in messages if m.date and m.date.replace(tzinfo=timezone.utc) >= since]
            print(f"Channel {channel}: {len(recent)} recent messages")

            for msg in recent:
                if not msg.text:
                    continue
                msg_id = f"{channel}_{msg.id}"
                if msg_id in sent_ids:
                    continue

                result = process_message(msg.text)
                if not result:
                    new_ids.add(msg_id)
                    continue

                # Handle both single and multiple messages
                if isinstance(result, list):
                    for r in result:
                        print("Sending:", r[:60])
                        await client.send_message(DEST_CHANNEL, r, parse_mode="md")
                        await asyncio.sleep(1)
                else:
                    print("Sending:", result[:60])
                    await client.send_message(DEST_CHANNEL, result, parse_mode="md")

                new_ids.add(msg_id)
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in channel {channel}: {e}")

    save_ids(new_ids)


with client:
    client.start()
    asyncio.get_event_loop().run_until_complete(main())

