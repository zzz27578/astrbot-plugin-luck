import os

html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>武陵战术数据中枢 - WULING</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <div class="app">
    <aside class="side">
      <section class="block brand">
        <div class="mini">[ ENDFIELD_WULING ARCHIVE ]</div>
        <div class="big-wrap">
          <div class="big">武陵<br>中枢</div>
        </div>
        <div class="row">
          <span class="chip">Ver. 5.4.0</span>
          <span class="chip">[ 核心控制台 ]</span>
        </div>
      </section>

      <section class="block nav">
        <div class="nav-title">[ SEC_INDEX ]</div>
        <div class="nav-list">
          <button class="nav-btn active" data-page="overview">总览与方案<small>PROFILE / ACCESS</small></button>
          <button class="nav-btn" data-page="runtime">运行配置<small>RUNTIME / PROBABILITY</small></button>
          <button class="nav-btn" data-page="signin">签到配置<small>SIGN_IN / FORECAST</small></button>
          <button class="nav-btn" data-page="fate">命运牌档案<small>FATE_MATRIX / ASSETS</small></button>
          <button class="nav-btn" data-page="cards">功能牌档案<small>FUNC_CARDS / EFFECTS</small></button>
          <button class="nav-btn" data-page="titles">称号档案<small>TITLES / CONDITIONS</small></button>
          <button class="nav-btn" data-page="stats">数据统计<small>DATA_STATS / RANKS</small></button>
        </div>
      </section>

      <section class="block current">
        <div class="subtle-label">[ ACTIVE_PROFILE ]</div>
        <div class="name" id="currentProfileName">加载中...</div>
        <div class="helper">全局参数自动跟随当前活跃方案同步。</div>
      </section>
      
      <!-- Structural Tonal Shift Right Edge -->
      <div class="side-edge"></div>
    </aside>

    <main class="main">
      <section class="hero">
        <div>
          <div class="kicker">[ TERRA WEB UI / ARCHIVE CONTROL ]</div>
          <h1 id="heroTitle">总览与方案</h1>
          <p id="heroDesc">管理活跃协议配置与群组访问权限。</p>
        </div>
        <div class="hero-side">
          <div class="hero-aux" id="heroAux"></div>
          <div class="toolbar">
            <button class="btn toolbar-btn refresh-btn" id="reloadBtn">RELOAD</button>
            <button class="btn btn-strong toolbar-btn save-btn clip-bevel" id="saveAllBtn">SAVE_SYNC</button>
          </div>
        </div>
      </section>

      <section class="pages">
        <div class="page active" id="page-overview"></div>
        <div class="page" id="page-runtime"></div>
        <div class="page" id="page-signin"></div>
        <div class="page" id="page-fate"></div>
        <div class="page" id="page-cards"></div>
        <div class="page" id="page-titles"></div>
        <div class="page" id="page-stats"></div>
      </section>
    </main>
  </div>

  <div class="dialog" id="dialog">
    <div class="dialog-card clip-bevel-card">
      <div class="dialog-head">
        <div>
          <div class="tiny">[ TERMINAL_EDITOR ]</div>
          <div class="dialog-title" id="dialogTitle">编辑器</div>
        </div>
        <button class="btn" id="closeDialogBtn">[ CLOSE ]</button>
      </div>
      <div id="dialogBody"></div>
    </div>
  </div>

  <div class="toast clip-bevel" id="toast"></div>

  <script src="/static/js/main.js"></script>
</body>
</html>
"""

css_content = """@charset "UTF-8";

:root {
  /* Colors - "Clinical Greenhouse" */
  --primary-container: #152419; /* 深邃生命绿 (Sidebar) */
  --on-primary-container: #a2bba9;
  --secondary-fixed: #5FF2D0; /* 数据脉冲青 (Accents) */
  --on-secondary-fixed: #002019;
  --surface-lowest: #ffffff; /* 无菌区 (Panels/Cards) */
  --surface-low: #f0f3f1; /* 背景区 */
  --surface-high: #e2e8e4; /* 稍微凸起的底色 */
  --on-surface: #191c1c;
  --on-surface-variant: #434843;
  --outline: #737973;
  --outline-variant: #ced4d0;
  --danger: #ba1a1a;
  
  /* Fonts */
  --font-headline: 'Space Grotesk', "Source Han Sans SC", "Microsoft YaHei", sans-serif;
  --font-body: 'Inter', "Source Han Sans SC", "Microsoft YaHei", sans-serif;
  
  --ease: cubic-bezier(.22, 1, .36, 1);
}

* { box-sizing: border-box; margin: 0; padding: 0; border-radius: 0 !important; }

