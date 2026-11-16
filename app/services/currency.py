
import xml.etree.ElementTree as ET
from urllib.request import Request,urlopen
from app.core.config import settings
from datetime import datetime,timedelta,timezone


FETCH_TIMEOUT_SECONDS=10

MAX_FEED_BYTES=2*1024*1024

_cache_={"data":None,"fetched_at":None}


def fetch_rates_xml(url:str) ->bytes:
    request=Request(url,headers={"User-Agent":"Sefername/1.0"})
    with urlopen(request,timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read(MAX_FEED_BYTES)
    


def parse_rates(data:bytes,codes:list[str]) -> dict:
    root=ET.fromstring(data)
    rates=[]
    date_text=root.attrib["Tarih"]
    bulletin_date=datetime.strptime(date_text,"%d.%m.%Y").date()

    for currency in root.findall("Currency"):
        code=currency.attrib["Kod"]
        if code not in codes:
            continue
        # TCMB pads the names with spaces to a fixed width
        name=(currency.findtext("CurrencyName") or "").strip()
        buying_text=currency.findtext("ForexBuying")
        if not buying_text:
            continue
        buying=float(buying_text)
        rates.append({"code":code,"name":name,"buying":buying})
    return {"date":bulletin_date,"rates":rates}

def get_rates()-> dict |None:
    now=datetime.now(timezone.utc)
    if _cache_["fetched_at"] is not None and now - _cache_["fetched_at"]< timedelta(minutes=settings.currency_refresh_minutes):
        return _cache_["data"]
    try:
        _cache_["data"]=parse_rates(fetch_rates_xml(settings.currency_feed_url),settings.currency_codes)
    except (OSError,ET.ParseError,KeyError,ValueError):
        pass
    _cache_["fetched_at"]=now
    return _cache_["data"]


