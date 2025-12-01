#!/usr/bin/env python3
"""
天鑽 The Regent - Property Listing Tracker
Updated: Loose Filter (Tower Name Only)
"""

import json
import smtplib
import os
import sys
import traceback
import urllib.request
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

def log(msg):
    print(msg, flush=True)

log("=" * 60)
log("天鑽放盤追蹤器 The Regent Listing Tracker")
log(f"時間 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 60)
log("")

# 配置：只保留座數設定，移除面積/房數限制
CONFIG = {
    # 篩選名字有 8,9, 10, 11, 12, 13, 15, 16, 18
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
}

log(f"篩選條件 Filter:")
log(f"  目標座數 Towers: {CONFIG['TARGET_TOWERS']}")
log(f"  其他條件: 無 (只要名稱含座號即抓取)")
log("")

# =============================================================================
# SCRAPER
# =============================================================================

def fetch_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"  ❌ Fetch error: {e}")
        return None

def scrape_28hse():
    log("[28Hse] 抓取中 Scraping...")
    
    url = "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
    html = fetch_url(url)
    
    if not html:
        return []
    
    log(f"  ✅ Fetched {len(html)} bytes")
    
    listings = []
    
    # Updated Regex: 寬鬆模式
    # 只要抓到 "第X座" ... 直到看到 "萬" (價錢)
    # Group 1: 座數
    # Group 2: 中間的描述 (樓層/室/呎數/房) - 全部當作文字存起來
    # Group 3: 價錢
    pattern = r'第\s*(\d+)\s*座(.*?)([\d\.]+)萬'
    
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        try:
            tower_str = match[0]
            description = match[1].strip() # 中間的雜訊或描述
            price_str = match[2]
            
            tower = int(tower_str)
            price = int(float(price_str) * 10000)
            
            # Filter 1: 只檢查座數
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue
            
            # 清理 Description 讓顯示好看一點 (移除多餘換行或標籤)
            clean_desc = re.sub(r'<[^>]+>', ' ', description) # 去除 HTML tags
            clean_desc = re.sub(r'\s+', ' ', clean_desc).strip() # 去除多餘空白
            
            # 嘗試從 Description 提取更多資訊 (僅供顯示，不過濾)
            # 找呎數 (例如 495呎)
            size_match = re.search(r'(\d{3,4})\s*[呎尺]', clean_desc)
            size = int(size_match.group(1)) if size_match else 0
            
            # 找房數
            rooms_match = re.search(r'(\d)\s*[房室]', clean_desc)
            rooms = int(rooms_match.group(1)) if rooms_match else 0
            
            # 找樓層/室 (簡單抓)
            floor_match = re.search(r'(高|中|低|[0-9]+)[樓層]', clean_desc)
            floor = floor_match.group(1) if floor_match else "??"
            
            unit_match = re.search(r'([A-H])室', clean_desc, re.IGNORECASE)
            unit = unit_match.group(1).upper() if unit_match else "?"

            # 建立 ID (用 座數+價錢+描述 hash 避免重複)
            # 因為現在沒有嚴格的 Unit/Floor，用內容特徵做 ID
            unique_str = f"{tower}-{price}-{clean_desc[:20]}"
            listing_id = str(hash(unique_str))[-10:] # 簡單的 Hash ID

            listing = {
                "id": listing_id, # 或是用原本的組合
                "tower": tower,
                "floor": floor,
                "unit": unit,
                "size": size,
                "rooms": rooms,
                "price": price,
                "raw_desc": clean_desc, # 保留原始描述方便查看
                "url": url,
                "scrapedAt": datetime.now().isoformat()
            }
            
            # 避免同一輪重複 (有些網頁會有重複區塊)
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"  📍 第{tower}座 | ${price_str}萬 | {clean_desc[:30]}...")
                
        except Exception as e:
            # log(f"Parsing error: {e}") # Debug use
            continue
    
    log(f"  Found: {len(listings)} matching listings")
    return listings

# =============================================================================
# EMAIL
# =============================================================================

def send_email(subject, body):
    sender = os.environ.get("EMAIL_SENDER", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "").strip()
    
    if not sender or not password:
        log("⚠️ Email not configured (Env vars missing)")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        
        log("✅ Email sent!")
        return True
    except Exception as e:
        log(f"❌ Email error: {e}")
        return False

def send_test_email():
    subject = f"🔔 天鑽 Tracker 啟動測試 - {datetime.now().strftime('%H:%M')}"
    body = "系統運作中。目前沒有偵測到「新」盤，但已更新網站上的現有盤資料。"
    return send_email(subject, body)

def send_listings_email(new_listings, total_count):
    if not new_listings:
        return
    
    subject = f"🏠 天鑽新放盤 ({len(new_listings)}) - {datetime.now().strftime('%m/%d %H:%M')}"
    
    lines = [
        f"天鑽 The Regent - 發現 {len(new_listings)} 個新放盤",
        f"(目前網站共有 {total_count} 個符合座數的放盤)",
        "", 
        "----------------------------------------"
    ]
    
    for i, l in enumerate(new_listings, 1):
        price_show = f"${l['price']/10000:,.1f}萬"
        lines.append(f"【{i}】第 {l['tower']} 座 (HK {price_show})")
        lines.append(f"    描述: {l['raw_desc']}")
        lines.append(f"    連結: {l['url']}")
        lines.append("----------------------------------------")
    
    lines.append("")
    lines.append("完整列表 Dashboard: https://spokenelam.github.io/sky-diamond-tracker/")
    
    send_email(subject, "\n".join(lines))

# =============================================================================
# CACHE & MAIN
# =============================================================================

def load_cache():
    try:
        path = Path(CONFIG["CACHE_FILE"])
        if path.exists():
            data = json.loads(path.read_text())
            return set(data.get("seen_ids", []))
    except:
        pass
    return set()

def save_data(seen_ids, listings):
    Path("data").mkdir(exist_ok=True)
    
    # Cache File: 記錄看過的 ID
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps({
        "last_run": datetime.now().isoformat(),
        "seen_ids": list(seen_ids)
    }, indent=2))
    
    # Output File (For Website): 儲存「所有」抓到的盤，讓網站顯示目前狀況
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps({
        "lastUpdate": datetime.now().isoformat(),
        "listings": listings
    }, ensure_ascii=False, indent=2))
    
    log("💾 Website Data & Cache saved")

def main():
    try:
        seen_ids = load_cache()
        log(f"Cache: {len(seen_ids)} previously seen IDs")
        
        # 1. 抓取所有符合座數的盤 (不論新舊)
        listings = scrape_28hse()
        
        # 2. 找出哪些是「新」的 (不在 Cache 裡)
        new_listings = [l for l in listings if l["id"] not in seen_ids]
        log(f"🆕 New Listings Found: {len(new_listings)}")
        
        # 3. 更新 Cache ID 列表 (將這次抓到的所有 ID 都加入 Cache，防止下次重複寄)
        current_ids = set(seen_ids)
        for l in listings:
            current_ids.add(l["id"])
        
        # 4. 寄 Email 邏輯
        if new_listings:
            log("📧 Sending notification for NEW listings...")
            send_listings_email(new_listings, len(listings))
        else:
            log("💤 No new listings. Skipping email.")
            # 如果你想在完全沒新盤時也收到測試信，可以取消下面這行的註解：
            # send_test_email() 
        
        # 5. 存檔 (包含舊盤，確保網站顯示所有資料)
        save_data(current_ids, listings)
        
        log("✅ Done!")
        
    except Exception as e:
        log(f"❌ ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
