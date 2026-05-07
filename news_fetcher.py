import feedparser
import requests
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_CHANNELS = {
    "CharlieintelCOD": "UCeVTDMFtQidODTCMFEMkIoA",
    "Zilianop": "UCiWdBack-tMFJG1cCDFKqPw",
    "JOKESTA": "UCQ8bF5Np0M0K7Jh_jBpHMxw",
    "Dogg": "UCq7Z7BbTAYjGqvkSQDbWS9A",
    "BobbyPlays": "UCPGiDHBMeqnRNGKEiWKOKGQ",
}

REDDIT_FEEDS = [
    "https://www.reddit.com/r/CallOfDutyMobile/.rss",
    "https://www.reddit.com/r/CODMLeaks/.rss",
    "https://www.reddit.com/r/CODMCompetitive/.rss",
]

RSS_FEEDS = [
    "https://charlieintel.com/feed",
    "https://www.dexerto.com/feed/",
    "https://dotesports.com/feed",
]

NITTER_ACCOUNTS = [
    "CODMLeaks",
    "CharlieintelCOD",
    "CODTracker",
]

TRUSTED_DOMAINS = [
    "charlieintel.com",
    "dexerto.com",
    "dotesports.com",
    "reddit.com",
    "youtu.be",
    "youtube.com",
    "nitter.poast.org",
    "nitter.privacydev.net",
]

BLOCKED_KEYWORDS = [
    "free cp", "hack", "generator", "giveaway link",
    "click here", "earn cp", "unlimited", "cheat"
]


def is_quality_post(title):
    title_lower = title.lower()
    return not any(word in title_lower for word in BLOCKED_KEYWORDS)


def is_trusted_source(link):
    return any(domain in link for domain in TRUSTED_DOMAINS)


def get_youtube_videos():
    updates = []
    for name, channel_id in YOUTUBE_CHANNELS.items():
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?key={YOUTUBE_API_KEY}&channelId={channel_id}"
            f"&part=snippet&order=date&maxResults=3&type=video"
        )
        try:
            res = requests.get(url, timeout=10).json()
            for item in res.get("items", []):
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                thumbnail = item["snippet"]["thumbnails"]["high"]["url"]
                updates.append({
                    "title": f"📺 {name}: {title}",
                    "link": f"https://youtu.be/{video_id}",
                    "image": thumbnail,
                    "source": "YouTube"
                })
        except Exception as e:
            print(f"YouTube error ({name}): {e}")
    return updates


def get_reddit_posts():
    updates = []
    for feed_url in REDDIT_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                image = None
                if hasattr(entry, 'media_thumbnail'):
                    image = entry.media_thumbnail[0]['url']
                updates.append({
                    "title": f"👾 {entry.title}",
                    "link": entry.link,
                    "image": image,
                    "source": "Reddit"
                })
        except Exception as e:
            print(f"Reddit error: {e}")
    return updates


def get_rss_news():
    updates = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                image = None
                if hasattr(entry, 'media_content'):
                    image = entry.media_content[0].get('url')
                updates.append({
                    "title": f"📰 {entry.title}",
                    "link": entry.link,
                    "image": image,
                    "source": "News"
                })
        except Exception as e:
            print(f"RSS error: {e}")
    return updates


def get_xleaks():
    updates = []
    nitter_instances = [
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    for account in NITTER_ACCOUNTS:
        for instance in nitter_instances:
            try:
                url = f"{instance}/{account}/rss"
                feed = feedparser.parse(url)
                if feed.entries:
                    for entry in feed.entries[:2]:
                        updates.append({
                            "title": f"🐦 @{account}: {entry.title[:120]}",
                            "link": entry.link,
                            "image": None,
                            "source": "X/Twitter"
                        })
                    break
            except Exception as e:
                print(f"Nitter error ({account}): {e}")
    return updates


def get_latest_news():
    all_updates = []
    all_updates += get_youtube_videos()
    all_updates += get_reddit_posts()
    all_updates += get_rss_news()
    all_updates += get_xleaks()

    filtered = [
        u for u in all_updates
        if is_quality_post(u['title']) and is_trusted_source(u['link'])
    ]

    print(f"Total fetched: {len(all_updates)} | After filter: {len(filtered)}")
    return filtered