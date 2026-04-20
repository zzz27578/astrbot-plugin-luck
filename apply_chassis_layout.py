import os

app_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>战术管理中枢 - WULING_SYS</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700;900&family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<!-- Body 变成了整个暗色机箱底座 -->
<body class="chassis">
  <div class="app-container">
    
    <!-- 左侧控制台（直接融入暗色底座） -->
    <aside class="side">
      <div class="side-header">
        <div class="mini-tag">[ ENDFIELD_WULING ARCHIVE ]</div>
        <!-- 霸气大字 -->
        <div class="big-title">管理<br>中枢</div>
        <div class="version-row">
          <span class="chip">Ver. 5.4.0</span>
          <span class="chip">[ CORE ]</span>
        </div>
      </div>

      <div class="side-nav">
        <div class="nav-title">// SEC_INDEX</div>
        <div class="nav-list">
          <button class="nav-btn active" data-page="overview">
            <span class="nav-text">总览与方案</span>
            <span class="nav-sub">PROFILE / ACCESS</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="runtime">
            <span class="nav-text">运行配置</span>
            <span class="nav-sub">RUNTIME / PROBABILITY</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="signin">
            <span class="nav-text">签到配置</span>
            <span class="nav-sub">SIGN_IN / FORECAST</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="fate">
            <span class="nav-text">命运牌档案</span>
            <span class="nav-sub">FATE_MATRIX / ASSETS</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="cards">
            <span class="nav-text">功能牌档案</span>
            <span class="nav-sub">FUNC_CARDS / EFFECTS</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="titles">
            <span class="nav-text">称号档案</span>
            <span class="nav-sub">TITLES / CONDITIONS</span>
            <div class="nav-indicator"></div>
          </button>
          <button class="nav-btn" data-page="stats">
            <span class="nav-text">数据统计</span>
            <span class="nav-sub">DATA_STATS / RANKS</span>
            <div class="nav-indicator"></div>
          </button>
        </div>
      </div>

      <div class="side-footer">
        <div class="subtle-label">[ ACTIVE_PROFILE ]</div>
        <div class="name" id="currentProfileName">加载中...</div>
        <div class="helper">SYS_SYNC // 参数自动跟随当前活跃方案。</div>
      </div>
    </aside>

    <!-- 贯穿左右的基准线，用于视觉缝合 -->
    <div class="cross-axis-line"></div>

    <!-- 右侧：悬浮嵌合的数据屏 (Data Shard) -->
    <main class="main-shard clip-bevel-shard">
      
      <!-- 纯净的头部区域，不再有突兀的深色块 -->
      <header class="shard-header">
        <div class="shard-header-content">
          <div class="kicker">[ TERRA WEB UI / ARCHIVE CONTROL ]</div>
          <h1 id="heroTitle">总览与方案</h1>
          <p id="heroDesc">管理活跃协议配置与群组访问权限。</p>
        </div>
        
        <div class="shard-toolbar">
          <div class="hero-aux" id="heroAux"></div>
          <div class="toolbar-actions">
            <button class="btn action-btn outline-btn" id="reloadBtn">
                [ RELOAD ]
            </button>
            <button class="btn action-btn solid-btn clip-bevel" id="saveAllBtn">
                SAVE_SYNC <span class="plus-mark">+</span>
            </button>
          </div>
        </div>
      </header>

      <!-- 真正的内容显示区 -->
      <div class="pages">
        <div class="page active" id="page-overview"></div>
        <div class="page" id="page-runtime"></div>
        <div class="page" id="page-signin"></div>
        <div class="page" id="page-fate"></div>
        <div class="page" id="page-cards"></div>
        <div class="page" id="page-titles"></div>
        <div class="page" id="page-stats"></div>
      </div>
    </main>

  </div>

  <!-- 弹窗也做成了机能包裹风格 -->
  <div class="dialog" id="dialog">
    <div class="dialog-backdrop"></div>
    <div class="dialog-card clip-bevel-shard">
      <div class="dialog-head">
        <div>
          <div class="tiny">[ TERMINAL_EDITOR ]</div>
          <div class="dialog-title" id="dialogTitle">编辑器</div>
        </div>
        <button class="btn outline-btn" id="closeDialogBtn">[ CLOSE ]</button>
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
  /* Chassis Theme (机箱黑/绿) */
  --chassis-bg: #090e0b;
  --chassis-green: #15291d;
  --chassis-text: #ffffff;
  --chassis-text-muted: #6b8776;
  
  /* Accent (高亮薄荷青) */
  --accent: #39e5b8;
  --accent-glow: rgba(57, 229, 184, 0.3);
  --on-accent: #002b21;
  
  /* Shard Theme (数据屏亮色) */
  --shard-bg: #f5f7f6;
  --shard-surface: #ffffff;
  --shard-border: #d4ddd8;
  --shard-text: #111413;
  --shard-text-muted: #5e6b64;
  
  --danger: #d93829;
  
  /* Fonts */
  --font-headline: 'Space Grotesk', "Source Han Sans SC", "Microsoft YaHei", sans-serif;
  --font-body: 'Inter', "Source Han Sans SC", "Microsoft YaHei", sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; border-radius: 0 !important; }