html, body { min-height: 100%; color-scheme: light; }
body {
  font-family: var(--font-body);
  color: var(--on-surface);
  background-color: var(--surface-low);
  overflow-x: hidden;
}

/* Ink Wash & Technical Grid Background */
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none;
  background: 
    linear-gradient(var(--outline-variant) 1px, transparent 1px),
    linear-gradient(90deg, var(--outline-variant) 1px, transparent 1px);
  background-size: 40px 40px; opacity: 0.15; z-index: -1;
}

/* Base Layout */
.app {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 100vh;
}

/* ========= SIDEBAR (The Organic Core) ========= */
.side {
  background: var(--primary-container);
  color: var(--surface-lowest);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  padding: 32px 0;
}
.side-edge {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px;
  background: rgba(0,0,0,0.2);
}
.block { border: none; background: transparent; padding: 0 24px; margin-bottom: 32px; box-shadow: none; }

.brand .mini { font-family: var(--font-headline); color: var(--secondary-fixed); letter-spacing: 2px; font-size: 10px; margin-bottom: 12px; }
.brand .big { font-family: var(--font-headline); font-size: 42px; font-weight: 900; line-height: 1; text-transform: uppercase; color: var(--surface-lowest); letter-spacing: -1px; }
.brand .bar { display: none; }
.brand .row { display: flex; gap: 8px; margin-top: 16px; }
.chip { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: var(--secondary-fixed); padding: 4px 8px; font-size: 10px; font-family: var(--font-headline); clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%); }

.nav-title { font-family: var(--font-headline); color: var(--on-primary-container); font-size: 11px; letter-spacing: 2px; margin-bottom: 16px; }
.nav-list { display: grid; gap: 4px; }
.nav-btn { background: transparent; border: none; color: var(--on-primary-container); text-align: left; padding: 12px 16px; cursor: pointer; transition: 0.2s; font-family: var(--font-headline); font-size: 13px; font-weight: 600; letter-spacing: 1px; width: 100%; position: relative; }
.nav-btn small { display: block; font-family: var(--font-body); font-size: 10px; opacity: 0.6; font-weight: 400; margin-top: 4px; letter-spacing: 0; }
.nav-btn:hover { background: rgba(255,255,255,0.05); color: var(--surface-lowest); border-left: 4px solid var(--secondary-fixed); padding-left: 20px; }
.nav-btn.active { background: var(--secondary-fixed); color: var(--on-secondary-fixed); clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px); padding-left: 16px; }
.nav-btn.active small { color: var(--on-secondary-fixed); opacity: 0.8; }

.current { border-top: 1px solid rgba(255,255,255,0.05); padding-top: 24px; margin-top: auto; margin-bottom: 0; }
.subtle-label { font-family: var(--font-headline); color: var(--secondary-fixed); font-size: 10px; letter-spacing: 2px; }
.current .name { font-family: var(--font-headline); font-size: 20px; font-weight: 700; margin: 8px 0; color: var(--surface-lowest); }
.current .helper { font-size: 11px; color: var(--on-primary-container); line-height: 1.6; }

/* ========= MAIN CONTENT (The Clinical Environment) ========= */
.main { display: flex; flex-direction: column; position: relative; }
.main::after { content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 50% 50%, rgba(27,48,34,0.015) 0%, transparent 60%); pointer-events: none; }

.hero { background: var(--surface-lowest); padding: 32px 48px; border-bottom: 2px solid var(--primary-container); display: flex; justify-content: space-between; align-items: flex-end; position: relative; z-index: 2; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
.hero .kicker { font-family: var(--font-headline); font-size: 11px; color: var(--outline); letter-spacing: 2px; margin-bottom: 12px; }
.hero h1 { font-family: var(--font-headline); font-size: 40px; font-weight: 900; color: var(--primary-container); line-height: 1; letter-spacing: -1px; }
.hero p { font-size: 13px; color: var(--on-surface-variant); margin-top: 12px; max-width: 600px; line-height: 1.6; }

.toolbar { display: flex; gap: 12px; }
.toolbar-btn { font-family: var(--font-headline); font-size: 12px; font-weight: 700; padding: 0 24px; height: 44px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; letter-spacing: 1px; transition: 0.2s; border: 1px solid var(--outline-variant); background: var(--surface-lowest); color: var(--primary-container); }
.toolbar-btn:hover { background: var(--surface-low); border-color: var(--primary-container); }
.save-btn { background: var(--primary-container); color: var(--surface-lowest); border: none; }
.save-btn:hover { background: var(--secondary-fixed); color: var(--on-secondary-fixed); }

/* Clip Path Utilities */
.clip-bevel { clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }
.clip-bevel-card { clip-path: polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px); }

