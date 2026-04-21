import re

with open('webui/static/app.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_overview = """function renderOverview() {
  const page = $('#page-overview');
  page.innerHTML = `
    <div class="grid">
      <section class="panel col-8" style="border: none; background: transparent; padding: 0; box-shadow: none;">
        <div class="panel-head" data-kicker="档案流转与配置枢纽">
          <div style="margin-top: 12px;">
            <div class="panel-title">方案档案</div>
            <div class="panel-note" style="font-size: 13px;">管理系统的运行参数预设。当处于激活状态时，其规则将覆盖全域。</div>
          </div>
          <button class="btn-strong" onclick="openCreateProfileDialog()">新建方案</button>
        </div>
        <div class="profile-list">
          ${state.profiles.map(p => {
      const active = p.profile_id === state.currentProfile;
      const justActivated = state.justActivatedProfile === p.profile_id;
      const hashId = (p.profile_id || '').replace(/[^0-9]/g, '').slice(-6) || 'A09';
      return `
            <article class="profile-card ${active ? 'active' : ''} ${justActivated ? 'just-activated' : ''}">
              <div class="serial-number">SYS-PRF-${hashId}</div>
              <div class="profile-main">
                  <h3>${esc(p.display_name || p.profile_id)}</h3>
                <div class="row" style="margin-bottom:8px;">
                  ${p.is_default ? '<span class="badge light">默认方案</span>' : ''}
                  <span class="badge">绑定群组: ${(p.group_count || 0)}</span>
                </div>
                <div class="meta">用户总量 ${p.user_count || 0} ｜ 功能牌数 ${p.func_card_count || 0} ｜ 命运牌数 ${p.fate_card_count || 0}</div>
                <div class="row" style="margin:8px 0 12px;">
                  ${(p.groups || []).slice(0, 3).map(g => `<span class="badge" style="border-color:transparent;background:var(--shard-bg);">群 ${esc(g)}</span>`).join('') || '<span class="helper">暂无绑定群组</span>'}
                </div>
                <div class="row">
                  <button class="btn outline-btn" onclick="editProfile('${esc(p.profile_id)}')">[ 编辑档案 ]</button>
                  <button class="btn outline-btn" onclick="bindGroupPrompt('${esc(p.profile_id)}')">[ 绑定群号 ]</button>
                  ${(p.groups || []).slice(0, 3).length ? `<button class="btn-mini btn-danger" onclick="unbindGroup('${esc(p.profile_id)}','${esc(p.groups[0])}')">[ 解绑核心 ]</button>` : ''}
                </div>
              </div>
              <div class="profile-switch-slot" style="position:absolute; top:24px; right:24px; bottom:auto;">
                <button class="btn-strong" style="padding:12px 16px; height:auto;" ${active ? 'disabled' : `onclick="useProfile('${esc(p.profile_id)}')"`}>
                  ${active ? '使用中' : '切换至该方案'}
                </button>
              </div>
            </article>`;
    }).join('')}
        </div>
      </section>

      <section class="panel col-4" style="background: linear-gradient(180deg, rgba(255,255,255,0.6), rgba(245,250,248,0.8)); border: 1px solid rgba(57, 229, 184, 0.15); border-radius: 4px; padding: 32px;">
        <div class="panel-head" data-kicker="边界协议与访问白名单">
          <div style="margin-top: 12px;">
            <div class="panel-title">越界限制</div>
            <div class="panel-note">指定哪些信标节点能够响应系统的调用。</div>
          </div>
        </div>
        <div class="switch-group" style="margin-bottom:24px;">
          <button class="btn ${state.groupAccess.mode === 'off' ? 'solid-btn' : 'outline-btn'}" style="flex:1; padding:0;" onclick="setAccessMode('off')">不限制</button>
          <button class="btn ${state.groupAccess.mode === 'blacklist' ? 'solid-btn' : 'outline-btn'}" style="flex:1; padding:0;" onclick="setAccessMode('blacklist')">拒绝响应</button>
          <button class="btn ${state.groupAccess.mode === 'whitelist' ? 'solid-btn' : 'outline-btn'}" style="flex:1; padding:0;" onclick="setAccessMode('whitelist')">白名单</button>
        </div>
        ${state.groupAccess.mode === 'blacklist' ? `
        <div class="field" style="margin-bottom:16px;">
          <label>拒绝访问的群号</label>
          <textarea class="textarea" id="blacklistInput">${esc((state.groupAccess.blacklist || []).join('\\n'))}</textarea>
        </div>` : ''}
        ${state.groupAccess.mode === 'whitelist' ? `
        <div class="field" style="margin-bottom:16px;">
          <label>授权访问的群号</label>
          <textarea class="textarea" id="whitelistInput">${esc((state.groupAccess.whitelist || []).join('\\n'))}</textarea>
        </div>` : ''}
        <div class="row" style="margin-top:20px;">
          <button class="btn-strong" style="width:100%;" onclick="saveGroupAccess()">更新访问协议</button>
        </div>
        
        <div class="panel-title" style="margin-top: 48px; margin-bottom: 16px; font-size: 16px; font-weight: 500;">全局流转数据</div>
        <div class="overview-stats">
          <div class="overview-stat">
            <b id="quickProfileCount">${state.profiles.length || 0}</b><span>已储方案</span>
          </div>
          <div class="overview-stat">
            <b id="quickGroupCount">${state.stats.total_groups || 0}</b><span>活跃信标</span>
          </div>
          <div class="overview-stat" style="grid-column: span 3;">
            <b id="quickUserCount">${state.stats.total_users || 0}</b><span>记录人员总数</span>
          </div>
        </div>
      </section>
    </div>`;
}"""

pattern = r'(?s)<div class="grid">\s*<section class="panel col-8">.*?</section>\s*</div>`;\n}'
new_html = re.sub(pattern, new_overview.split('`\n', 1)[1], html)

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Patch applied successfully.")