html { min-height: 100%; font-size: 14px; }

/* ================= 1. THE CHASSIS (底座) ================= */
body.chassis {
  font-family: var(--font-body);
  background-color: var(--chassis-bg);
  background-image: 
    radial-gradient(circle at top left, var(--chassis-green) 0%, transparent 40%),
    radial-gradient(var(--chassis-green) 1px, transparent 1px);
  background-size: 100% 100%, 24px 24px;
  background-attachment: fixed;
  color: var(--chassis-text);
  min-height: 100vh;
  overflow-x: hidden;
  display: flex;
}

.app-container {
  display: flex;
  width: 100%;
  max-width: 1920px;
  margin: 0 auto;
  position: relative;
}

/* 贯穿轴线，打破左右边界，强行缝合 */
.cross-axis-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 156px; /* 对齐左侧标题底边 */
  height: 1px;
  background: linear-gradient(90deg, rgba(57,229,184,0), rgba(57,229,184,0.3) 10%, rgba(57,229,184,0.3) 90%, rgba(57,229,184,0));
  z-index: 5;
  pointer-events: none;
}

/* ================= 2. THE SIDEBAR ================= */
.side {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 40px 0 40px 40px;
  position: relative;
  z-index: 10;
}

/* 大白字体霸气重做 */
.side-header {
  padding-bottom: 24px;
}
.mini-tag {
  font-family: var(--font-headline);
  color: var(--accent);
  font-size: 10px;
  letter-spacing: 2px;
  margin-bottom: 12px;
  font-weight: 700;
}
.big-title {
  font-family: var(--font-headline);
  font-size: 64px;
  font-weight: 900;
  line-height: 0.9;
  letter-spacing: -2px;
  color: var(--chassis-text);
  text-shadow: 0 4px 24px rgba(0,0,0,0.5);
  margin-bottom: 20px;
}
.version-row {
  display: flex;
  gap: 8px;
}
.chip {
  background: rgba(57, 229, 184, 0.08);
  border: 1px solid rgba(57, 229, 184, 0.2);
  color: var(--accent);
  padding: 4px 10px;
  font-size: 10px;
  font-family: var(--font-headline);
  font-weight: 700;
  letter-spacing: 1px;
  clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);
}

