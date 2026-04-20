import os

html = """<!DOCTYPE html>
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
</html>"""

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('HTML written.')
