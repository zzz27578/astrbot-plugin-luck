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
      <!-- Top tactical decorations -->
      <div class="side-top-dec">
        <div class="blink-dot"></div>
        <span>SYS.OP.NOMINAL // UPLINK SECURE</span>
      </div>

      <section class="block brand">
        <div class="mini">[ ENDFIELD_WULING ARCHIVE ]</div>
        <div class="big-wrap">
          <div class="big">武陵<br>中枢</div>
        </div>
        <div class="row">
          <span class="chip">Ver. 5.4.0</span>
          <span class="chip">[ CORE_TERMINAL ]</span>
        </div>
      </section>

      <section class="block nav">
        <div class="nav-title">[ SEC_INDEX ]</div>
        <div class="nav-list">
          <button class="nav-btn active" data-page="overview">
            <div class="nav-btn-dec"></div>
            总览与方案<small>PROFILE / ACCESS</small>
          </button>
          <button class="nav-btn" data-page="runtime">
            <div class="nav-btn-dec"></div>
            运行配置<small>RUNTIME / PROBABILITY</small>
          </button>
          <button class="nav-btn" data-page="signin">
            <div class="nav-btn-dec"></div>
            签到配置<small>SIGN_IN / FORECAST</small>
          </button>
          <button class="nav-btn" data-page="fate">
            <div class="nav-btn-dec"></div>
            命运牌档案<small>FATE_MATRIX / ASSETS</small>
          </button>
          <button class="nav-btn" data-page="cards">
            <div class="nav-btn-dec"></div>
            功能牌档案<small>FUNC_CARDS / EFFECTS</small>
          </button>
          <button class="nav-btn" data-page="titles">
            <div class="nav-btn-dec"></div>
            称号档案<small>TITLES / CONDITIONS</small>
          </button>
          <button class="nav-btn" data-page="stats">
            <div class="nav-btn-dec"></div>
            数据统计<small>DATA_STATS / RANKS</small>
          </button>
        </div>
      </section>

      <section class="block current">
        <div class="subtle-label">[ ACTIVE_PROFILE ]</div>
        <div class="name" id="currentProfileName">加载中...</div>
        <div class="helper">GLOBAL_SYNC // 全局参数自动跟随当前活跃方案同步。</div>
      </section>
      
      <!-- Structural Tonal Shift Right Edge -->
      <div class="side-edge"></div>
      <div class="side-bottom-dec">
         <span>WULING_TECH_SYS // 2026.0</span>
      </div>
    </aside>

    <main class="main">
      <div class="main-top-bar">
         <div class="line-run"></div>
         <span>DATA_STREAM_ACTIVE /// LOCATION: LOCALHOST</span>
      </div>

      <section class="hero">
        <div>
          <div class="kicker">[ TERRA WEB UI / ARCHIVE CONTROL ]</div>
          <h1 id="heroTitle">总览与方案</h1>
          <p id="heroDesc">管理活跃协议配置与群组访问权限。</p>
        </div>
        <div class="hero-side">
          <div class="hero-aux" id="heroAux"></div>
          <div class="toolbar">
            <button class="btn toolbar-btn refresh-btn tactical-corners" id="reloadBtn">
                <span class="btn-icon">↻</span> RELOAD
            </button>
            <button class="btn btn-strong toolbar-btn save-btn clip-bevel" id="saveAllBtn">
                SAVE_SYNC <span class="btn-dec">+</span>
            </button>
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
    <div class="dialog-card clip-bevel-card tactical-corners-lg">
      <div class="dialog-head">
        <div>
          <div class="tiny">[ TERMINAL_EDITOR ]</div>
          <div class="dialog-title" id="dialogTitle">编辑器</div>
        </div>
        <button class="btn tactical-corners" id="closeDialogBtn">[ CLOSE ]</button>
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
  /* Colors - Deepened Palette */
  --primary-container: #111d15; /* 更深的黑绿，增加厚重感 */
  --on-primary-container: #779682;
  --secondary-fixed: #39e5b8; /* 更刺眼的青色，增强脉冲感 */
  --secondary-glow: rgba(57, 229, 184, 0.25);
  --on-secondary-fixed: #002b21;
  
  --surface-lowest: #ffffff; 
  --surface-low: #edf1ef; /* 稍微偏冷灰，带点机能感 */
  --surface-high: #e0e5e2;
  --on-surface: #141716;
  --on-surface-variant: #4a524e;
  
  --outline: #89938d;
  --outline-variant: #c3cac6;
  --danger: #d93829;
  --danger-glow: rgba(217, 56, 41, 0.2);
  
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
  position: relative;
}

