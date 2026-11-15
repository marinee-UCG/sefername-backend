from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
from app.core.config import settings
from email.utils import parsedate_to_datetime
from datetime import datetime,timedelta,timezone


FETCH_TIMEOUT_SECONDS=10

MAX_FEED_BYTES=2*1024*1024
ALLOWED_LINK_PREFIX="https://www.trthaber.com/"

_cache_={"items":[],"fetched_at":None}


def fetch_feed(url:str) -> bytes:
    request=Request(url,headers={"User-Agent":"Sefername/1.0"})
    with urlopen(request,timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read(MAX_FEED_BYTES)

def parse_headlines(data:bytes,count:int) -> list[dict]:
    root=ET.fromstring(data)
    headlines=[]
    for item in root.iter("item"):
        title=item.findtext("title")
        link=item.findtext("link")
        if title is None or link is None or not link.startswith(ALLOWED_LINK_PREFIX):
            continue
        pub_date=item.findtext("pubDate")
        published_at=None
        if pub_date is not None:
            try:
                published_at=parsedate_to_datetime(pub_date)
            except (TypeError,ValueError):
                pass
        headlines.append({"title":title.strip(),"url":link,"published_at":published_at})
        if len(headlines) >= count:
            break
    return headlines

def get_headlines() -> list[dict]:
    now=datetime.now(timezone.utc)
    # Still fresh: hand out what we have, TRT is not asked again
    if _cache_["fetched_at"] is not None and now-_cache_["fetched_at"] < timedelta(minutes=settings.news_refresh_minutes):
        return _cache_["items"]
    try:
        _cache_["items"]=parse_headlines(fetch_feed(settings.news_feed_url),settings.news_count)
    except (OSError,ET.ParseError):
        # TRT down or sent broken XML: keep the last good list
        pass
    # Counted even when it failed, so a dead feed is tried again in 15 minutes, not on every request
    _cache_["fetched_at"]=now
    return _cache_["items"]