import re


with open('webui/server.py', 'r', encoding='utf-8') as f:
    sc = f.read()

# Update server.py fields
sc = sc.replace(
    'cover_image = str(body.get("cover_image", "")).strip()',
    'cover_image = str(body.get("cover_image", "")).strip()\n        desc = str(body.get("desc", "")).strip()\n        tags = body.get("tags", [])\n        if not isinstance(tags, list): tags = []\n        tags = [str(t).strip() for t in tags if str(t).strip()]'
)
sc = sc.replace(
    'meta["cover_image"] = cover_image',
    'meta["cover_image"] = cover_image\n        meta["desc"] = desc\n        meta["tags"] = tags'
)

if '"desc": meta.get("desc", "")' not in sc:
    sc = sc.replace(
        '        "cover_image": meta.get("cover_image", ""),',
        '        "cover_image": meta.get("cover_image", ""),\n        "desc": meta.get("desc", ""),\n        "tags": meta.get("tags", []),\n'
    )

with open('webui/server.py', 'w', encoding='utf-8') as f:
    f.write(sc)

# App.html
with open('webui/static/app.html', 'r', encoding='utf-8') as f:
    hc = f.read()

# Mock mock_meta update
hc = hc.replace(
    "if (item) item.display_name = body.display_name || item.display_name;",
    "if (item) { item.display_name = body.display_name || item.display_name; item.desc = body.desc || ''; item.tags = body.tags || []; }"
)

# Replace renderOverview
new_renderOverview = '''function renderOverview() {
  const page = $('#page-overview');
  const activeProfileData = state.profiles.find(p => p.profile_id === state.currentProfile) || state.profiles[0] || {};
  page.innerHTML = `
    <div class="grid">
      <section class="panel col-8">
        <div class="panel-head">
          <div>
            <div class="panel-title">方案管理</div>
          </div>
          <button class="btn-strong" onclick="openCreateProfileDialog()">[ 新建方案 ]</button>
        </div>
        <div class="profile-list">
          ${state.profiles.map(p => {
      const active = p.profile_id === state.currentProfile;
      const justActivated = state.justActivatedProfile === p.profile_id;
      return `
            <article class="profile-card ${active ? 'active' : ''} ${justActivated ? 'just-activated' : ''}">
              <div class="scan-beam"></div>
              <div class="profile-main">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                  <h3>${esc(p.display_name || p.profile_id)}</h3>
                  <button class="action-link" style="padding: 4px 10px;" onclick="editProfile('${esc(p.profile_id)}')">编辑</button>
                </div>
                ${ p.desc ? `<div class="panel-note" style="margin-top:0; margin-bottom:8px; color:var(--shard-text-muted);">${esc(p.desc)}</div>` : '' }
                <div class="row" style="margin-bottom:12px;">
                  ${p.is_default ? '<span class="badge light">默认方案</span>' : ''}
                  ${(p.tags || []).map(t => `<span class="badge">${esc(t)}</span>`).join('')}
                </div>
                <div class="meta" style="font-size:14px; font-weight:700; color:var(--shard-text); display:flex; gap:16px; margin-bottom:0;">
                   <span>👥 用户 ${p.user_count || 0}</span>
                   <span>🎴 功能牌 ${p.func_card_count || 0}</span>
                   <span>🎴 命运牌 ${p.fate_card_count || 0}</span>
                </div>
              </div>
              <div class="profile-hud-slot">
                ${active 
                  ? '<div class="hud-active-status"><span class="hud-text">运行中</span><div class="hud-pulse"></div></div>' 
                  : `<button class="hud-switch-btn" onclick="useProfile('${esc(p.profile_id)}')"><span class="hud-text">载入方案</span><svg class="hud-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></button>`}
              </div>
            </article>`;
    }).join('')}
        </div>
      </section>

      <section class="panel col-4">
        <div class="panel-head">
          <div>
            <div class="panel-title">群组接入</div>
            <div class="panel-note">管理当前运行方案 [ ${esc(activeProfileData.display_name || '')} ] 绑定的群组。</div>
          </div>
        </div>
        <div class="field" style="margin-bottom:16px;">
          <label>绑定新群组</label>
          <div style="display:flex; gap:8px;">
            <input class="input" id="newBindGroupId" placeholder="输入群号">
            <button class="btn-strong" onclick="bindGroupFromPanel('${esc(activeProfileData.profile_id)}')">[ 绑定 ]</button>
          </div>
        </div>
        <div class="field"><label>已绑群组 ( ${(activeProfileData.groups || []).length} )</label></div>
        <div class="stack" style="max-height: 400px; overflow-y: auto; gap:8px; margin-top:8px;">
          ${(activeProfileData.groups || []).length === 0 ? '<div class="empty">暂未绑定任何群组</div>' : ''}
          ${(activeProfileData.groups || []).map(g => `
            <div style="display:flex; justify-content:space-between; align-items:center; background:var(--shard-bg); border:1px solid var(--shard-border); padding:8px 12px;">
              <span style="font-family:var(--font-headline); font-weight:700;">${esc(g)}</span>
              <button class="btn-danger icon-btn" style="height:28px; padding:0 8px; border-color:transparent; background:transparent;" onclick="unbindGroup('${esc(activeProfileData.profile_id)}','${esc(g)}')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
          `).join('')}
        </div>
      </section>
    </div>`;
}
'''