/* ================= ENVIRONMENTAL EFFECTS ================= */
/* 密集的点阵网格，增加科技纵深感 */
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none;
  background-image: radial-gradient(var(--outline-variant) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.3;
  z-index: -1;
}
/* 光影晕染：让画面不再扁平 */
body::after {
  content: ""; position: fixed; inset: 0; pointer-events: none;
  background: radial-gradient(circle at 70% 30%, rgba(255,255,255,0.8) 0%, transparent 60%),
              radial-gradient(circle at 30% 80%, rgba(57, 229, 184, 0.05) 0%, transparent 50%);
  z-index: -1;
}

/* Base Layout */
.app {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 100vh;
}

/* ========= SIDEBAR (The Organic Core) ========= */
.side {
  background: linear-gradient(180deg, var(--primary-container) 0%, #0d1610 100%);
  color: var(--surface-lowest);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  padding: 0 0 24px 0;
  box-shadow: 4px 0 24px rgba(0,0,0,0.1);
}
.side-top-dec {
  display: flex; align-items: center; gap: 8px; padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,0.05);
  font-family: var(--font-headline); font-size: 9px; color: var(--on-primary-container); letter-spacing: 2px;
}
.blink-dot {
  width: 6px; height: 6px; background: var(--secondary-fixed); border-radius: 50% !important;
  box-shadow: 0 0 8px var(--secondary-fixed);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

.side-bottom-dec {
  margin-top: 16px; padding: 0 24px;
  font-family: var(--font-headline); font-size: 9px; color: rgba(255,255,255,0.15); letter-spacing: 2px;
}

.side-edge {
  position: absolute; right: 0; top: 0; bottom: 0; width: 2px;
  background: linear-gradient(180deg, transparent, var(--secondary-fixed), transparent);
  opacity: 0.3;
}
.block { border: none; background: transparent; padding: 0 24px; margin-top: 32px; box-shadow: none; }

.brand .mini { font-family: var(--font-headline); color: var(--secondary-fixed); letter-spacing: 2px; font-size: 10px; margin-bottom: 12px; font-weight: 700; }
.brand .big { font-family: var(--font-headline); font-size: 42px; font-weight: 900; line-height: 0.9; text-transform: uppercase; color: var(--surface-lowest); letter-spacing: -2px; }
.brand .row { display: flex; gap: 8px; margin-top: 16px; }
.chip { background: rgba(57, 229, 184, 0.1); border: 1px solid rgba(57, 229, 184, 0.3); color: var(--secondary-fixed); padding: 4px 8px; font-size: 10px; font-family: var(--font-headline); clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%); font-weight: 700; letter-spacing: 1px;}

