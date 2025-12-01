<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>天鑽放盤監控 | The Regent Listing Tracker</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+HK:wght@300;400;500;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f0f13;
            --bg-secondary: #16161d;
            --bg-card: #1c1c26;
            --accent-gold: #d4af37;
            --accent-gold-dim: #9a7b2a;
            --accent-teal: #00d4aa;
            --accent-red: #ff4757;
            --accent-blue: #4a9eff;
            --text-primary: #ffffff;
            --text-secondary: #9898a8;
            --text-muted: #5a5a6e;
            --border: #2a2a38;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Noto Sans HK', 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 1.5rem; }
        
        /* Header */
        header {
            text-align: center;
            padding: 2rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }
        .logo { font-size: 2.5rem; margin-bottom: 0.5rem; }
        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-gold), #fff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
        }
        .subtitle { color: var(--text-secondary); font-size: 0.95rem; }
        
        /* Status */
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 1.5rem 0;
            flex-wrap: wrap;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .status-dot {
            width: 8px; height: 8px;
            background: var(--accent-teal);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
        
        /* Criteria */
        .criteria {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }
        .criteria-title {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.75rem;
        }
        .criteria-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .tag {
            padding: 0.4rem 0.75rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.85rem;
        }
        .tag.highlight { border-color: var(--accent-gold); color: var(--accent-gold); }
        
        /* Stats */
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-gold);
        }
        .stat-value.teal { color: var(--accent-teal); }
        .stat-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        /* Listings */
        .listings {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }
        .listings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
        }
        .listings-header h2 { font-size: 1rem; font-weight: 600; }
        
        .listing-item {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 1rem;
            align-items: center;
            transition: background 0.2s;
        }
        .listing-item:hover { background: rgba(212,175,55,0.03); }
        .listing-item:last-child { border-bottom: none; }
        
        .listing-main h3 {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .raw-desc {
            display: block;
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            font-weight: normal;
        }
        .new-badge {
            display: inline-block;
            padding: 0.1rem 0.4rem;
            background: var(--accent-red);
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 700;
            color: white;
            vertical-align: middle;
        }
        .listing-details {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .listing-detail { display: flex; align-items: center; gap: 0.25rem; }
        .price { color: var(--accent-gold); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .rooms {
            padding: 0.15rem 0.5rem;
            background: rgba(74,158,255,0.15);
            border-radius: 4px;
            color: var(--accent-blue);
        }
        
        .listing-actions {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 0.5rem;
        }
        .agent {
            padding: 0.35rem 0.7rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.8rem;
        }
        /* Agent colors */
        .agent.centanet { border-color: #ff6b35; color: #ff6b35; }
        .agent.midland { border-color: #00a0e9; color: #00a0e9; }
        .agent.hse28 { border-color: #8bc34a; color: #8bc34a; }
        .agent.hkp { border-color: #9c27b0; color: #9c27b0; }
        
        .view-btn {
            padding: 0.5rem 1rem;
            background: transparent;
            border: 1px solid var(--accent-gold);
            border-radius: 6px;
            color: var(--accent-gold);
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .view-btn:hover { background: var(--accent-gold); color: #000; }
        
        .listing-time { font-size: 0.75rem; color: var(--text-muted); }
        
        /* Empty state */
        .empty {
            padding: 3rem;
            text-align: center;
            color: var(--text-muted);
        }
        .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
        
        /* Sources */
        .sources {
            margin-top: 2rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
        }
        .sources h3 {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }
        .source-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        .source-link {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-primary);
            transition: all 0.2s;
        }
        .source-link:hover { border-color: var(--accent-gold-dim); }
        .source-icon {
            width: 36px; height: 36px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 8px;
            font-size: 1.1rem;
        }
        .source-name { font-weight: 500; font-size: 0.9rem; }
        .source-domain { font-size: 0.75rem; color: var(--text-muted); }
        
        /* Footer */
        footer {
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        footer a { color: var(--accent-gold); text-decoration: none; }
        
        /* Responsive */
        @media (max-width: 640px) {
            .stats { grid-template-columns: 1fr; }
            .source-grid { grid-template-columns: 1fr; }
            .listing-item { grid-template-columns: 1fr; }
            .listing-actions { flex-direction: row; margin-top: 0.5rem; justify-content: space-between; width: 100%; }
            .status-bar { gap: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">💎</div>
            <h1>天鑽放盤監控</h1>
            <p class="subtitle">The Regent Listing Tracker</p>
            
            <div class="status-bar">
                <div class="status-item">
                    <span class="status-dot"></span>
                    <span>自動更新 (Auto-update)</span>
                </div>
                <div class="status-item">
                    <span>🕐</span>
                    <span id="last-update">Loading...</span>
                </div>
            </div>
        </header>
        
        <div class="criteria">
            <div class="criteria-title">目前篩選條件 Filter Criteria</div>
            <div class="criteria-tags">
                <span class="tag highlight">🏢 第 8-13, 15, 16, 18 座</span>
                <span class="tag">📋 顯示所有放盤 (Show All)</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-count">-</div>
                <div class="stat-label">符合條件 Matching</div>
            </div>
            <div class="stat-card">
                <div class="stat-value teal" id="new-count">-</div>
                <div class="stat-label">今日新盤 New Today</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-price">-</div>
                <div class="stat-label">平均呎價 Avg $/ft²</div>
            </div>
        </div>
        
        <div class="listings">
            <div class="listings-header">
                <h2>📋 放盤列表 Listings</h2>
            </div>
            <div id="listings-container">
                <div class="empty">
                    <div class="empty-icon">⏳</div>
                    <p>載入中... Loading...</p>
                </div>
            </div>
        </div>
        
        <div class="sources">
            <h3>🔗 快速連結 Quick Links</h3>
            <div class="source-grid">
                <a href="https://hk.centanet.com/estate/The-Regent/2-DEPPWPPJPB" target="_blank" class="source-link">
                    <div class="source-icon" style="background:rgba(255,107,53,0.15);">🏠</div>
                    <div><div class="source-name" style="color:#ff6b35;">中原地產 Centaline</div></div>
                </a>
                <a href="https://www.midland.com.hk/zh-hk/estate/New-Territories-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-The-Regent-E000016716" target="_blank" class="source-link">
                    <div class="source-icon" style="background:rgba(0,160,233,0.15);">🏠</div>
                    <div><div class="source-name" style="color:#00a0e9;">美聯物業 Midland</div></div>
                </a>
                <a href="https://www.28hse.com/buy/residential/a3/dg45/c22902" target="_blank" class="source-link">
                    <div class="source-icon" style="background:rgba(139,195,74,0.15);">🏠</div>
                    <div><div class="source-name" style="color:#8bc34a;">28Hse</div></div>
                </a>
                <a href="https://www.hkp.com.hk/zh-hk/estate/New-Territories-Tai-Po-The-Regent-E000016716" target="_blank" class="source-link">
                    <div class="source-icon" style="background:rgba(156,39,176,0.15);">🏠</div>
                    <div><div class="source-name" style="color:#9c27b0;">香港置業 HK Property</div></div>
                </a>
            </div>
        </div>
        
        <footer>
            <p>自動監控系統 Automated Tracking System</p>
            <p>Powered by GitHub Actions</p>
        </footer>
    </div>
    
    <script>
        function formatPrice(price) {
            if (price >= 100000000) return `$${(price/100000000).toFixed(2)}億`;
            return `$${(price/10000).toFixed(0)}萬`;
        }
        
        function formatPriceFt(price) {
            return `$${price.toLocaleString()}/呎`;
        }
        
        function timeAgo(dateStr) {
            const date = new Date(dateStr);
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);
            
            if (seconds < 60) return '剛剛 Just now';
            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes}分鐘前 ${minutes}m ago`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}小時前 ${hours}h ago`;
            const days = Math.floor(hours / 24);
            return `${days}日前 ${days}d ago`;
        }
        
        function isToday(dateStr) {
            const date = new Date(dateStr);
            const today = new Date();
            return date.toDateString() === today.toDateString();
        }
        
        function renderListings(listings) {
            const container = document.getElementById('listings-container');
            
            if (!listings || listings.length === 0) {
                container.innerHTML = `
                    <div class="empty">
                        <div class="empty-icon">🏠</div>
                        <p>暫無符合條件嘅放盤</p>
                        <p>No matching listings found</p>
                    </div>`;
                return;
            }
            
            container.innerHTML = listings.map((l, i) => {
                const isNew = isToday(l.scrapedAt);
                
                // 處理可能缺失的資料
                const hasSize = l.size && l.size > 0;
                const hasRooms = l.rooms && l.rooms > 0;
                const floorText = l.floor && l.floor !== '??' ? `${l.floor}樓` : '';
                const unitText = l.unit && l.unit !== '?' ? `${l.unit}室` : '';
                
                // 如果沒有具體樓層/室，顯示原始描述
                const titleText = (floorText || unitText) 
                    ? `第${l.tower}座 ${floorText} ${unitText}`
                    : `第${l.tower}座 (詳細見描述)`;

                return `
                <div class="listing-item">
                    <div class="listing-main">
                        <h3>
                            ${titleText}
                            ${isNew ? '<span class="new-badge">NEW</span>' : ''}
                        </h3>
                        
                        <span class="raw-desc">${l.raw_desc || ''}</span>
                        
                        <div class="listing-details">
                            <span class="listing-detail price">${formatPrice(l.price)}</span>
                            
                            ${hasSize ? `<span class="listing-detail">📐 ${l.size}呎</span>` : ''}
                            ${hasSize ? `<span class="listing-detail">${formatPriceFt(l.pricePerFt)}</span>` : ''}
                            ${hasRooms ? `<span class="rooms">${l.rooms}房</span>` : ''}
                        </div>
                    </div>
                    <div class="listing-actions">
                        <span class="agent ${l.source}">🏢 ${l.sourceName || '28Hse'}</span>
                        <a href="${l.url}" target="_blank" class="view-btn">查看 View →</a>
                        <span class="listing-time">${timeAgo(l.scrapedAt)}</span>
                    </div>
                </div>`;
            }).join('');
        }
        
        function updateStats(listings) {
            document.getElementById('total-count').textContent = listings.length;
            
            const newToday = listings.filter(l => isToday(l.scrapedAt)).length;
            document.getElementById('new-count').textContent = newToday;
            
            // 只計算有呎數資料的放盤
            const validListings = listings.filter(l => l.pricePerFt > 0);
            
            if (validListings.length > 0) {
                const avg = Math.round(validListings.reduce((s,l) => s + l.pricePerFt, 0) / validListings.length);
                document.getElementById('avg-price').textContent = `$${avg.toLocaleString()}`;
            } else {
                document.getElementById('avg-price').textContent = '-';
            }
        }
        
        async function loadData() {
            try {
                // 增加時間參數避免瀏覽器緩存舊的 JSON
                const response = await fetch(`data/listings.json?t=${new Date().getTime()}`);
                const data = await response.json();
                
                document.getElementById('last-update').textContent = 
                    `Last update: ${timeAgo(data.lastUpdate)}`;
                
                const listings = data.listings || [];
                // 排序：新抓取的排前面
                listings.sort((a,b) => new Date(b.scrapedAt) - new Date(a.scrapedAt));
                
                renderListings(listings);
                updateStats(listings);
                
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('listings-container').innerHTML = `
                    <div class="empty">
                        <div class="empty-icon">⚠️</div>
                        <p>無法載入數據 (Failed to load data)</p>
                        <p style="font-size:0.8rem;margin-top:1rem;color:#666;">請稍後再試</p>
                    </div>`;
            }
        }
        
        // Load on page load
        document.addEventListener('DOMContentLoaded', loadData);
        
        // Auto refresh every 5 minutes
        setInterval(loadData, 5 * 60 * 1000);
    </script>
</body>
</html>
