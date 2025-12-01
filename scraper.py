#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v21 (28Hse + Squarefoot + Centaline)
三台聯播：嘗試加入中原 (Centaline) 抓取邏輯。
"""

import json
import os
import smtplib
import urllib.request
import re
import time
import random
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
CONFIG = {
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"],
    # 網址設定
    "URL_28HSE": "https://www.28hse.com/buy/a3/dg45/c22902",
    "URL_SQFT": "https://www.squarefoot.com.hk/buy?propertyDoSearchVersion=2.0&searchText=%E5%A4%A9%E9%91%BD&locations=&district_group_hk=&district_group_kw=&district_group_nt=&district_group_islands=&district_group_sch_pri=&district_group_sch_sec=&district_group_university=&price=&price=&mainType=&roomRange=",
    "URL_CENTA": "https://hk.centanet.com/findproperty/list/buy/-%E5%A4%A9%E9%91%BD_2-DEPPWPPJPB"
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
        time.sleep(random.uniform(3, 6)) # 中原需要休息更久
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error ({url}): {e}")
        return None

# =============================================================================
# 1. 28Hse (v14 Cleaner)
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
# 2. Squarefoot (v20)
# =============================================================================
def scrape_squarefoot():
    log("--- Scraping Squarefoot ---")
    html_raw = fetch_url(CONFIG["URL_SQFT"])
    if not html_raw: return []
    if "Security" in html_raw: return []

    listings = []
    clean_html = html_raw.replace('\n', ' ')
    pattern = r'(\d+)\s*座.{0,600}?售\s*\$([\d,]+)'
    matches = re.finditer(pattern, clean_html)
    
    for match in matches:
        try:
            tower = int(match.group(1))
            if tower < 1 or tower > 20: continue 
            price = int(match.group(2).replace(',', '')) * 10000
            
            raw_text = match.group(0)
            floor = "??"
            f_match = re.search(r'(低|中|高)層', raw_text)
            if f_match: floor = f_match.group(1)
            
            link = CONFIG["URL_SQFT"]
            desc = f"第{tower}座 (Squarefoot)"

            listing = {
                "id": f"sqft-{tower}-{price}",
                "tower": tower, "floor": floor, "unit": "?",
                "price": price, "raw_desc": desc, "url": link,
                "source": "hkp", "sourceName": "Squarefoot", # 紫色
                "scrapedAt": datetime.now().isoformat()
            }
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Squarefoot: T{tower} ${price/10000}萬")
        except: continue
    return listings

# =============================================================================
# 3. Centaline (New - 針對 Nuxt 結構)
# =============================================================================
def scrape_centaline():
    log("--- Scraping Centaline ---")
    html_raw = fetch_url(CONFIG["URL_CENTA"])
    if not html_raw: return []
    
    # 檢查是否被 Incapsula 封鎖
    if "Incapsula" in html_raw or "Request unsuccessful" in html_raw:
        log("🚨 Centaline Blocked (Incapsula).")
        return []

    listings = []
    clean_html = html_raw.replace('\n', ' ')
    
    # 中原列表頁通常不顯示座數，只顯示 "實用 XXX呎 ... $XXX萬"
    # 因為網址已經 Filter 左天鑽，所以我地假設抓到既都係天鑽
    
    # Regex: 實用\s*(\d+)呎.{0,200}?\$\s*([\d,]+)萬
    pattern = r'實用\s*(\d+)\s*呎.{0,200}?\$\s*([\d,]+)\s*萬'
    
    matches = re.finditer(pattern, clean_html)
    
    for match in matches:
        try:
            size = int(match.group(1))
            price = int(match.group(2).replace(',', '')) * 10000
            
            # 因為中原列表經常唔寫座數，我地設為 0，等用戶自己 Click 入去睇
            tower = 0 
            
            # 嘗試找樓層 (在匹配文字附近)
            raw_text = match.group(0)
            floor = "??"
            f_match = re.search(r'(低|中|高)層', raw_text) # 中原可能寫在前面，這裡盡量抓
            if f_match: floor = f_match.group(1)

            # 描述
            desc = f"天鑽 (中原盤) {size}呎"
            link = CONFIG["URL_CENTA"]

            listing = {
                "id": f"centa-{size}-{price}", # 用 呎數+價錢 做 ID
                "tower": tower, "floor": floor, "unit": "?",
                "price": price, "raw_desc": desc, "url": link,
                "source": "centanet", # 橙色
                "sourceName": "中原",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Centaline: {size}呎 ${price/10000}萬")
        except: continue
        
    return listings

# --- Main ---
def main():
    log("🚀 Starting Scraper v21 (3-Sources)...")
    
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    all_listings = []
    all_listings.extend(scrape_28hse())     # 28Hse
    all_listings.extend(scrape_squarefoot()) # Squarefoot
    all_listings.extend(scrape_centaline())  # Centaline
    
    log(f"📊 Total Found: {len(all_listings)}")
    
    # Sort: 有座數排先，無座數(0)排後
    all_listings.sort(key=lambda x: (x['tower'] == 0, x['tower'], x['price']))

    # Email
    new_listings = [l for l in all_listings if l["id"] not in seen_ids]
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    
    if new_listings and sender and password:
        subject = f"🔥 天鑽新盤通報 ({len(new_listings)})"
        lines = ["最新放盤 (28Hse/Squarefoot/中原):", ""]
        for l in new_listings:
            t_str = f"第 {l['tower']} 座" if l['tower'] > 0 else "天鑽 (座數未詳)"
            loc = f"{l['floor']}層 {l['unit']}室" if l['unit'] != "?" else ""
            lines.append(f"📍 {t_str} {loc} | ${l['price']/10000:,.0f}萬 | {l['sourceName']}")
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