.nav-title { font-family: var(--font-headline); color: rgba(255,255,255,0.3); font-size: 10px; letter-spacing: 3px; margin-bottom: 16px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 8px; }
.nav-list { display: grid; gap: 4px; }
.nav-btn { background: transparent; border: none; color: var(--on-primary-container); text-align: left; padding: 12px 16px; cursor: pointer; transition: 0.2s; font-family: var(--font-headline); font-size: 12px; font-weight: 600; letter-spacing: 1px; width: 100%; position: relative; display: flex; flex-direction: column; }
.nav-btn .nav-btn-dec { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: transparent; transition: 0.2s; }
.nav-btn small { font-family: var(--font-body); font-size: 9px; opacity: 0.5; font-weight: 500; margin-top: 4px; letter-spacing: 0; text-transform: uppercase; }
.nav-btn:hover { background: rgba(255,255,255,0.02); color: var(--surface-lowest); padding-left: 20px; }
.nav-btn:hover .nav-btn-dec { background: rgba(255,255,255,0.2); }
.nav-btn.active { background: linear-gradient(90deg, rgba(57, 229, 184, 0.1), transparent); color: var(--secondary-fixed); padding-left: 20px; }
.nav-btn.active .nav-btn-dec { background: var(--secondary-fixed); box-shadow: 0 0 10px var(--secondary-fixed); }
.nav-btn.active small { color: var(--surface-lowest); opacity: 0.8; }

.current { border-top: 1px solid rgba(255,255,255,0.05); padding-top: 24px; margin-top: auto; margin-bottom: 0; }
.subtle-label { font-family: var(--font-headline); color: var(--secondary-fixed); font-size: 10px; letter-spacing: 2px; }
.current .name { font-family: var(--font-headline); font-size: 18px; font-weight: 700; margin: 8px 0; color: var(--surface-lowest); }
.current .helper { font-size: 10px; color: var(--on-primary-container); line-height: 1.6; font-family: var(--font-headline); }

/* ========= MAIN CONTENT (The Clinical Environment) ========= */
.main { display: flex; flex-direction: column; position: relative; }
.main-top-bar {
  height: 24px; border-bottom: 1px solid var(--outline-variant); display: flex; align-items: center; padding: 0 48px; gap: 12px;
}
.main-top-bar .line-run { width: 100px; height: 2px; background: var(--secondary-fixed); box-shadow: 0 0 8px var(--secondary-fixed); }
.main-top-bar span { font-family: var(--font-headline); font-size: 9px; color: var(--outline); letter-spacing: 2px; font-weight: 700; }

.hero { background: linear-gradient(180deg, rgba(255,255,255,0.8), rgba(255,255,255,0.2)), var(--surface-lowest); padding: 32px 48px; border-bottom: 1px solid var(--outline-variant); display: flex; justify-content: space-between; align-items: flex-end; position: relative; z-index: 2; box-shadow: 0 10px 30px rgba(0,0,0,0.02); }
.hero::after { content: ""; position: absolute; left: 0; bottom: -1px; width: 160px; height: 3px; background: var(--primary-container); }
.hero .kicker { font-family: var(--font-headline); font-size: 10px; color: var(--outline); letter-spacing: 3px; margin-bottom: 12px; font-weight: 700; }
.hero h1 { font-family: var(--font-headline); font-size: 36px; font-weight: 900; color: var(--primary-container); line-height: 1; letter-spacing: -1px; }
.hero p { font-size: 13px; color: var(--on-surface-variant); margin-top: 12px; max-width: 600px; line-height: 1.6; font-weight: 500; }

.toolbar { display: flex; gap: 12px; }
.toolbar-btn { font-family: var(--font-headline); font-size: 12px; font-weight: 700; padding: 0 24px; height: 42px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer; letter-spacing: 1px; transition: 0.2s; border: 1px solid var(--outline-variant); background: var(--surface-lowest); color: var(--primary-container); position: relative; }
.toolbar-btn:hover { background: var(--surface-high); border-color: var(--primary-container); }
.toolbar-btn .btn-icon { font-size: 14px; }
.save-btn { background: var(--primary-container); color: var(--surface-lowest); border: 1px solid var(--primary-container); }
.save-btn .btn-dec { color: var(--secondary-fixed); font-weight: 900; }
.save-btn:hover { background: var(--secondary-fixed); color: var(--on-secondary-fixed); border-color: var(--secondary-fixed); box-shadow: 0 0 16px var(--secondary-glow); }

