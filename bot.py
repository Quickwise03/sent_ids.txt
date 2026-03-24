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
    -1002049500142,
    -1001433351995,
    -1001510857881,
    -1001538889184
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
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "instahyre.com",
    "internshala.com",
    "shine.com",
    "monster.com",
    "hirist.com",
    "foundit.in",
    "wellfound.com",
    "cutshort.io",
    "unstop.com"
]

JOB_BLOGS = [
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
    "sarkariwallahjob.com"
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
    "sharethis.com"
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
    return any(bad in url_lower for bad in BAD_LINK_PATTERNS)


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


def scrape_apply_link_from_blog(url):
    try:
        r = requests.get(url, timeout=8, headers=HEADERS, allow_redirects=True)
        if not r.ok:
            return url

        final_url = r.url
        if is_best_domain(final_url):
            return final_url
        if is_good_domain(final_url):
            return final_url

        soup = BeautifulSoup(r.text, "html.parser")

        # Priority 1 — ATS or portal links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                continue
            if is_skip_url(href) or is_bad_link(href):
                continue
            if is_best_domain(href):
                return href
            if is_good_domain(href):
                return href

        # Priority 2 — Apply button text
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text().lower().strip()
            if not href.startswith("http"):
                continue
            if is_skip_url(href) or is_bad_link(href):
                continue
            if is_job_blog(href):
                continue
            if any(kw in text for kw in ["apply now", "apply here", "apply online", "click here to apply", "official link", "apply link", "official website"]):
                return href

        # Priority 3 — Any external non-blog link
        blog_domain_match = re.search(r'https?://([^/]+)', url)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                continue
            if is_skip_url(href) or is_bad_link(href):
                continue
            if is_job_blog(href):
                continue
            link_domain_match = re.search(r'https?://([^/]+)', href)
            if blog_domain_match and link_domain_match:
                if blog_domain_match.group(1) != link_domain_match.group(1):
                    return href

        # No external link — return blog page itself (walk-in jobs)
        return url

    except Exception as e:
        print(f"Blog scrape error: {e}")
        return url


def extract_fields(text):
    lines = text.split("\n")
    company = role = location = salary = last_date = ""

    for line in lines:
        l = line.lower().strip()
        clean = re.sub(r'[*_]', '', line).strip()
        value = clean.split(":", 1)[-1].strip() if ":" in clean else ""

        if value.startswith("http") or value.startswith("//"):
            continue
        if not value or len(value) < 2:
            continue

        if not company:
            if any(w in l for w in ["company", "organisation", "organization", "employer"]):
                company = value
            elif re.search(r'([A-Z][a-zA-Z ]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group|Data|Global))', line):
                m = re.search(r'([A-Z][a-zA-Z ]+ ?(Technologies|Solutions|Systems|Services|India|Ltd|Pvt|Inc|Corp|Group|Data|Global))', line)
                if m:
                    company = m.group(0).strip()
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

    if not any([company, role, location, salary, last_date]):
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

    final_link = None

    for url in valid_urls:
        if is_best_domain(url):
            final_link = url
            print(f"Best domain: {url}")
            break

    if not final_link:
        for url in valid_urls:
            if is_good_domain(url):
                final_link = url
                print(f"Good domain: {url}")
                break

    if not final_link:
        for url in valid_urls:
            if is_job_blog(url):
                print(f"Scraping blog: {url}")
                scraped = scrape_apply_link_from_blog(url)
                if scraped:
                    final_link = scraped
                    print(f"Scraped: {scraped}")
                    break

    if not final_link:
        for url in valid_urls:
            scraped = scrape_apply_link_from_blog(url)
            if scraped:
                final_link = scraped
                break

    if not final_link:
        print("Skipped: no apply link found")
        return None

    return format_message(cleaned, final_link)


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