/* 导航菜单在深色区，高对比激活 */
.side-nav {
  margin-top: 40px;
  flex: 1;
  padding-right: 24px;
}
.nav-title {
  font-family: var(--font-headline);
  color: var(--chassis-text-muted);
  font-size: 11px;
  letter-spacing: 3px;
  margin-bottom: 16px;
}
.nav-list { display: flex; flex-direction: column; gap: 4px; }
.nav-btn {
  background: transparent;
  border: none;
  color: var(--chassis-text-muted);
  text-align: left;
  padding: 12px 16px;
  cursor: pointer;
  transition: 0.2s;
  position: relative;
  display: flex;
  flex-direction: column;
}
.nav-text {
  font-family: var(--font-headline);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
}
.nav-sub {
  font-family: var(--font-headline);
  font-size: 9px;
  opacity: 0.6;
  margin-top: 4px;
  letter-spacing: 1px;
}
.nav-indicator {
  position: absolute;
  left: -20px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 0;
  background: var(--accent);
  transition: 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.nav-btn:hover { color: var(--chassis-text); padding-left: 24px; background: rgba(255,255,255,0.02); }
.nav-btn.active {
  color: var(--accent);
  padding-left: 24px;
}
.nav-btn.active .nav-indicator {
  height: 60%;
  left: 0;
  box-shadow: 0 0 12px var(--accent-glow);
}
.nav-btn.active .nav-sub { color: var(--chassis-text); opacity: 0.9; }

.side-footer {
  margin-top: auto;
  padding-top: 24px;
  padding-right: 24px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.subtle-label { font-family: var(--font-headline); color: var(--accent); font-size: 10px; letter-spacing: 2px; }
.side-footer .name { font-family: var(--font-headline); font-size: 16px; font-weight: 700; margin: 8px 0; color: var(--chassis-text); }
.side-footer .helper { font-size: 10px; color: var(--chassis-text-muted); font-family: var(--font-headline); }


/* ================= 3. THE DATA SHARD (数据屏) ================= */
/* 将右侧做成一个悬浮的、带切角的独立白板，被黑底包裹 */
.main-shard {
  flex: 1;
  margin: 32px 32px 32px 0;
  background: var(--shard-bg);
  color: var(--shard-text);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 20;
  border: 1px solid var(--shard-border);
  /* 给面板加上科幻的阴影和内发光 */
  box-shadow: 
    0 32px 64px rgba(0,0,0,0.4), 
    inset 0 0 0 1px rgba(255,255,255,0.5);
}

.clip-bevel-shard {
  clip-path: polygon(32px 0, 100% 0, 100% calc(100% - 32px), calc(100% - 32px) 100%, 0 100%, 0 32px);
}

/* 数据屏内部的顶部 Header */
.shard-header {
  padding: 32px 48px;
  border-bottom: 1px solid var(--shard-border);
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  background: var(--shard-surface);
  position: relative;
}
.shard-header::after {
  content: '';
  position: absolute;
  left: 48px;
  bottom: -1px;
  width: 80px;
  height: 3px;
  background: var(--chassis-green);
}

.shard-header-content .kicker {
  font-family: var(--font-headline);
  font-size: 10px;
  color: var(--shard-text-muted);
  letter-spacing: 3px;
  margin-bottom: 8px;
  font-weight: 700;
}
.shard-header-content h1 {
  font-family: var(--font-headline);
  font-size: 32px;
  font-weight: 900;
  color: var(--shard-text);
  letter-spacing: -1px;
}
.shard-header-content p {
  font-size: 13px;
  color: var(--shard-text-muted);
  margin-top: 8px;
  font-weight: 500;
}

/* 右侧的悬浮操作按钮 */
.shard-toolbar {
  display: flex;
  gap: 16px;
  align-items: center;
}
.toolbar-actions {
  display: flex;
  gap: 12px;
}
.action-btn {
  font-family: var(--font-headline);
  font-size: 11px;
  font-weight: 800;
  height: 40px;
  padding: 0 20px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 1px;
  transition: 0.2s;
}
.outline-btn {
  background: transparent;
  border: 1px solid var(--shard-border);
  color: var(--shard-text);
}
.outline-btn:hover {
  border-color: var(--chassis-green);
  background: rgba(0,0,0,0.03);
}
.solid-btn {
  background: var(--chassis-green);
  border: 1px solid var(--chassis-green);
  color: var(--shard-surface);
}
.solid-btn .plus-mark { color: var(--accent); margin-left: 6px; font-size: 14px; font-weight: 900; }
.solid-btn:hover {
  background: var(--accent);
  color: var(--on-accent);
  border-color: var(--accent);
}
.clip-bevel {
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
}

/* 内容区 */
.pages {
  padding: 40px 48px;
  flex: 1;
  overflow-y: auto;
}
.page {
  display: none;
  gap: 24px;
}
.page.active {
  display: grid;
}

/* 栅格系统 */
.grid { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: 24px; }
.col-12 { grid-column: span 12; } .col-8 { grid-column: span 8; } .col-7 { grid-column: span 7; } .col-6 { grid-column: span 6; } .col-5 { grid-column: span 5; } .col-4 { grid-column: span 4; }

/* ================= 4. INTERNAL SHARD COMPONENTS (内部组件精细线框化) ================= */

/* Panels */
.panel {
  background: var(--shard-surface);
  border: 1px solid var(--shard-border);
  padding: 24px;
  position: relative;
}
.panel-head {
  border-bottom: 2px solid var(--shard-text);
  padding-bottom: 12px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.panel-title {
  font-family: var(--font-headline);
  font-size: 18px;
  font-weight: 800;
  color: var(--shard-text);
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-title::before { content: '■'; font-size: 10px; color: var(--accent); }
.panel-note { font-size: 12px; color: var(--shard-text-muted); margin-top: 8px; line-height: 1.6; }

/* Inputs - 线框感 */
.input, .textarea, .select {
  width: 100%;
  border: 1px solid var(--shard-border);
  border-bottom: 2px solid var(--shard-text-muted);
  background: var(--shard-bg);
  color: var(--shard-text);
  padding: 12px 16px;
  outline: none;
  font-family: var(--font-body);
  font-size: 13px;
  transition: 0.2s;
  font-weight: 500;
}
.textarea { min-height: 100px; resize: vertical; }
.input:focus, .textarea:focus, .select:focus {
  border-bottom-color: var(--chassis-green);
  background: var(--shard-surface);
  box-shadow: inset 0 -4px 0 rgba(57, 229, 184, 0.1);
}
.field { display: grid; gap: 8px; }
.field label {
  font-family: var(--font-headline);
  font-size: 10px;
  font-weight: 800;
  color: var(--shard-text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.field-grid.three { grid-template-columns: repeat(3, minmax(0,1fr)); }
.field-grid.four { grid-template-columns: repeat(4, minmax(0,1fr)); }

/* 内部通用按钮 */
.btn, .btn-strong, .btn-danger, .btn-mini, .mode-btn {
  font-family: var(--font-headline);
  font-size: 11px;
  font-weight: 800;
  padding: 10px 16px;
  cursor: pointer;
  letter-spacing: 1px;
  transition: 0.2s;
  border: 1px solid var(--shard-border);
  background: var(--shard-surface);
  color: var(--shard-text);
  display: inline-flex;
  justify-content: center;
  align-items: center;
  text-transform: uppercase;
}
.btn:hover { border-color: var(--chassis-green); background: var(--shard-bg); }
.btn-strong { background: var(--chassis-green); color: var(--shard-surface); border-color: var(--chassis-green); }
.btn-strong:hover { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
.btn-danger { color: var(--danger); border-color: rgba(217, 56, 41, 0.3); }
.btn-danger:hover { background: var(--danger); color: white; border-color: var(--danger); }

/* Cards & Lists */
.stack { display: grid; gap: 12px; }
.row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }

.profile-card, .event-item, .effect-row {
  background: var(--shard-surface);
  border: 1px solid var(--shard-border);
  padding: 16px 20px;
  transition: 0.2s;
  position: relative;
}
.profile-card:hover { border-color: var(--chassis-green); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.profile-card.active {
  border-color: var(--chassis-green);
  background: var(--shard-surface);
  box-shadow: inset 4px 0 0 var(--chassis-green);
}
.profile-card h3 {
  font-family: var(--font-headline);
  font-size: 18px;
  font-weight: 800;
  color: var(--shard-text);
  margin-bottom: 4px;
  letter-spacing: -0.5px;
}
.profile-card .meta, .profile-card .helper {
  font-size: 12px;
  color: var(--shard-text-muted);
  margin-bottom: 12px;
}
.badge {
  display: inline-flex;
  padding: 4px 8px;
  font-family: var(--font-headline);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  background: var(--shard-bg);
  border: 1px solid var(--shard-border);
  color: var(--shard-text);
}

/* Switch */
.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  border: 1px solid var(--shard-border);
  background: var(--shard-surface);
  margin-bottom: 12px;
  transition: 0.2s;
}
.toggle-row:hover { border-color: var(--chassis-green); }
.toggle-copy .helper { font-size: 12px; color: var(--shard-text-muted); margin-top: 6px; }
.toggle-box {
  width: 48px;
  height: 26px;
  background: var(--shard-bg);
  border: 1px solid var(--shard-border);
  position: relative;
  cursor: pointer;
  transition: 0.2s;
  flex-shrink: 0;
}
.toggle-box::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 20px;
  height: 20px;
  background: var(--shard-text-muted);
  transition: 0.2s;
}
.toggle-box.on { background: var(--chassis-green); border-color: var(--chassis-green); }
.toggle-box.on::before { transform: translateX(22px); background: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }

/* Archive Grids (卡牌) */
.archive-grid, .pending-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 24px; }
.archive-card {
  background: var(--shard-surface);
  border: 1px solid var(--shard-border);
  display: flex;
  flex-direction: column;
  transition: 0.3s;
  position: relative;
}
.archive-card::before {
  content: '';
  position: absolute;
  left: -1px;
  top: -1px;
  width: 12px;
  height: 12px;
  border-top: 2px solid var(--shard-text);
  border-left: 2px solid var(--shard-text);
  transition: 0.3s;
  pointer-events: none;
  z-index: 5;
}
.archive-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.06); border-color: var(--chassis-green); }
.archive-card:hover::before { border-color: var(--accent); width: 24px; height: 24px; }

.archive-cover {
  aspect-ratio: 3/4;
  background: var(--shard-bg);
  border-bottom: 1px solid var(--shard-border);
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}
.archive-cover::after { content: 'IMG_DATA'; position: absolute; font-family: var(--font-headline); font-size: 10px; font-weight: 700; color: rgba(0,0,0,0.05); letter-spacing: 2px; }
.archive-cover img { width: 100%; height: 100%; object-fit: cover; border: 1px solid var(--shard-border); z-index: 1; position: relative; }
.archive-body { padding: 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.archive-title { font-family: var(--font-headline); font-size: 16px; font-weight: 800; color: var(--shard-text); }
.archive-desc { font-size: 12px; color: var(--shard-text-muted); background: var(--shard-bg); padding: 12px; border: 1px solid var(--shard-border); line-height: 1.5; }
.archive-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: auto; padding-top: 16px; border-top: 1px dashed var(--shard-border); }
.archive-actions .btn { padding: 8px 0; font-size: 10px; }

/* Stats Widgets */
.overview-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 24px; }
.overview-stat {
  border: 1px solid var(--shard-border);
  background: var(--shard-surface);
  padding: 24px;
  border-top: 3px solid var(--chassis-green);
  position: relative;
}
.overview-stat b {
  font-family: var(--font-headline);
  font-size: 36px;
  font-weight: 900;
  color: var(--shard-text);
  display: block;
  margin-bottom: 4px;
  letter-spacing: -1px;
}
.overview-stat span {
  font-size: 11px;
  color: var(--shard-text-muted);
  letter-spacing: 2px;
  font-weight: 700;
  font-family: var(--font-headline);
  display: block;
}

/* Dialog */
.dialog { position: fixed; inset: 0; display: none; align-items: center; justify-content: center; padding: 24px; z-index: 100; }
.dialog.show { display: flex; }
.dialog-backdrop { position: absolute; inset: 0; background: rgba(9, 14, 11, 0.9); backdrop-filter: blur(8px); }
.dialog-card {
  background: var(--shard-surface);
  border: 1px solid var(--shard-border);
  width: min(1000px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  padding: 40px;
  position: relative;
  z-index: 101;
  box-shadow: 0 40px 100px rgba(0,0,0,0.5);
}
.dialog-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2px solid var(--chassis-green);
  padding-bottom: 16px;
  margin-bottom: 32px;
}
.dialog-title {
  font-family: var(--font-headline);
  font-size: 24px;
  font-weight: 900;
  color: var(--chassis-green);
  text-transform: uppercase;
}
.tiny { font-family: var(--font-headline); font-size: 10px; color: var(--shard-text-muted); letter-spacing: 3px; margin-bottom: 8px; font-weight: 700; }

/* Toast */
.toast {
  position: fixed;
  right: 32px;
  bottom: 32px;
  background: var(--chassis-green);
  color: var(--chassis-text);
  padding: 16px 24px;
  font-family: var(--font-headline);
  font-size: 13px;
  font-weight: 700;
  z-index: 200;
  box-shadow: 0 16px 40px rgba(0,0,0,0.3);
  opacity: 0;
  transform: translateY(20px);
  transition: 0.3s;
  border-left: 4px solid var(--accent);
  letter-spacing: 1px;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.bad { border-left-color: var(--danger); }

/* js/main.js specific elements overrides */
.thumb { width: 80px; height: 80px; border: 1px solid var(--shard-border); background: var(--shard-bg); overflow: hidden; display: flex; align-items: center; justify-content: center; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.asset-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.tag-preview, .empty { background: var(--shard-bg); border: 1px dashed var(--shard-border); padding: 24px; text-align: center; font-size: 13px; color: var(--shard-text-muted); font-weight: 500; }
.filter-bar { display: flex; gap: 16px; align-items: center; padding: 16px; background: var(--shard-surface); border: 1px solid var(--shard-border); margin-bottom: 20px; }
.stats-profile-bar { border-bottom: 2px solid var(--chassis-green); padding-bottom: 16px; margin-bottom: 24px; }
.stats-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stats-kpi { border: 1px solid var(--shard-border); background: var(--shard-surface); padding: 20px; border-top: 3px solid var(--chassis-green); position: relative; }
.group-entry, .leaderboard-item { border: 1px solid var(--shard-border); background: var(--shard-surface); padding: 16px; margin-bottom: 12px; transition: 0.2s; }
.group-entry:hover, .leaderboard-item:hover { border-color: var(--chassis-green); transform: translateX(4px); }
.pool-card { border: 1px solid var(--shard-border); background: var(--shard-surface); padding: 24px; border-top: 4px solid var(--chassis-green); }

/* Scrollbar Styling */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--shard-bg); border-left: 1px solid var(--shard-border); }
::-webkit-scrollbar-thumb { background: var(--shard-border); }
::-webkit-scrollbar-thumb:hover { background: var(--chassis-green); }
"""

with open('webui/static/styles.css', 'w', encoding='utf-8') as f:
    f.write(css_code)
print('CSS chassis applied.')