/* Clip Path & Tactical Borders Utilities */
.clip-bevel { clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }
.clip-bevel-card { clip-path: polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px); }

/* Tactical Corners (模拟四角的包边) */
.tactical-corners::before, .tactical-corners::after { content: ""; position: absolute; width: 6px; height: 6px; border: 2px solid var(--primary-container); pointer-events: none; }
.tactical-corners::before { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.tactical-corners::after { bottom: -1px; right: -1px; border-left: none; border-top: none; }

.tactical-corners-lg::before, .tactical-corners-lg::after { content: ""; position: absolute; width: 12px; height: 12px; border: 3px solid var(--primary-container); pointer-events: none; }
.tactical-corners-lg::before { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.tactical-corners-lg::after { bottom: -1px; right: -1px; border-left: none; border-top: none; }

/* Grid Layouts */
.pages { padding: 32px 48px; position: relative; z-index: 2; flex: 1; }
.page { display: none; gap: 24px; }
.page.active { display: grid; }
.grid { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: 24px; }
.col-12 { grid-column: span 12; } .col-8 { grid-column: span 8; } .col-7 { grid-column: span 7; } .col-6 { grid-column: span 6; } .col-5 { grid-column: span 5; } .col-4 { grid-column: span 4; }

/* Panels (赋予更多的仪器感) */
.panel { background: rgba(255,255,255,0.7); backdrop-filter: blur(10px); border: 1px solid var(--outline-variant); padding: 24px; position: relative; }
.panel-head { border-bottom: 2px solid var(--primary-container); padding-bottom: 12px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
.panel-title { font-family: var(--font-headline); font-size: 20px; font-weight: 800; color: var(--primary-container); text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
.panel-title::before { content: ">_"; color: var(--secondary-fixed); font-weight: 900; }
.panel-note { font-size: 12px; color: var(--on-surface-variant); margin-top: 8px; line-height: 1.6; }

/* Form Fields (终端指令输入) */
.input, .textarea, .select { width: 100%; border: none; border-bottom: 2px solid var(--outline); background: rgba(255,255,255,0.5); color: var(--on-surface); padding: 12px 16px; outline: none; font-family: var(--font-body); font-size: 13px; transition: 0.2s; font-weight: 500; }
.textarea { min-height: 100px; resize: vertical; }
.input:focus, .textarea:focus, .select:focus { border-bottom-color: var(--primary-container); background: rgba(57, 229, 184, 0.05); }
.field { display: grid; gap: 8px; }
.field label { font-family: var(--font-headline); font-size: 11px; font-weight: 800; color: var(--outline); letter-spacing: 1px; text-transform: uppercase; display: flex; justify-content: space-between; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.field-grid.three { grid-template-columns: repeat(3, minmax(0,1fr)); }
.field-grid.four { grid-template-columns: repeat(4, minmax(0,1fr)); }

/* Buttons */
.btn, .btn-strong, .btn-danger, .btn-mini, .mode-btn { font-family: var(--font-headline); font-size: 11px; font-weight: 700; padding: 10px 16px; cursor: pointer; letter-spacing: 1px; transition: 0.2s; border: 1px solid var(--outline-variant); background: var(--surface-lowest); color: var(--primary-container); display: inline-flex; justify-content: center; align-items: center; text-transform: uppercase; }
.btn:hover { background: var(--surface-high); border-color: var(--primary-container); }
.btn-strong { background: var(--primary-container); color: var(--surface-lowest); border-color: var(--primary-container); }
.btn-strong:hover { background: var(--secondary-fixed); color: var(--on-secondary-fixed); border-color: var(--secondary-fixed); box-shadow: 0 0 12px var(--secondary-glow); }
.btn-danger { color: var(--danger); border-color: rgba(217, 56, 41, 0.3); }
.btn-danger:hover { background: var(--danger); color: white; border-color: var(--danger); box-shadow: 0 0 12px var(--danger-glow); }

/* Lists & Cards */
.stack { display: grid; gap: 12px; }
.row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }

/* Profile Card */
.profile-card, .event-item, .effect-row { background: var(--surface-lowest); border: 1px solid var(--outline-variant); padding: 16px 20px; transition: 0.2s; position: relative; }
.profile-card:hover { border-color: var(--primary-container); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.05); }
.profile-card.active { border-color: var(--primary-container); box-shadow: inset 4px 0 0 var(--secondary-fixed); background: linear-gradient(90deg, rgba(57, 229, 184, 0.05), transparent); }
.profile-card h3 { font-family: var(--font-headline); font-size: 18px; font-weight: 800; color: var(--primary-container); margin-bottom: 6px; letter-spacing: -0.5px; }
.profile-card .meta, .profile-card .helper { font-size: 12px; color: var(--on-surface-variant); margin-bottom: 12px; font-weight: 500; }
.badge { display: inline-flex; padding: 4px 8px; font-family: var(--font-headline); font-size: 10px; font-weight: 700; letter-spacing: 1px; background: var(--surface-high); color: var(--on-surface); border: 1px solid var(--outline-variant); }

/* Switch / Toggle */
.toggle-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 16px; border: 1px solid var(--outline-variant); background: var(--surface-lowest); margin-bottom: 12px; transition: 0.2s; }
.toggle-row:hover { border-color: var(--outline); }
.toggle-copy .helper { font-size: 12px; color: var(--on-surface-variant); margin-top: 6px; line-height: 1.5; }
.toggle-box { width: 48px; height: 26px; background: var(--surface-high); border: 1px solid var(--outline-variant); position: relative; cursor: pointer; transition: 0.2s; flex-shrink: 0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05); }
.toggle-box::before { content: ""; position: absolute; left: 2px; top: 2px; width: 20px; height: 20px; background: var(--outline); transition: 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.toggle-box.on { background: var(--primary-container); border-color: var(--primary-container); }
.toggle-box.on::before { transform: translateX(22px); background: var(--secondary-fixed); box-shadow: 0 0 8px var(--secondary-fixed); }

/* Archive Cards (命运牌/功能牌) */
.archive-grid, .pending-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
.archive-card { background: var(--surface-lowest); border: 1px solid var(--outline-variant); display: flex; flex-direction: column; transition: 0.3s; position: relative; isolation: isolate; }
.archive-card::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 4px; background: var(--outline-variant); z-index: 2; transition: 0.3s; }
.archive-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.08); border-color: var(--primary-container); }
.archive-card:hover::before { background: var(--secondary-fixed); box-shadow: 0 2px 10px var(--secondary-glow); }