/* Grid Layouts */
.pages { padding: 32px 48px; position: relative; z-index: 2; flex: 1; }
.page { display: none; gap: 24px; }
.page.active { display: grid; }
.grid { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: 24px; }
.col-12 { grid-column: span 12; } .col-8 { grid-column: span 8; } .col-7 { grid-column: span 7; } .col-6 { grid-column: span 6; } .col-5 { grid-column: span 5; } .col-4 { grid-column: span 4; }

/* Panels */
.panel { background: var(--surface-lowest); border: 1px solid var(--outline-variant); padding: 24px; position: relative; }
.panel-head { border-bottom: 2px solid var(--primary-container); padding-bottom: 12px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
.panel-title { font-family: var(--font-headline); font-size: 20px; font-weight: 800; color: var(--primary-container); }
.panel-note { font-size: 12px; color: var(--on-surface-variant); margin-top: 8px; line-height: 1.6; }

/* Form Fields (Terminal Inputs) */
.input, .textarea, .select { width: 100%; border: none; border-bottom: 2px solid var(--primary-container); background: var(--surface-low); color: var(--on-surface); padding: 12px 16px; outline: none; font-family: var(--font-body); font-size: 13px; transition: 0.2s; }
.textarea { min-height: 100px; resize: vertical; }
.input:focus, .textarea:focus, .select:focus { border-bottom-color: var(--secondary-fixed); background: color-mix(in srgb, var(--secondary-fixed) 8%, var(--surface-low)); }
.field { display: grid; gap: 8px; }
.field label { font-family: var(--font-headline); font-size: 11px; font-weight: 700; color: var(--primary-container); letter-spacing: 1px; text-transform: uppercase; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.field-grid.three { grid-template-columns: repeat(3, minmax(0,1fr)); }
.field-grid.four { grid-template-columns: repeat(4, minmax(0,1fr)); }

/* Buttons */
.btn, .btn-strong, .btn-danger, .btn-mini, .mode-btn { font-family: var(--font-headline); font-size: 11px; font-weight: 700; padding: 10px 16px; cursor: pointer; letter-spacing: 1px; transition: 0.2s; border: 1px solid var(--outline-variant); background: var(--surface-lowest); color: var(--primary-container); display: inline-flex; justify-content: center; align-items: center; }
.btn:hover { background: var(--surface-low); border-color: var(--primary-container); }
.btn-strong { background: var(--primary-container); color: var(--surface-lowest); border-color: var(--primary-container); clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px); }
.btn-strong:hover { background: var(--secondary-fixed); color: var(--on-secondary-fixed); border-color: var(--secondary-fixed); }
.btn-danger { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
.btn-danger:hover { background: var(--danger); color: white; }

/* Lists & Cards */
.stack { display: grid; gap: 16px; }
.row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }

/* Profile Card */
.profile-card, .event-item, .effect-row { background: var(--surface-lowest); border: 1px solid var(--outline-variant); padding: 20px; transition: 0.2s; position: relative; }
.profile-card:hover { border-color: var(--primary-container); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.04); }
.profile-card.active { border-color: var(--secondary-fixed); border-left: 4px solid var(--secondary-fixed); background: color-mix(in srgb, var(--secondary-fixed) 5%, var(--surface-lowest)); }
.profile-card h3 { font-family: var(--font-headline); font-size: 18px; font-weight: 800; color: var(--primary-container); margin-bottom: 6px; }
.profile-card .meta, .profile-card .helper { font-size: 12px; color: var(--on-surface-variant); margin-bottom: 12px; }
.badge { display: inline-flex; padding: 4px 8px; font-family: var(--font-headline); font-size: 10px; font-weight: 700; letter-spacing: 1px; background: var(--surface-high); color: var(--on-surface); border: 1px solid var(--outline-variant); }

/* Switch / Toggle */
.toggle-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 16px; border: 1px solid var(--outline-variant); background: var(--surface-lowest); margin-bottom: 12px; }
.toggle-copy .helper { font-size: 12px; color: var(--on-surface-variant); margin-top: 6px; line-height: 1.5; }
.toggle-box { width: 44px; height: 24px; background: var(--surface-high); border: 1px solid var(--outline-variant); position: relative; cursor: pointer; transition: 0.2s; flex-shrink: 0; }
.toggle-box::before { content: ""; position: absolute; left: 2px; top: 2px; width: 18px; height: 18px; background: var(--outline); transition: 0.2s; }
.toggle-box.on { background: var(--primary-container); border-color: var(--primary-container); }
.toggle-box.on::before { transform: translateX(20px); background: var(--secondary-fixed); }

