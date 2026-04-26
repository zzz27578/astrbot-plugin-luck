import re

with open('webui/static/app.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. CSS 修改 (修复铺满，增加动画，去掉多余绿边)
css_old = """/* ================= 鹰角风：实用型工业级首页 (The Control Showcase) ================= */
#page-home { display: flex !important; margin: -40px -48px; height: 100vh; }"""
css_new = """/* ================= 鹰角风：实用型工业级首页 (The Control Showcase) ================= */
#page-home { display: flex !important; position: absolute; inset: 0; margin: 0; padding: 0; z-index: 100; }

/* 终极变形动画类 */
.home-showcase.morph-out .showcase-left {
  flex: none;
  width: 200px;
  padding: 32px 0 24px 16px;
  transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);
}
.home-showcase.morph-out .sc-crosshair, 
.home-showcase.morph-out .sc-top-info, 
.home-showcase.morph-out .sc-terminal {
  opacity: 0;
  transition: opacity 0.2s;
}
.home-showcase.morph-out .showcase-right {
  flex: 1;
  clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
  border-left: none;
  transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);
}
.home-showcase.morph-out .sr-header, 
.home-showcase.morph-out .sr-pathways {
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.2s;
}
"""
content = content.replace(css_old, css_new)

# 替换右侧容器 CSS
right_old = """  clip-path: polygon(15% 0, 100% 0, 100% 100%, 0 100%);
  border-left: 2px solid var(--accent);"""
right_new = """  clip-path: polygon(10% 0, 100% 0, 100% 100%, 0 100%);
  border-left: none; /* 去掉多余绿边 */
  transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);"""
content = content.replace(right_old, right_new)

# 删除右侧多余的 ::before 绿条
green_bar_old = """\.showcase-right::before {\n  content: ''; position: absolute; top: 0; bottom: 0; left: 0; width: 6px;\n  background: var(--accent);\n}"""
content = content.replace(green_bar_old, "")


# 2. 替换 setTopView
set_top_old = """    if (view === 'home') {
      $('.glass-side').style.display = 'none';
      $('#homePages').style.display = 'block';
      $('.shard-header').style.display = 'none';
      $('#configPages').style.display = 'none';
      $('#statsPages').style.display = 'none';
      $('.toolbar-actions').style.display = 'none';
      renderHome();
      return;
    }"""
set_top_new = """    if (view === 'home') {
      $('.glass-side').style.display = 'none';
      $('.glass-top').style.display = 'none'; // 首页沉浸全屏
      $('#homePages').style.display = 'block';
      $('.shard-header').style.display = 'none';
      $('#configPages').style.display = 'none';
      $('#statsPages').style.display = 'none';
      $('.toolbar-actions').style.display = 'none';
      renderHome();
      return;
    }
    $('.glass-top').style.display = 'flex';
    $('.glass-side').style.display = 'flex';
    $('#homePages').style.display = 'none';"""
content = content.replace(set_top_old, set_top_new)


# 3. 替换 renderHome
content = re.sub(
    r"function renderHome\(\).*?`\s*\};?\s*\}",
    """function triggerSystemMorph() {
  const showcase = document.querySelector('.home-showcase');
  if (showcase) showcase.classList.add('morph-out');
  setTimeout(() => {
    setTopView('config');
  }, 500);
}

function renderHome() {
  $('#page-home').innerHTML = `
    <div class="home-showcase">
      <div class="showcase-noise"></div>
      <div class="showcase-grid-bg"></div>
      
      <div class="showcase-left">
        <div class="sc-crosshair" style="top: 48px; left: 48px;"></div>
        <div class="sc-crosshair" style="bottom: 48px; right: 48px;"></div>
        
        <div class="sc-top-info" style="margin-left: 0; margin-top: 0; padding: 48px;">
          <div class="line-1" style="font-size: 11px; font-weight: 700; opacity: 0.6;">WULING_SYS // VER 5.4.0</div>
          <div class="line-2" style="margin-top: 4px;">STANDBY FOR AUTHORIZATION</div>
        </div>
        
        <div class="sc-terminal" style="margin-left: 0; margin-bottom: 0; padding: 48px;">
          > KERNEL BOOT SEQUENCE INITIATED...<br>
          > INITIALIZING NEURAL LINK... <span class="highlight">OK</span><br>
          > LOADING CONFIG ARCHIVE... <span class="highlight">OK</span><br>
          > SYNC WITH TELEMETRY NODE... <span class="highlight">ESTABLISHED</span><br><br>
          <span style="color: rgba(255,255,255,0.2);">> AWAITING USER INITIATION -></span>
        </div>
      </div>
      
      <div class="showcase-right">
        <div class="sr-header">
          <span class="sr-kicker">// WULING INTEGRATED CONTROL //</span>
          <div class="sr-title" style="font-size: 40px; margin-bottom: 12px;">系统权限验证</div>
          <div class="sr-desc">核心协议已加载完毕，全域大盘就绪。请确认授权以展开控制中枢。</div>
        </div>
        
        <div class="sr-pathways">
          <div class="pathway-btn" style="padding: 32px;" onclick="triggerSystemMorph()">
            <div class="pw-left">
              <span class="pw-num">[ AUTHORIZE ]</span>
              <span class="pw-name" style="font-size: 24px;">初始化并接入</span>
              <span class="pw-en">SYSTEM INITIATE</span>
            </div>
            <div class="pw-arrow">ENTER →</div>
          </div>
        </div>
      </div>
    </div>
  `;
}
""",
    content,
    flags=re.DOTALL
)

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")
