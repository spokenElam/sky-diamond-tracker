#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v18 (SPA/JSON Decode Fix)
破解利嘉閣的 Single Page Application 結構，從 JSON Script 中提取資料。
"""

import json
import os
import smtplib
import urllib.request
import re
import time
import random
import html  # [新增] 用來解碼 HTML
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
CONFIG = {
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"],
    "URL_28HSE": "https://www.28hse.com/buy/a3/dg45/c22902",
    "URL_RICA": "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%A4%A9%E9%91%BD-estate-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-hma-hk"
}

def log(msg):
    print(msg, flush=True)

def get_headers():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.3 Safari/605.1.15',
    ]
    return {
        'User-Agent': random.choice(agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': 'locale=zh-hk'
    }

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    try:
        time.sleep(random.uniform(2, 4))
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error ({url}): {e}")
        return None

# =============================================================================
# 1. 28Hse (保持完美狀態)
# =============================================================================
def scrape_28hse():
    log("--- Scraping 28Hse ---")
    html_raw = fetch_url(CONFIG["URL_28HSE"])
    if not html_raw: return []
    if "Security Check" in html_raw: return []

    listings = []
    chunks = re.split(r'class="item', html_raw)
    
    for chunk in chunks[1:]:
        try:
            tower = 0; floor = "??"; unit = "?"
            full_desc_match = re.search(r'unit_desc"[^>]*>\s*(.*?)\s*<', chunk)
            if full_desc_match:
                full_text = full_desc_match.group(1)
                t_match = re.search(r'(\d+)\s*座', full_text)
                if t_match: tower = int(t_match.group(1))
                f_match = re.search(r'(低|中|高)層', full_text)
                if f_match: floor = f_match.group(1)
                u_match = re.search(r'([A-H])室', full_text, re.IGNORECASE)
                if u_match: unit = u_match.group(1).upper()
            
            if tower == 0:
                t_match_backup = re.search(r'(?:第|Block)?\s*(\d+)\s*座', chunk)
                if t_match_backup: tower = int(t_match_backup.group(1))

            if tower == 0: continue

            price_match = re.search(r'(?:\$|售)\s*([\d,]+)\s*萬', chunk)
            if not price_match: continue
            price = int(price_match.group(1).replace(',', '')) * 10000

            clean_text = re.sub(r'<[^>]+>', ' ', chunk)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            desc = clean_text[10:60] + "..."
            
            link_match = re.search(r'href="([^"]+)"', chunk)
            link = link_match.group(1) if link_match else CONFIG["URL_28HSE"]

            listing = {
                "id": f"28hse-{tower}-{price}",
                "tower": tower, "floor": floor, "unit": unit,
                "price": price, "raw_desc": desc, "url": link,
                "source": "hse28", "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ 28Hse: T{tower} {floor} {unit} ${price/10000}萬")
        except: continue
    return listings

# =============================================================================
# 2. Ricacorp (針對 SPA JSON 結構)
# =============================================================================
def scrape_ricacorp():
    log("--- Scraping Ricacorp ---")
    raw_response = fetch_url(CONFIG["URL_RICA"])
    if not raw_response: return []
    
    # [關鍵步驟] 利嘉閣資料藏在 JSON Script 內，而且被編碼了 (e.g. &quot;)
    # 必須先解碼，Regex 才能生效
    clean_html = html.unescape(raw_response)
    
    # 檢查是否被 Incapsula 防火牆擋住
    if "Incapsula" in clean_html or "Request unsuccessful" in clean_html:
        log("🚨 Ricacorp Blocked by Firewall.")
        return []

    listings = []
    
    # 策略：因為解碼後資料會變成一長串文字
    # 我們根據你截圖的格式 "天鑽 8座 1房" 來抓
    # 尋找: 天鑽... (任意空白) ... 數字 + 座 ...... (400字內) ..... $ + 數字
    
    # Regex 解釋:
    # 天鑽\s+            -> 必須見到天鑽
    # (?:第)?(\d+)\s*座  -> 抓座號 (Group 1)
    # .{0,400}?         -> 往後找
    # \$([\d,]+)        -> 抓價錢 (Group 2)
    
    pattern = r'天鑽\s+(?:第)?(\d+)\s*座.{0,400}?\$\s*([\d,]+)'
    
    matches = re.finditer(pattern, clean_html)
    found_count = 0
    
    for match in matches:
        try:
            tower = int(match.group(1))
            price = int(match.group(2).replace(',', '')) * 10000
            
            # 嘗試在匹配到的文字周圍找樓層 (低/中/高)
            full_match_text = match.group(0)
            floor = "??"
            f_match = re.search(r'(低|中|高)層', full_match_text)
            if f_match: floor = f_match.group(1)
            
            # 利嘉閣連結 (固定前綴 + 搜尋參數，因為難以從 JSON 抓準確連結)
            link = CONFIG["URL_RICA"]
            desc = f"第{tower}座 (利嘉閣)"

            listing = {
                "id": f"rica-{tower}-{price}",
                "tower": tower, "floor": floor, "unit": "?",
                "price": price, "raw_desc": desc, "url": link,
                "source": "centanet", # 橙色標籤
                "sourceName": "Ricacorp",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                found_count += 1
                log(f"   ✅ Ricacorp: T{tower} ${price/10000}萬")
        except: continue
    
    if found_count == 0:
        log("⚠️ Ricacorp connected but 0 listings found. Structure might differ.")
        
    return listings

# --- Main ---
def main():
    log("🚀 Starting Scraper v18 (JSON Fix)...")
    
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    all_listings = []
    all_listings.extend(scrape_28hse())
    all_listings.extend(scrape_ricacorp())
    
    log(f"📊 Total Found: {len(all_listings)}")
    
    all_listings.sort(key=lambda x: (x['tower'], x['price']))

    # Email
    new_listings = [l for l in all_listings if l["id"] not in seen_ids]
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    
    if new_listings and sender and password:
        subject = f"🔥 天鑽新盤通報 ({len(new_listings)})"
        lines = ["最新放盤 (28Hse + 利嘉閣):", ""]
        for l in new_listings:
            loc = f"{l['floor']}層 {l['unit']}室" if l['unit'] != "?" else ""
            lines.append(f"📍 第 {l['tower']} 座 {loc} | ${l['price']/10000:,.0f}萬 | {l['sourceName']}")
            lines.append(f"   {l['url']}")
            lines.append("")
        lines.append("Dashboard: https://spokenelam.github.io/sky-diamond-tracker/")
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
        msg['Subject'] = subject
        msg.attach(MIMEText("\n".join(lines), 'plain', 'utf-8'))
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender, password)
                server.sendmail(sender, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
            log("📧 Email sent.")
        except: pass

    # Save
    current_ids = list(seen_ids)
    for l in all_listings:
        if l["id"] not in current_ids:
            current_ids.append(l["id"])
            
    Path("data").mkdir(exist_ok=True)
    output_data = {"lastUpdate": datetime.now().isoformat(), "listings": all_listings}
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    cache_data = {"last_run": datetime.now().isoformat(), "seen_ids": current_ids}
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