.archive-cover { aspect-ratio: 3/4; background: linear-gradient(135deg, var(--surface-low), var(--surface-high)); border-bottom: 1px solid var(--outline-variant); padding: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }
.archive-cover::after { content: "[ IMG_SLOT ]"; position: absolute; font-family: var(--font-headline); font-size: 10px; font-weight: 700; color: rgba(0,0,0,0.1); letter-spacing: 2px; z-index: 0; }
.archive-cover img { width: 100%; height: 100%; object-fit: cover; border: 1px solid var(--outline-variant); z-index: 1; position: relative; }
.archive-body { padding: 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.archive-title { font-family: var(--font-headline); font-size: 16px; font-weight: 800; color: var(--primary-container); }
.archive-desc { font-size: 12px; color: var(--on-surface-variant); background: var(--surface-low); padding: 12px; border: 1px solid var(--outline-variant); border-left: 3px solid var(--outline); line-height: 1.5; }
.archive-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: auto; padding-top: 16px; border-top: 1px dashed var(--outline-variant); }
.archive-actions .btn { padding: 8px 0; font-size: 10px; text-align: center; }

/* Stats Widgets */
.overview-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 24px; }
.overview-stat { border: 1px solid var(--outline-variant); background: linear-gradient(180deg, var(--surface-lowest), var(--surface-low)); padding: 20px; border-left: 4px solid var(--secondary-fixed); position: relative; }
.overview-stat::after { content: ""; position: absolute; right: 20px; top: 20px; width: 16px; height: 16px; border: 2px solid var(--outline-variant); border-radius: 50% !important; }
.overview-stat b { font-family: var(--font-headline); font-size: 32px; font-weight: 900; color: var(--primary-container); display: block; margin-bottom: 4px; letter-spacing: -1px; }
.overview-stat span { font-size: 11px; color: var(--outline); text-transform: uppercase; letter-spacing: 2px; font-weight: 700; font-family: var(--font-headline); display: block; }

