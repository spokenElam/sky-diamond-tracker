#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v19 (28Hse + House730 + Ricacorp Debug)
加入 House730 作為新來源，並對利嘉閣進行連線檢測。
"""

import json
import os
import smtplib
import urllib.request
import re
import time
import random
import html
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
    "URL_RICA": "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%A4%A9%E9%91%BD-estate-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-hma-hk",
    "URL_H730": "https://www.house730.com/buy/s/%E5%A4%A9%E9%91%BD/"
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
        time.sleep(random.uniform(2, 5))
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error ({url}): {e}")
        return None

# =============================================================================
# 1. 28Hse (v14 Cleaner Version - 保持完美)
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
            
            # 抓資料
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
# 2. House730 (New)
# =============================================================================
def scrape_house730():
    log("--- Scraping House730 ---")
    html_raw = fetch_url(CONFIG["URL_H730"])
    if not html_raw: return []
    
    # 檢查標題
    if "Cloudflare" in html_raw or "Security" in html_raw:
        log("🚨 House730 Blocked by Cloudflare.")
        return []

    listings = []
    # House730 結構通常係 "item-mod" 或類似
    # 我地用通用暴力搜尋法，因為 House730 格式比較標準
    
    clean_html = html_raw.replace('\n', ' ')
    
    # 尋找: 天鑽...座...萬
    # Regex: 天鑽\s*(?:第)?(\d+)座.{0,200}?\$([\d,]+)萬
    matches = re.finditer(r'天鑽\s*(?:第)?(\d+)座.{0,200}?\$([\d,]+)萬', clean_html)
    
    found_count = 0
    for match in matches:
        try:
            tower = int(match.group(1))
            price = int(match.group(2).replace(',', '')) * 10000
            
            # 抓連結 (往回找 href)
            # 由於 regex 抓唔到 href，我地用列表頁做 link
            link = CONFIG["URL_H730"]
            
            desc = f"第{tower}座 (House730)"
            
            listing = {
                "id": f"h730-{tower}-{price}",
                "tower": tower, "floor": "??", "unit": "?",
                "price": price, "raw_desc": desc, "url": link,
                "source": "hkp", # 用紫色 (借用 hkp style)
                "sourceName": "House730",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                found_count += 1
                log(f"   ✅ House730: T{tower} ${price/10000}萬")
        except: continue
        
    if found_count == 0:
        log("⚠️ House730 found 0 items. (Maybe Regex mismatch or no listings)")
        
    return listings

# =============================================================================
# 3. Ricacorp (Debug Mode)
# =============================================================================
def scrape_ricacorp():
    log("--- Scraping Ricacorp (Diagnostic) ---")
    html_raw = fetch_url(CONFIG["URL_RICA"])
    if not html_raw: return []
    
    # 【DEBUG】印出標題，確認是否被 Block
    title_match = re.search(r'<title>(.*?)</title>', html_raw, re.IGNORECASE)
    page_title = title_match.group(1) if title_match else "Unknown"
    log(f"   [Ricacorp Page Title]: {page_title}")
    
    if "Security" in page_title or "Just a moment" in page_title:
        log("🚨 Ricacorp is serving a Challenge Page (Blocked).")
        return []

    # 嘗試抓取 (如果無 Block)
    listings = []
    clean_html = html.unescape(html_raw).replace('\n', ' ')
    
    # 嘗試極寬鬆 Regex: 數字+座 ... $數字
    pattern = r'(\d+)\s*座.{0,1000}?\$\s*([\d,]+)'
    matches = re.finditer(pattern, clean_html)
    
    found_count = 0
    for match in matches:
        try:
            tower = int(match.group(1))
            # 過濾：只抓 8-19 座，避免抓到雜訊 (例如 "3座" 可能係其他野)
            if tower < 8 or tower > 19: continue
            
            price = int(match.group(2).replace(',', '')) * 10000
            if price < 4000000: continue # 避免抓到租盤 ($18,000)

            link = CONFIG["URL_RICA"]
            desc = f"第{tower}座 (利嘉閣)"

            listing = {
                "id": f"rica-{tower}-{price}",
                "tower": tower, "floor": "??", "unit": "?",
                "price": price, "raw_desc": desc, "url": link,
                "source": "centanet", # 橙色
                "sourceName": "Ricacorp",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                found_count += 1
                log(f"   ✅ Ricacorp: T{tower} ${price/10000}萬")
        except: continue
        
    return listings

# --- Main ---
def main():
    log("🚀 Starting Scraper v19 (Multi-Source)...")
    
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    all_listings = []
    all_listings.extend(scrape_28hse())
    all_listings.extend(scrape_house730())
    all_listings.extend(scrape_ricacorp())
    
    log(f"📊 Total Found: {len(all_listings)}")
    
    all_listings.sort(key=lambda x: (x['tower'], x['price']))

    # Email
    new_listings = [l for l in all_listings if l["id"] not in seen_ids]
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    
    if new_listings and sender and password:
        subject = f"🔥 天鑽新盤通報 ({len(new_listings)})"
        lines = ["最新放盤:", ""]
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