/* Archive Cards */
.archive-grid, .pending-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
.archive-card { background: var(--surface-lowest); border: 1px solid var(--outline-variant); display: flex; flex-direction: column; transition: 0.2s; position: relative; isolation: isolate; }
.archive-card::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 4px; background: var(--outline-variant); z-index: 2; transition: 0.2s; }
.archive-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.06); border-color: var(--primary-container); }
.archive-card:hover::before { background: var(--secondary-fixed); }

.archive-cover { aspect-ratio: 3/4; background: var(--surface-low); border-bottom: 1px solid var(--outline-variant); padding: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.archive-cover img { width: 100%; height: 100%; object-fit: cover; border: 1px solid var(--outline-variant); }
.archive-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; flex: 1; }
.archive-title { font-family: var(--font-headline); font-size: 16px; font-weight: 800; color: var(--primary-container); }
.archive-desc { font-size: 12px; color: var(--on-surface-variant); background: var(--surface-low); padding: 12px; border: 1px solid var(--outline-variant); border-left: 2px solid var(--primary-container); }
.archive-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: auto; padding-top: 16px; border-top: 1px solid var(--outline-variant); }
.archive-actions .btn { padding: 8px 0; font-size: 10px; text-align: center; }

/* Stats Widgets */
.overview-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 24px; }
.overview-stat { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 20px; border-left: 4px solid var(--secondary-fixed); position: relative; }
.overview-stat b { font-family: var(--font-headline); font-size: 28px; font-weight: 900; color: var(--primary-container); display: block; margin-bottom: 4px; }
.overview-stat span { font-size: 11px; color: var(--on-surface-variant); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; font-family: var(--font-headline); }

/* Dialog */
.dialog { position: fixed; inset: 0; background: rgba(21, 36, 25, 0.8); backdrop-filter: blur(8px); z-index: 100; display: none; align-items: center; justify-content: center; padding: 24px; }
.dialog.show { display: flex; }
.dialog-card { background: var(--surface-lowest); border: 1px solid var(--primary-container); width: min(1000px, 100%); max-height: 90vh; overflow-y: auto; padding: 40px; box-shadow: 0 24px 64px rgba(0,0,0,0.15); }
.dialog-head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid var(--primary-container); padding-bottom: 16px; margin-bottom: 32px; }
.dialog-title { font-family: var(--font-headline); font-size: 24px; font-weight: 900; color: var(--primary-container); }
.tiny { font-family: var(--font-headline); font-size: 11px; color: var(--outline); letter-spacing: 2px; margin-bottom: 4px; }

/* Toast */
.toast { position: fixed; right: 32px; bottom: 32px; background: var(--primary-container); color: var(--surface-lowest); padding: 16px 24px; font-family: var(--font-body); font-size: 13px; font-weight: 500; z-index: 200; box-shadow: 0 12px 32px rgba(0,0,0,0.15); opacity: 0; transform: translateY(20px); transition: 0.3s; border-left: 4px solid var(--secondary-fixed); }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.bad { border-left-color: var(--danger); }

/* Misc Elements mapping */
.thumb { width: 80px; height: 80px; border: 1px solid var(--outline-variant); background: var(--surface-low); overflow: hidden; display: flex; align-items: center; justify-content: center; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.asset-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tag-preview, .empty { background: var(--surface-low); border: 1px dashed var(--outline-variant); padding: 20px; text-align: center; font-size: 12px; color: var(--on-surface-variant); }
.filter-bar { display: flex; gap: 16px; align-items: center; padding: 16px; background: var(--surface-lowest); border: 1px solid var(--outline-variant); margin-bottom: 20px; }
.stats-profile-bar { border-bottom: 1px solid var(--outline-variant); padding-bottom: 16px; margin-bottom: 24px; }
.stats-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stats-kpi { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 20px; border-left: 4px solid var(--primary-container); }
.group-entry, .leaderboard-item { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 16px; margin-bottom: 12px; }
.pool-card { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 20px; border-top: 4px solid var(--primary-container); }

/* Rarity Legend Adjustments for Light Theme */
.rarity-ring { width: 200px; height: 200px; border-radius: 50% !important; border: 8px solid var(--surface-low); position: relative; box-shadow: 0 0 0 1px var(--outline-variant); margin: 0 auto; }
.rarity-ring-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.rarity-ring-center b { font-family: var(--font-headline); font-size: 32px; color: var(--primary-container); }
.rarity-ring-center span { font-size: 10px; font-weight: 700; letter-spacing: 1px; color: var(--outline); }
"""

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

with open('webui/static/styles.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

print("UI Theme Applied Successfully!")
"""