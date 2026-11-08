#!/usr/bin/env python3
"""No external packages or API keys. RSS entries are unverified third-party headlines."""
import datetime as dt
import email.utils
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "news.json"
QUERIES = {
 "US": '"Federal Reserve" OR "Nasdaq" OR "S&P 500" OR "US stocks" OR "earnings"',
 "HK": '"Hang Seng" OR "HKEX" OR "Hong Kong stocks"',
 "CN": '"China A shares" OR "Shanghai Composite" OR "Shenzhen stock market"',
 "UK": '"FTSE 100" OR "Bank of England" OR "London Stock Exchange"',
 "KR": '"KOSPI" OR "Bank of Korea" OR "South Korea stocks"',
}
FINANCE = re.compile(r'\b(stock|stocks|shares|market|markets|nasdaq|dow|s&p|ftse|kospi|hang seng|hkex|earnings|revenue|profit|inflation|cpi|ppi|fed|interest|bank|bond|treasury|ipo|tariff|trade|semiconductor|chip|oil|currency|forex|gdp|economy|economic|index|indices|exchange|wall street|rate)\b|股市|股票|财报|美联储|降息|加息|关税|央行|港股|A股', re.I)
NOISE = re.compile(r'\b(weather|fog|recipe|sleep|football|celebrity|horoscope|gardening|wedding)\b', re.I)
MAJOR = re.compile(r'\b(federal reserve|fomc|rate cut|rate hike|cpi|ppi|earnings|inflation|tariff|gdp|central bank)\b',re.I)

def fetch(query):
    params = urllib.parse.urlencode({"q":query+" when:3d","hl":"en-US","gl":"US","ceid":"US:en"})
    req=urllib.request.Request("https://news.google.com/rss/search?"+params,headers={"User-Agent":"Mozilla/5.0 GlobalInvestPro/1.8"})
    with urllib.request.urlopen(req,timeout=18) as resp:
        xml=resp.read(2_000_000)
    root=ET.fromstring(xml)
    items=[]
    for node in root.findall(".//item"):
        title=(node.findtext("title") or "").strip()
        link=(node.findtext("link") or "").strip()
        if not title or not link.startswith("https://") or not FINANCE.search(title) or NOISE.search(title):continue
        date=node.findtext("pubDate") or ""
        try:
            parsed=email.utils.parsedate_to_datetime(date)
            when=parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")
        except (TypeError,ValueError,OverflowError):continue
        source=node.find("source")
        items.append({"title":title,"url":link,"published":when,"source":source.text if source is not None and source.text else "Google News","importance":"重点关注" if MAJOR.search(title) else "一般财经"})
    return items

def main():
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    errors=[]; articles=[]; seen=set(); successful=0
    for market,query in QUERIES.items():
        try:
            rows=fetch(query);successful+=1
            for item in rows:
                key=re.sub(r'\W+','',item["title"].lower())
                if key in seen:continue
                seen.add(key)
                item["market"]=market
                articles.append(item)
        except Exception as exc:
            errors.append(market+": "+str(exc)[:150])
    articles.sort(key=lambda x:x["published"],reverse=True)
    if successful==0:
        print("All sources failed; preserving existing data, workflow fails visibly.")
        raise RuntimeError("; ".join(errors))
    now=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")
    result={"version":"1.8","generatedAt":now,"provider":"Google News RSS via GitHub Actions","status":"ok" if not errors else "partial","error":"; ".join(errors),"items":articles[:100]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Fetched {len(articles)} articles, {successful}/{len(QUERIES)} markets; errors={errors}")

if __name__=="__main__":main()