start_idx = hc.find("function renderOverview() {")
end_idx = hc.find("function renderRuntime() {")
if start_idx != -1 and end_idx != -1:
    # Need to keep the comment block
    hc = hc[:start_idx] + new_renderOverview + "\n// ===== [ page: runtime ] ===================================================\n" + hc[end_idx:]


new_editProfile = '''async function editProfile(id) {
  const current = state.profiles.find(p => p.profile_id === id);
  state.editingProfileId = id;
  const tagsStr = (current?.tags || []).join(', ');
  openDialog('编辑方案', `
    <div>
      <div>
        <div class="field">
          <label>方案名称</label><input class="input" id="newProfileName" value="${esc(current?.display_name || '')}">
        </div>
        <div class="field" style="margin-top:12px;">
          <label>方案备注</label><textarea class="textarea" id="editProfileDesc" rows="2" placeholder="给这个方案写点说明...">${esc(current?.desc || '')}</textarea>
        </div>
        <div class="field" style="margin-top:12px;">
          <label>词条展示（多个词条用逗号隔开）</label><input class="input" id="editProfileTags" value="${esc(tagsStr)}" placeholder="例如：赛季一,高难度">
        </div>
        <div class="row" style="margin-top:20px;"><button class="btn-strong" onclick="saveProfileEdit()">[ 保存方案 ]</button><button class="btn-danger" onclick="deleteProfileConfirm()">[ 删除方案 ]</button></div>
      </div>
    </div>`, 'create');
}
'''
start_idx2 = hc.find("async function editProfile(id) {")
end_idx2 = hc.find("async function saveProfileEdit() {")
if start_idx2 != -1 and end_idx2 != -1:
    hc = hc[:start_idx2] + new_editProfile + "\n" + hc[end_idx2:]


new_saveProfileEdit = '''async function saveProfileEdit() {
  const id = state.editingProfileId;
  const name = $('#newProfileName')?.value?.trim();
  const desc = $('#editProfileDesc')?.value?.trim() || '';
  const tagsRaw = $('#editProfileTags')?.value || '';
  const tags = tagsRaw.split(/[,，]/).map(v => v.trim()).filter(Boolean);

  if (!id || !name) return showToast('方案名称不能为空。', true);
  const res = await apiPost('/api/profile_meta', { profile_id: id, display_name: name, cover_image: '', desc, tags });
  if (!res.ok) return showToast(res.error || '保存失败。', true);

  closeDialog();
  await refreshProfilesAndStats();
  renderAll();
  showToast('方案编辑已保存。');
}
'''
start_idx3 = hc.find("async function saveProfileEdit() {")
end_idx3 = hc.find("async function deleteProfileConfirm() {")
if start_idx3 != -1 and end_idx3 != -1:
    hc = hc[:start_idx3] + new_saveProfileEdit + "\n" + hc[end_idx3:]


bind_func = '''async function bindGroupFromPanel(id) {
  const input = $('#newBindGroupId');
  const gid = input?.value?.trim();
  if (!gid) return showToast('请输入群号。', true);
  if (!/^\\d+$/.test(gid)) return showToast('群号格式无效。', true);
  const res = await apiPost('/api/profile_bind_group', { profile_id: id, group_id: gid });
  if (res.ok) {
    if (input) input.value = '';
    await refreshProfilesAndStats();
    renderAll();
    showToast('群号绑定成功。');
  } else {
    showToast(res.error || '绑定失败。', true);
  }
}
'''
if 'async function bindGroupFromPanel' not in hc:
    hc = hc.replace('async function bindGroupPrompt(id) {', bind_func + '\nasync function bindGroupPrompt(id) {')

if 'bindGroupFromPanel,' not in hc:
    hc = hc.replace('bindGroupPrompt,', 'bindGroupPrompt,\n  bindGroupFromPanel,')

with open('webui/static/app.html', 'w', encoding='utf-8') as f:
    f.write(hc)
print("Fix script applied successfully.")