/* Dialog */
.dialog { position: fixed; inset: 0; background: rgba(17, 29, 21, 0.85); backdrop-filter: blur(8px); z-index: 100; display: none; align-items: center; justify-content: center; padding: 24px; }
.dialog.show { display: flex; }
.dialog-card { background: var(--surface-lowest); border: 2px solid var(--primary-container); width: min(1000px, 100%); max-height: 90vh; overflow-y: auto; padding: 40px; box-shadow: 0 32px 80px rgba(0,0,0,0.3); position: relative; }
.dialog-head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid var(--primary-container); padding-bottom: 16px; margin-bottom: 32px; }
.dialog-title { font-family: var(--font-headline); font-size: 24px; font-weight: 900; color: var(--primary-container); text-transform: uppercase; }
.tiny { font-family: var(--font-headline); font-size: 11px; color: var(--outline); letter-spacing: 3px; margin-bottom: 4px; font-weight: 700; }

/* Toast */
.toast { position: fixed; right: 32px; bottom: 32px; background: var(--primary-container); color: var(--surface-lowest); padding: 16px 24px; font-family: var(--font-body); font-size: 13px; font-weight: 600; z-index: 200; box-shadow: 0 16px 40px rgba(0,0,0,0.2); opacity: 0; transform: translateY(20px); transition: 0.3s; border-left: 4px solid var(--secondary-fixed); letter-spacing: 0.5px; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.bad { border-left-color: var(--danger); }

/* Generic Utility mappings */
.thumb { width: 80px; height: 80px; border: 1px solid var(--outline-variant); background: var(--surface-low); overflow: hidden; display: flex; align-items: center; justify-content: center; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.asset-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.tag-preview, .empty { background: rgba(255,255,255,0.5); border: 1px dashed var(--outline); padding: 24px; text-align: center; font-size: 13px; color: var(--on-surface-variant); font-weight: 500; }
.filter-bar { display: flex; gap: 16px; align-items: center; padding: 16px; background: var(--surface-lowest); border: 1px solid var(--outline-variant); margin-bottom: 20px; }

/* Stats overrides */
.stats-profile-bar { border-bottom: 2px solid var(--outline-variant); padding-bottom: 16px; margin-bottom: 24px; }
.stats-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stats-kpi { border: 1px solid var(--outline-variant); background: linear-gradient(135deg, var(--surface-lowest), var(--surface-low)); padding: 20px; border-left: 4px solid var(--primary-container); position: relative; }
.group-entry, .leaderboard-item { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 16px; margin-bottom: 12px; transition: 0.2s; }
.group-entry:hover, .leaderboard-item:hover { border-color: var(--outline); transform: translateX(4px); }
.pool-card { border: 1px solid var(--outline-variant); background: var(--surface-lowest); padding: 24px; border-top: 4px solid var(--primary-container); box-shadow: 0 8px 24px rgba(0,0,0,0.02); }

/* Scrollbar Styling for a technical feel */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--surface-low); border-left: 1px solid var(--outline-variant); }
::-webkit-scrollbar-thumb { background: var(--outline); }
::-webkit-scrollbar-thumb:hover { background: var(--primary-container); }
"""

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

with open('webui/static/styles.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

print("UI Enhanced Depth Applied Successfully!")
"""