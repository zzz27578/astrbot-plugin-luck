// ===== [ state / constants / helpers ] =====================================
const state = {
  currentProfile: 'default',
  activePage: 'overview',
  profiles: [],
  runtimeConfig: {},
  groupAccess: { mode: 'off', blacklist: [], whitelist: [] },
  signInTexts: { good_things: [], bad_things: [], luck_ranges: [] },
  fateCards: [],
  fateImages: [],
  funcCards: [],
  images: [],
  stats: { total_groups: 0, total_users: 0, card_holders: {}, groups: [] },
  goodSelected: [],
  badSelected: [],
  editingFuncIndex: -1,
  editingFuncEffects: [],
  editingFateIndex: -1,
  justActivatedProfile: '',
  funcFilter: 'all',
};

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

const pageMeta = {
  overview: ['总览与方案', '把方案、访问控制与核心信息放在同一屏内，切换顺手，状态清晰。'],
  runtime: ['运行配置', '保留完整功能，但让高频参数调整更轻松、更直观。'],
  signin: ['签到配置', '事件池、运势区间与预览集中排布，方便边改边看。'],
  fate: ['命运牌档案', '命运牌、资源图片与编辑器放在一起，减少来回跳转。'],
  cards: ['功能牌档案', '竖版卡片展示，按类型快速查看并编辑功能牌。'],
  titles: ['称号档案', '配置称号的获取条件、效果与说明，支持按方案独立维护。'],
  stats: ['数据统计', '按方案查看群组、用户与持牌排行。'],
};


const rarityLabelMap = { 1: '普通', 2: '稀有', 3: '史诗', 4: '传说', 5: '神话' };
const typeLabelMap = { attack: '攻击', heal: '辅助', defense: '防御' };
const effectCatalog = {
  attack: [
    { key: 'steal', name: '偷取金币', params: ['数值'] },
    { key: 'freeze', name: '冻结', params: ['小时'] },
    { key: 'silence', name: '沉默', params: ['小时'] },
    { key: 'seal_draw_all', name: '封锁抽牌', params: ['小时'] },
    { key: 'luck_drain', name: '抽取爆率', params: ['小时', '百分比'] },
    { key: 'steal_fate', name: '偷取命运收益', params: [] },
    { key: 'borrow_blade', name: '借刀伤害', params: ['最小值', '最大值'] },
    { key: 'bounty_mark', name: '悬赏印记', params: ['小时', '追加金币'] },
    { key: 'strip_buff_gain', name: '夺取增益并加爆率', params: ['百分比', '小时'] },
    { key: 'aoe_damage', name: '群体攻击', params: ['最小值', '最大值', '人数'] },
    { key: 'dice_rule', name: '骰子规则', params: ['规则键'] },
    { key: 'dice_duel', name: '对赌', params: ['底注'] }
  ],
  heal: [
    { key: 'cleanse', name: '净化', params: [] },
    { key: 'aoe_heal', name: '群体回复', params: ['最小值', '最大值', '人数'] },
    { key: 'luck_bless', name: '好运加护', params: ['小时', '百分比'] },
    { key: 'fate_roulette', name: '命运转盘', params: [] },
    { key: 'dice_reroll_lowest_once', name: '最低点重投一次', params: [] }
  ],
  defense: [
    { key: 'add_shield', name: '护盾', params: [] },
    { key: 'thorn_armor', name: '反甲', params: ['小时', '反伤比例'] },
    { key: 'cleanse', name: '净化', params: [] }
  ]
};

function effectToTag(effect) {
  const p = effect.params || [];
  switch (effect.key) {
    case 'steal': return `steal:${p[0] || 0}`;
    case 'freeze': return `freeze:${p[0] || 0}`;
    case 'silence': return `silence:${p[0] || 0}`;
    case 'seal_draw_all': return `seal_draw_all:${p[0] || 0}`;
    case 'luck_drain': return `luck_drain:${p[0] || 0}:${p[1] || 0}`;
    case 'steal_fate': return 'steal_fate';
    case 'borrow_blade': return `borrow_blade:${p[0] || 0}:${p[1] || 0}`;
    case 'bounty_mark': return `bounty_mark:${p[0] || 0}:${p[1] || 0}`;
    case 'strip_buff_gain': return `strip_buff_gain:${p[0] || 0}:${p[1] || 0}`;
    case 'aoe_damage': return `aoe_damage:${p[0] || 0}:${p[1] || 0}:${p[2] || 0}`;
    case 'dice_rule': return `dice_rule:${p[0] || 'all_in_raid_v1'}`;
    case 'dice_duel': return `dice_duel:${p[0] || 20}`;
    case 'cleanse': return 'cleanse';
    case 'aoe_heal': return `aoe_heal:${p[0] || 0}:${p[1] || 0}:${p[2] || 0}`;
    case 'luck_bless': return `luck_bless:${p[0] || 0}:${p[1] || 0}`;
    case 'fate_roulette': return 'fate_roulette';
    case 'dice_reroll_lowest_once': return 'dice_reroll_lowest_once';
    case 'add_shield': return 'add_shield';
    case 'thorn_armor': return `thorn_armor:${p[0] || 0}:${p[1] || 0}`;
    default: return '';
  }
}

function tagToEffect(tag) {
  const raw = String(tag || '');
  if (!raw) return null;
  const [key, ...rest] = raw.split(':');
  if (key === 'steal') return { key, params: [rest[0] || ''] };
  if (key === 'freeze') return { key, params: [rest[0] || ''] };
  if (key === 'silence') return { key, params: [rest[0] || ''] };
  if (key === 'seal_draw_all') return { key, params: [rest[0] || ''] };
  if (key === 'luck_drain') return { key, params: [rest[0] || '', rest[1] || ''] };
  if (key === 'steal_fate') return { key, params: [] };
  if (key === 'borrow_blade') return { key, params: [rest[0] || '', rest[1] || ''] };
  if (key === 'bounty_mark') return { key, params: [rest[0] || '', rest[1] || ''] };
  if (key === 'strip_buff_gain') return { key, params: [rest[0] || '', rest[1] || ''] };
  if (key === 'aoe_damage') return { key, params: [rest[0] || '', rest[1] || '', rest[2] || ''] };
  if (key === 'dice_rule') return { key, params: [rest.join(':') || 'all_in_raid_v1'] };
  if (key === 'dice_duel') return { key, params: [rest[0] || '20'] };
  if (key === 'cleanse') return { key, params: [] };
  if (key === 'aoe_heal') return { key, params: [rest[0] || '', rest[1] || '', rest[2] || ''] };
  if (key === 'luck_bless') return { key, params: [rest[0] || '', rest[1] || ''] };
  if (key === 'fate_roulette') return { key, params: [] };
  if (key === 'dice_reroll_lowest_once') return { key, params: [] };
  if (key === 'add_shield') return { key, params: [] };
  if (key === 'thorn_armor') return { key, params: [rest[0] || '', rest[1] || ''] };
  return { key: 'raw', raw };
}

function effectLabel(effect) {
  if (!effect) return '未识别效果';
  if (effect.key === 'raw') return `原始标签：${effect.raw}`;
  const dict = [...effectCatalog.attack, ...effectCatalog.heal, ...effectCatalog.defense].find(x => x.key === effect.key);
  return dict?.name || effect.key;
}

function humanizeTag(tag) {
  const effect = tagToEffect(tag);
  if (!effect) return '未设定';
  const p = effect.params || [];
  switch (effect.key) {
    case 'steal': return `偷取目标 ${p[0]} 金币`;
    case 'freeze': return `冻结 ${p[0]} 小时`;
    case 'silence': return `沉默 ${p[0]} 小时`;
    case 'seal_draw_all': return `封锁抽牌 ${p[0]} 小时`;
    case 'luck_drain': return `抽取 ${p[1]}% 爆率，持续 ${p[0]} 小时`;
    case 'steal_fate': return '偷取命运收益';
    case 'borrow_blade': return `借刀造成 ${p[0]}-${p[1]} 伤害`;
    case 'bounty_mark': return `悬赏 ${p[0]} 小时，每次追加 ${p[1]} 金币`;
    case 'strip_buff_gain': return `夺取增益并获得 ${p[0]}% 爆率 ${p[1]} 小时`;
    case 'aoe_damage': return `群攻 ${p[0]}-${p[1]}，最多 ${p[2]} 人`;
    case 'dice_rule': return `骰子规则 ${p[0]}`;
    case 'dice_duel': return `对赌底注 ${p[0]}`;
    case 'cleanse': return '净化负面状态';
    case 'aoe_heal': return `群体回复 ${p[0]}-${p[1]}，最多 ${p[2]} 人`;
    case 'luck_bless': return `${p[0]} 小时内爆率 +${p[1]}%`;
    case 'fate_roulette': return '命运转盘';
    case 'dice_reroll_lowest_once': return '最低点自动重投一次';
    case 'add_shield': return '挂载护盾';
    case 'thorn_armor': return `反甲 ${p[0]} 小时，反伤 ${p[1]}%`;
    case 'raw': return `原始标签：${effect.raw}`;
    default: return tag;
  }
}

function showToast(text, bad = false) {
  const el = $('#toast');
  el.textContent = text;
  el.className = `toast show${bad ? ' bad' : ''}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => el.className = 'toast', 2200);
}

function apiUrl(path) {
  return `${path}${path.includes('?') ? '&' : '?'}profile=${encodeURIComponent(state.currentProfile || 'default')}`;
}
const requestJson = async (path, options = {}) => (await fetch(apiUrl(path), options)).json();
const apiGet = (path) => requestJson(path);
const apiPost = (path, body) => requestJson(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const apiDelete = (path) => requestJson(path, { method: 'DELETE' });
const apiDeleteProfileById = (profileId) => apiPost('/api/profile_remove', { profile_id: profileId });

function setPage(page) {
  state.activePage = page;
  const meta = pageMeta[page];
  $('#heroTitle').textContent = meta[0];
  $('#heroDesc').textContent = meta[1];
  $$('.nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
  $$('.page').forEach(el => el.classList.toggle('active', el.id === `page-${page}`));
  renderHeroAux();
}

function getProfileName(id = state.currentProfile) {
  return state.profiles.find(p => p.profile_id === id)?.display_name || id;
}

function ensureRuntime() {
  const c = state.runtimeConfig || {};
  c.webui_settings ||= { enable: true, port: 4399 };
  c.fate_cards_settings ||= { enable: true, daily_draw_limit: 3 };
  c.func_cards_settings ||= {
    enable: true,
    enable_dice_cards: true,
    enable_public_duel_mode: false,
    public_duel_daily_limit: 3,
    public_duel_min_stake: 10,
    public_duel_max_stake: 200,
    enable_rarity_dedup: true,
    rarity_mode: 'default',
    max_equipped_titles: 3,
    custom_rarity_weights: { rarity_1: 30, rarity_2: 30, rarity_3: 28, rarity_4: 11, rarity_5: 1 },
    economy_settings: { draw_probability: 5, free_daily_draw: 1, draw_cost: 20, pity_threshold: 10 }
  };
  c.func_cards_settings.custom_rarity_weights ||= { rarity_1: 30, rarity_2: 30, rarity_3: 28, rarity_4: 11, rarity_5: 1 };
  c.func_cards_settings.economy_settings ||= { draw_probability: 5, free_daily_draw: 1, draw_cost: 20, pity_threshold: 10 };
  c.func_cards_settings.max_equipped_titles ||= 3;
  state.runtimeConfig = c;
}



function setDeep(obj, path, value) {
  const keys = path.split('.');
  let t = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    t[keys[i]] ||= {};
    t = t[keys[i]];
  }
  t[keys[keys.length - 1]] = value;
}
function getDeep(obj, path) { return path.split('.').reduce((a, k) => a?.[k], obj); }

// ===== [ data loading / refresh ] ==========================================
async function loadProfiles() {
  const res = await apiGet('/api/profile_overview');
  if (res.ok) state.profiles = res.profiles || [];
  if (!state.profiles.some(p => p.profile_id === state.currentProfile) && state.profiles[0]) state.currentProfile = state.profiles[0].profile_id;
}
async function loadRuntime() {
  const res = await apiGet('/api/runtime_config');
  if (res.ok) state.runtimeConfig = res.config || {};
  ensureRuntime();
}
async function loadGroupAccess() {
  const res = await apiGet('/api/group_access');
  if (res.ok) state.groupAccess = res.config || { mode: 'off', blacklist: [], whitelist: [] };
}
async function loadSignin() {
  const res = await apiGet('/api/sign_in_texts');
  if (res.ok) state.signInTexts = res.texts || {};
  state.signInTexts.good_things ||= [];
  state.signInTexts.bad_things ||= [];
  state.signInTexts.luck_ranges ||= [];
}
async function loadFate() {
  const [a, b] = await Promise.all([apiGet('/api/fate_cards'), apiGet('/api/fate_images')]);
  if (a.ok) state.fateCards = a.cards || [];
  if (b.ok) state.fateImages = b.images || [];
}
async function loadCards() {
  const [a, b] = await Promise.all([apiGet('/api/func_cards'), apiGet('/api/images')]);
  if (a.ok) state.funcCards = a.cards || [];
  if (b.ok) state.images = b.files || [];
}
async function loadTitles() {
  const res = await apiGet('/api/titles');
  if (res.ok) {
    state.titles = res.titles || [];
    state.titleCatalog = res.catalog || { conditions: [], effects: [] };
  }
}
async function loadStats() {
  const res = await apiGet('/api/user_stats');
  if (res.ok) state.stats = res.stats || { total_groups: 0, total_users: 0, card_holders: {}, groups: [] };
}
async function refreshActiveProfileData() {
  await Promise.all([loadRuntime(), loadGroupAccess(), loadSignin(), loadFate(), loadCards(), loadTitles(), loadStats()]);
}
async function refreshProfilesAndStats() {
  await Promise.all([loadProfiles(), loadStats()]);
}



async function loadAll(showMessage = false) {
  try {
    await loadProfiles();
    await refreshActiveProfileData();
    renderAll();
    if (showMessage) showToast('载入成功');
  } catch (e) {
    console.error(e);
    showToast('载入失败，请检查后端接口。', true);
  }
}

function animateCurrentProfileLabel(nextName) {
  const wrap = $('.current');
  const el = $('#currentProfileName');
  if (!wrap || !el) return;
  if (el.textContent === nextName) return;
  wrap.classList.remove('changing');
  void wrap.offsetWidth;
  el.textContent = nextName;
  wrap.classList.add('changing');
  clearTimeout(animateCurrentProfileLabel.timer);
  animateCurrentProfileLabel.timer = setTimeout(() => wrap.classList.remove('changing'), 360);
}
function updateTop() {
  animateCurrentProfileLabel(getProfileName());
  const quickProfile = $('#quickProfileCount');
  const quickGroup = $('#quickGroupCount');
  const quickUser = $('#quickUserCount');
  if (quickProfile) quickProfile.textContent = String(state.profiles.length || 0);
  if (quickGroup) quickGroup.textContent = String(state.stats.total_groups || 0);
  if (quickUser) quickUser.textContent = String(state.stats.total_users || 0);
}

const rarityWeightPalette = [
  { key: 'rarity_1', label: '普通', color: '#6f7d8e' },
  { key: 'rarity_2', label: '稀有', color: '#58a7ff' },
  { key: 'rarity_3', label: '史诗', color: '#9f6cff' },
  { key: 'rarity_4', label: '传说', color: '#ffbf5f' },
  { key: 'rarity_5', label: '神话', color: '#ff7078' },
];
const funcTypePalette = {
  attack: { label: '攻击', color: '#ff8d78' },
  heal: { label: '辅助', color: '#69dec1' },
  defense: { label: '防御', color: '#6f96ff' },
};
function buildRarityWeightPreview() {
  const weights = state.runtimeConfig?.func_cards_settings?.custom_rarity_weights || {};
  const items = rarityWeightPalette.map(item => {
    const value = Math.max(0, Number(weights[item.key] || 0));
    return { ...item, value };
  });
  const total = items.reduce((sum, item) => sum + item.value, 0);
  let cursor = 0;
  const segments = total > 0
    ? items.map(item => {
      const ratio = item.value / total;
      const start = cursor * 100;
      cursor += ratio;
      const end = cursor * 100;
      return `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
    })
    : ['rgba(255,255,255,.08) 0% 100%'];
  const previewItems = items.map(item => ({
    ...item,
    percent: total > 0 ? ((item.value / total) * 100) : 0,
  }));
  return {
    total,
    ringBackground: `conic-gradient(${segments.join(', ')})`,
    items: previewItems,
  };
}
function updateRarityChart() {
  const ring = $('#rarityRing');
  const legend = $('#rarityLegend');
  const total = $('#rarityWeightTotal');
  if (!ring || !legend || !total) return;
  const preview = buildRarityWeightPreview();
  ring.style.background = preview.ringBackground;
  total.textContent = String(preview.total || 0);
  legend.innerHTML = preview.items.map(item => `
    <div class="rarity-legend-item">
      <span class="rarity-dot" style="--dot-color:${item.color}"></span>
      <span>${item.label}</span>
      <span>${item.value} / ${item.percent.toFixed(1)}%</span>
    </div>`).join('');
}
function buildFuncTypeDistribution() {
  const items = Object.entries(funcTypePalette).map(([key, meta]) => {
    const count = state.funcCards.filter(card => (card.type || 'attack') === key).length;
    return { key, ...meta, count };
  });
  const total = items.reduce((sum, item) => sum + item.count, 0);
  let cursor = 0;
  const segments = total > 0
    ? items.filter(item => item.count > 0).map(item => {
      const ratio = item.count / total;
      const start = cursor * 100;
      cursor += ratio;
      const end = cursor * 100;
      return `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
    })
    : ['rgba(255,255,255,.08) 0% 100%'];
  return {
    total,
    ringBackground: `conic-gradient(${segments.join(', ')})`,
    items: items.map(item => ({
      ...item,
      percent: total > 0 ? ((item.count / total) * 100) : 0,
    })),
  };
}
function renderHeroAux() {
  const el = $('#heroAux');
  const hero = $('.hero');
  if (!el || !hero) return;
  el.innerHTML = '';
  hero.classList.remove('with-aux');
}
function openBatchEventDialog(kind) {
  const label = kind === 'good' ? '宜项' : '忌项';
  openDialog(`批量增加${label}`, `
    <div>
      <div class="field"><label>${label}文案（每行一条）</label><textarea class="textarea" id="batchEventInput" style="min-height:220px;"></textarea></div>
      <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="confirmBatchEventAdd('${kind}')">[ 写入${label} ]</button></div>
    </div>`, 'create');
}
function confirmBatchEventAdd(kind) {
  const raw = $('#batchEventInput')?.value || '';
  const list = raw.split(/\r?\n/).map(v => v.trim()).filter(Boolean);
  if (!list.length) return showToast('请至少输入一条文案。', true);
  const target = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
  target.push(...list);
  closeDialog();
  renderSignin();
  showToast('批量文案已写入。');
}
function setEventText(kind, idx, value) {
  const target = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
  target[idx] = value;
}
function openEditorFromImage(openEditor, inputId, file) {
  openEditor(-1);
  setTimeout(() => {
    const el = document.getElementById(inputId);
    if (el) el.value = file;
  }, 0);
}
function openFateEditorFromImage(file) {
  openEditorFromImage(openFateEditor, 'fateFilename', file);
}
function openFuncEditorFromImage(file) {
  openEditorFromImage(openFuncEditor, 'funcFilename', file);
}
async function duplicateFateCard(i) {
  const original = state.fateCards[i];
  if (!original) return;
  const copy = JSON.parse(JSON.stringify(original));
  copy.text = `${copy.text || '未命名命运牌'} 副本`;
  state.fateCards.splice(i + 1, 0, copy);
  renderFate();
  await saveFateCards(false);
  showToast('命运牌已复制。');
}
async function duplicateFuncCard(i) {
  const original = state.funcCards[i];
  if (!original) return;
  const copy = JSON.parse(JSON.stringify(original));
  copy.card_name = `${copy.card_name || '未命名功能牌'} 副本`;
  state.funcCards.splice(i + 1, 0, copy);
  renderCards();
  await saveFuncCards(false);
  showToast('功能牌已复制。');
}
function isFateCardIncomplete(card) {
  return !(card.text || '').trim() || !card.filename || !state.fateImages.includes(card.filename);
}
function ensureFateDraftCards() {
  const boundFiles = new Set(state.fateCards.map(card => card.filename).filter(Boolean));
  state.fateImages.filter(file => !boundFiles.has(file)).forEach(file => {
    state.fateCards.push({ text: '', gold: 0, filename: file });
  });
}
function detectIncompleteFateCards() {
  ensureFateDraftCards();
  state.fateCards.sort((a, b) => Number(isFateCardIncomplete(b)) - Number(isFateCardIncomplete(a)));
  renderFate();
  const pendingCount = state.fateCards.filter(isFateCardIncomplete).length;
  showToast(pendingCount ? `已置顶 ${pendingCount} 张未完成命运牌。` : '当前没有未完成的命运牌。');
}
function isFuncCardIncomplete(card) {
  return !(card.card_name || '').trim() || !card.filename || !state.images.includes(card.filename) || !(card.description || '').trim() || !(card.tags || []).length;
}
function setFuncFilter(value) {
  state.funcFilter = value || 'all';
  renderCards();
}
// ===== [ page: overview ] ==================================================
function renderOverview() {
  const page = $('#page-overview');
  page.innerHTML = `
    <div class="grid">
      <section class="panel col-8">
        <div class="panel-head">
          <div>
            <div class="panel-title">方案管理</div>
            <div class="panel-note">直接放在主界面。切换、重命名、绑定群号都在这里完成。</div>
          </div>
          <button class="btn-strong" onclick="openCreateProfileDialog()">[ 新建方案 ]</button>
        </div>
        <div class="profile-list">
          ${state.profiles.map(p => {
      const active = p.profile_id === state.currentProfile;
      const justActivated = state.justActivatedProfile === p.profile_id;
      return `
            <article class="profile-card ${active ? 'active' : ''} ${justActivated ? 'just-activated' : ''}">
              <div class="profile-main">
                  <h3>${esc(p.display_name || p.profile_id)}</h3>
                <div class="row" style="margin-bottom:4px;">
                  ${p.is_default ? '<span class="badge light">默认方案</span>' : ''}
                  <span class="badge">绑定群组 ${(p.group_count || 0)}</span>
                </div>
                <div class="meta">用户 ${p.user_count || 0} ｜ 功能牌 ${p.func_card_count || 0} ｜ 命运牌 ${p.fate_card_count || 0}</div>
                <div class="row" style="margin:4px 0;">
                  ${(p.groups || []).slice(0, 3).map(g => `<span class="badge">群 ${esc(g)}</span>`).join('') || '<span class="helper">暂无绑定群组</span>'}
                </div>
                <div class="row">
                  <button class="btn" onclick="editProfile('${esc(p.profile_id)}')">[ 编辑 ]</button>
                  <button class="btn" onclick="bindGroupPrompt('${esc(p.profile_id)}')">[ 绑定群号 ]</button>
                </div>
                ${(p.groups || []).slice(0, 3).length ? `<div class="row" style="margin-top:4px;">${(p.groups || []).slice(0, 3).map(g => `<button class="btn-mini" onclick="unbindGroup('${esc(p.profile_id)}','${esc(g)}')">解绑 ${esc(g)}</button>`).join('')}</div>` : ''}
              </div>
              <div class="profile-switch-slot">
                <button class="profile-switch-btn" ${active ? 'disabled' : `onclick="useProfile('${esc(p.profile_id)}')"`}>
                  ${active ? '使用中' : '切换'}
                </button>
              </div>
            </article>`;
    }).join('')}
        </div>
      </section>

      <section class="panel col-4">
        <div class="panel-head">
          <div>
            <div class="panel-title">访问控制</div>
            <div class="panel-note">黑名单与白名单互斥，只能有一种模式处于启用状态。</div>
          </div>
        </div>
        <div class="switch-group" style="margin-bottom:12px;">
          <button class="mode-btn ${state.groupAccess.mode === 'off' ? 'active' : ''}" onclick="setAccessMode('off')">关闭限制</button>
          <button class="mode-btn black ${state.groupAccess.mode === 'blacklist' ? 'active' : ''}" onclick="setAccessMode('blacklist')">黑名单模式</button>
          <button class="mode-btn white ${state.groupAccess.mode === 'whitelist' ? 'active' : ''}" onclick="setAccessMode('whitelist')">白名单模式</button>
        </div>
        ${state.groupAccess.mode === 'blacklist' ? `
        <div class="field" style="margin-bottom:10px;">
          <label>黑名单群号（每行一个）</label>
          <textarea class="textarea" id="blacklistInput">${esc((state.groupAccess.blacklist || []).join('\n'))}</textarea>
        </div>` : ''}
        ${state.groupAccess.mode === 'whitelist' ? `
        <div class="field">
          <label>白名单群号（每行一个）</label>
          <textarea class="textarea" id="whitelistInput">${esc((state.groupAccess.whitelist || []).join('\n'))}</textarea>
        </div>` : ''}
        <div class="row" style="margin-top:10px;">
          <button class="btn-strong" onclick="saveGroupAccess()">[ 保存访问控制 ]</button>
        </div>
        <div class="overview-stats">
          <div class="overview-stat"><b id="quickProfileCount">${state.profiles.length || 0}</b><span>方案数量</span></div>
          <div class="overview-stat"><b id="quickGroupCount">${state.stats.total_groups || 0}</b><span>群组总量</span></div>
          <div class="overview-stat"><b id="quickUserCount">${state.stats.total_users || 0}</b><span>用户总量</span></div>
        </div>
      </section>
    </div>`;
}

// ===== [ page: runtime ] ===================================================
function renderRuntime() {
  ensureRuntime();
  const c = state.runtimeConfig;
  const f = c.func_cards_settings;
  const e = f.economy_settings;
  const w = f.custom_rarity_weights;
  const preview = buildRarityWeightPreview();
  const fateEnabled = !!c.fate_cards_settings.enable;
  const funcEnabled = !!f.enable;
  const duelEnabled = funcEnabled && !!f.enable_public_duel_mode;
  const weightEnabled = funcEnabled;
  $('#page-runtime').innerHTML = `
    <div class="grid">
      <section class="panel col-4">
        <div class="panel-head"><div><div class="panel-title">模块开关</div><div class="panel-note">开关打开后，右侧对应参数才会进入可调状态。</div></div></div>
        ${toggleBox('命运牌系统', '开启后才会启用命运牌相关抽取与每日上限配置。', 'fate_cards_settings.enable', c.fate_cards_settings.enable)}
        ${toggleBox('功能牌系统', '关闭时，功能牌的经济、稀有度和对赌相关配置都会锁定。', 'func_cards_settings.enable', f.enable)}
        ${toggleBox('骰子牌系统', '控制骰子功能牌与相关规则入口是否开放。', 'func_cards_settings.enable_dice_cards', f.enable_dice_cards)}
        ${toggleBox('公开对赌模式', '开启后，才允许配置每日次数与赌注范围。', 'func_cards_settings.enable_public_duel_mode', f.enable_public_duel_mode)}
        ${toggleBox('同稀有度优先不重复', '开启后，抽到功能牌时会尽量避免连续给出同稀有度重复内容。', 'func_cards_settings.enable_rarity_dedup', f.enable_rarity_dedup)}
      </section>

      <section class="panel col-8">
        <div class="panel-head">
          <div>
            <div class="panel-title">参数配置</div>
            <div class="panel-note">稀有度名称已改为：普通 / 稀有 / 史诗 / 传说 / 神话。</div>
          </div>
          <button class="btn-strong" onclick="saveRuntime()">[ 保存运行配置 ]</button>
        </div>

        <div class="runtime-split">
          <div class="config-block ${fateEnabled ? '' : 'locked'}">
            ${numField('命运牌每日上限', 'fate_cards_settings.daily_draw_limit', c.fate_cards_settings.daily_draw_limit, !fateEnabled)}
          </div>
          <div class="config-block ${funcEnabled ? '' : 'locked'}">
            ${selectField('稀有度模式', 'func_cards_settings.rarity_mode', f.rarity_mode, [['default', '默认'], ['custom', '自定义']], !funcEnabled)}
          </div>
        </div>

        <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">公开对赌配置</div><div class="panel-note">把对赌次数与赌注范围放到同一行，方便整体调整。</div></div></div>
        <div class="runtime-three config-block ${duelEnabled ? '' : 'locked'}">
          ${numField('对赌每日次数', 'func_cards_settings.public_duel_daily_limit', f.public_duel_daily_limit, !duelEnabled)}
          ${numField('最小赌注', 'func_cards_settings.public_duel_min_stake', f.public_duel_min_stake, !duelEnabled)}
          ${numField('最大赌注', 'func_cards_settings.public_duel_max_stake', f.public_duel_max_stake, !duelEnabled)}
        </div>

        <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">抽卡经济</div><div class="panel-note">上排控制掉率与免费次数，下排控制单次消耗与保底。</div></div></div>
        <div class="runtime-split config-block ${funcEnabled ? '' : 'locked'}">
          ${numField('基础掉率', 'func_cards_settings.economy_settings.draw_probability', e.draw_probability, !funcEnabled)}
          ${numField('每日免费抽取', 'func_cards_settings.economy_settings.free_daily_draw', e.free_daily_draw, !funcEnabled)}
          ${numField('超出免费后的单次消耗', 'func_cards_settings.economy_settings.draw_cost', e.draw_cost, !funcEnabled)}
          ${numField('保底次数', 'func_cards_settings.economy_settings.pity_threshold', e.pity_threshold, !funcEnabled)}
        </div>

        <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">稀有度权重</div><div class="panel-note">左侧逐项输入，右侧实时预览各稀有度占比。</div></div></div>
        <div class="rarity-weight-layout config-block ${weightEnabled ? '' : 'locked'}">
          <div class="rarity-weight-fields">
            ${numField('普通', 'func_cards_settings.custom_rarity_weights.rarity_1', w.rarity_1, !weightEnabled)}
            ${numField('稀有', 'func_cards_settings.custom_rarity_weights.rarity_2', w.rarity_2, !weightEnabled)}
            ${numField('史诗', 'func_cards_settings.custom_rarity_weights.rarity_3', w.rarity_3, !weightEnabled)}
            ${numField('传说', 'func_cards_settings.custom_rarity_weights.rarity_4', w.rarity_4, !weightEnabled)}
            ${numField('神话', 'func_cards_settings.custom_rarity_weights.rarity_5', w.rarity_5, !weightEnabled)}
          </div>
          <div class="rarity-ring-wrap">
            <div class="rarity-ring" id="rarityRing" style="background:${preview.ringBackground};">
              <div class="rarity-ring-center"><div><b id="rarityWeightTotal">${preview.total}</b><span>权重总值</span></div></div>
            </div>
            <div class="rarity-legend-title">实时概率分布</div>
            <div class="rarity-legend" id="rarityLegend">
              ${preview.items.map(item => `
                <div class="rarity-legend-item">
                  <span class="rarity-dot" style="--dot-color:${item.color}"></span>
                  <span>${item.label}</span>
                  <span>${item.value} / ${item.percent.toFixed(1)}%</span>
                </div>`).join('')}
            </div>
          </div>
        </div>
      </section>
    </div>`;
  updateRarityChart();
}

function toggleBox(label, desc, path, on) {
  return `<div class="toggle-row"><div class="toggle-copy"><div>${label}</div><div class="helper">${desc}</div></div><div class="toggle-box ${on ? 'on' : ''}" onclick="toggleRuntime('${path}', this)"></div></div>`;
}
function numField(label, path, value, disabled = false) {
  return `<div class="field"><label>${label}</label><input class="input" type="number" value="${esc(value ?? 0)}" ${disabled ? 'disabled' : ''} oninput="setRuntimeValue('${path}', this.value)"></div>`;
}
function selectField(label, path, value, options, disabled = false) {
  return `<div class="field"><label>${label}</label><select class="select" ${disabled ? 'disabled' : ''} onchange="setRuntimeValue('${path}', this.value)">${options.map(([v, t]) => `<option value="${esc(v)}" ${String(v) === String(value) ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>`;
}

// ===== [ page: signin ] ====================================================
function renderSignin() {
  const ranges = state.signInTexts.luck_ranges || [];
  $('#page-signin').innerHTML = `
    <div class="grid signin-layout">
      <section class="panel col-7">
        <div class="panel-head">
          <div>
            <div class="panel-title">事件文本池</div>
            <div class="panel-note">签到预览会按“宜 / 忌”格式生成，这里直接维护对应文案。</div>
          </div>
        </div>
        <div class="signin-columns">
          <div>
            <div class="signin-list-head">
              <div class="signin-list-title">宜项列表</div>
              <div class="signin-actions">
                <button class="btn" onclick="openBatchEventDialog('good')">[ 批量增加宜项 ]</button>
                <button class="btn-danger" onclick="deleteSelectedEvents('good')">[ 批量删除已勾选 ]</button>
              </div>
            </div>
            <div class="event-list">
              ${(state.signInTexts.good_things || []).map((item, i) => eventItem('good', item, i)).join('') || '<div class="empty">暂无宜项文本</div>'}
            </div>
            <div class="row" style="margin-top:8px;">
              <button class="btn" onclick="addSingleEvent('good')">[ 增加一条宜项 ]</button>
            </div>
          </div>
          <div>
            <div class="signin-list-head">
              <div class="signin-list-title">忌项列表</div>
              <div class="signin-actions">
                <button class="btn" onclick="openBatchEventDialog('bad')">[ 批量增加忌项 ]</button>
                <button class="btn-danger" onclick="deleteSelectedEvents('bad')">[ 批量删除已勾选 ]</button>
              </div>
            </div>
            <div class="event-list">
              ${(state.signInTexts.bad_things || []).map((item, i) => eventItem('bad', item, i)).join('') || '<div class="empty">暂无忌项文本</div>'}
            </div>
            <div class="row" style="margin-top:8px;">
              <button class="btn" onclick="addSingleEvent('bad')">[ 增加一条忌项 ]</button>
            </div>
          </div>
        </div>
      </section>

      <section class="panel col-5">
        <div class="panel-head">
          <div>
            <div class="panel-title">签到预览</div>
            <div class="panel-note">按 QQ 内实际生成习惯分行显示，方便直接比对最终效果。</div>
          </div>
          <button class="btn-strong" onclick="saveSignin()">[ 保存签到配置 ]</button>
        </div>
        <div class="row" style="margin-bottom:10px;">
          <button class="btn-strong" onclick="previewSignin()">[ 生成签到预览 ]</button>
        </div>
        <div class="tag-preview signin-preview" id="signinPreview">尚未生成预览。</div>
        <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">运势区间</div><div class="panel-note">标签、数值区间和点评文案会直接影响预览结果。</div></div><button class="btn" onclick="addRange()">[ 新增区间 ]</button></div>
        <div class="stack">
          ${ranges.map((r, i) => `
            <div class="profile-card signin-range">
              <div class="field-grid four">
                <div class="field"><label>标签</label><input class="input" value="${esc(r.label || '')}" onchange="setRange(${i}, 'label', this.value)"></div>
                <div class="field"><label>最小值</label><input class="input" type="number" value="${esc(r.min ?? 0)}" onchange="setRange(${i}, 'min', Number(this.value))"></div>
                <div class="field"><label>最大值</label><input class="input" type="number" value="${esc(r.max ?? 0)}" onchange="setRange(${i}, 'max', Number(this.value))"></div>
                <div class="field"><label>金币修正</label><input class="input" type="number" value="${esc(r.gold_delta ?? 0)}" onchange="setRange(${i}, 'gold_delta', Number(this.value))"></div>
              </div>
              <div class="field" style="margin-top:10px;"><label>点评文案（每行一条）</label><textarea class="textarea" onchange="setRangeComments(${i}, this.value)">${esc((r.comments || []).join('\n'))}</textarea></div>
              <div class="row" style="margin-top:10px;"><button class="btn-danger" onclick="removeRange(${i})">[ 删除区间 ]</button></div>
            </div>`).join('') || '<div class="empty">暂无运势区间</div>'}
        </div>
      </section>
    </div>`;
}

function eventItem(kind, item, i) {
  const checked = (kind === 'good' ? state.goodSelected : state.badSelected).includes(i) ? 'checked' : '';
  const placeholder = kind === 'good' ? '输入宜项文案' : '输入忌项文案';
  return `<div class="event-item"><input class="event-check" type="checkbox" ${checked} onchange="toggleEventSelect('${kind}', ${i}, this.checked)"><input class="input" id="eventInput-${kind}-${i}" value="${esc(item)}" placeholder="${placeholder}" oninput="setEventText('${kind}', ${i}, this.value)"><button class="btn-danger" onclick="removeEvent('${kind}', ${i})">[ 删除 ]</button></div>`;
}

// ===== [ page: fate ] ======================================================
function renderFate() {
  ensureFateDraftCards();
  $('#page-fate').innerHTML = `
    <div class="grid">
      <section class="panel col-12 fate-main">
        <div class="panel-head">
          <div>
            <div class="panel-title">命运牌档案</div>
            <div class="panel-note">上传图片后可用“检测未完成编辑的牌”把未完善的牌直接置顶。</div>
          </div>
          <div class="row">
            <button class="btn-strong" onclick="openFateEditor(-1)">[ 新增命运牌 ]</button>
            <button class="btn" onclick="uploadFateImages()">[ 批量上传图片 ]</button>
            <button class="btn-danger" onclick="detectIncompleteFateCards()">[ 检测未完成编辑的牌 ]</button>
            <button class="btn" onclick="saveFateCards()">[ 保存全部 ]</button>
          </div>
        </div>
        <div class="archive-grid">
          ${state.fateCards.map((card, i) => fateItem(card, i)).join('') || '<div class="empty">暂无命运牌</div>'}
        </div>
      </section>
    </div>`;
}

function fateItem(card, i) {
  const has = card.filename && state.fateImages.includes(card.filename);
  const src = has ? `/fate_assets/${encodeURIComponent(card.filename)}?profile=${encodeURIComponent(state.currentProfile)}` : '';
  const incomplete = isFateCardIncomplete(card);
  return `
    <article class="archive-card${incomplete ? ' incomplete' : ''}">
      <div class="archive-cover">${has ? `<img src="${src}" alt="命运牌图片">` : '未绑定图片'}</div>
      <div class="archive-body">
        <div class="archive-title">${esc(card.text || '未命名命运牌')}</div>
        <div class="archive-meta">
          <span class="badge orange">金币 ${esc(card.gold ?? 0)}</span>
          ${incomplete ? '<span class="badge">未完成</span>' : ''}
        </div>
        <div class="archive-actions">
          <button class="btn-strong" onclick="openFateEditor(${i})">[ 编辑 ]</button>
          <button class="btn-green" onclick="duplicateFateCard(${i})">[ 复制 ]</button>
          <button class="btn-danger" onclick="deleteFateCard(${i})">[ 删除 ]</button>
        </div>
      </div>
    </article>`;
}

// ===== [ page: cards ] =====================================================
function renderCards() {
  const filter = state.funcFilter || 'all';
  const incompleteCount = state.funcCards.filter(isFuncCardIncomplete).length;
  const unusedImages = state.images.filter(file => !state.funcCards.some(card => card.filename === file));
  const filteredEntries = state.funcCards.map((card, index) => ({ card, index })).filter(({ card }) => {
    const type = card.type || 'attack';
    if (filter === 'all') return true;
    if (filter === 'other') return !Object.keys(funcTypePalette).includes(type);
    return type === filter;
  });
  $('#page-cards').innerHTML = `
    <div class="grid">
      <section class="panel col-12">
        <div class="panel-head">
          <div>
            <div class="panel-title">功能牌档案</div>
            <div class="panel-note">用下拉筛选不同类型的牌，稀有度边缘会发出更明显的淡光。</div>
          </div>
          <div class="row">
            <button class="btn-strong" onclick="openFuncEditor(-1)">[ 新增功能牌 ]</button>
            <button class="btn" onclick="batchAddCards()">[ 批量添加 ]</button>
            <button class="btn" onclick="uploadFuncImages()">[ 批量上传图片 ]</button>
            <button class="btn" onclick="saveFuncCards()">[ 保存全部 ]</button>
          </div>
        </div>
        <div class="filter-bar">
          <div class="filter-bar-title">类型筛选</div>
          <select class="select filter-select" onchange="setFuncFilter(this.value)">
            <option value="all" ${filter === 'all' ? 'selected' : ''}>全部</option>
            <option value="attack" ${filter === 'attack' ? 'selected' : ''}>攻击</option>
            <option value="heal" ${filter === 'heal' ? 'selected' : ''}>辅助</option>
            <option value="defense" ${filter === 'defense' ? 'selected' : ''}>防御</option>
            <option value="other" ${filter === 'other' ? 'selected' : ''}>其他</option>
          </select>
          <div class="filter-summary">当前显示 ${filteredEntries.length} / ${state.funcCards.length} ｜ 未完成 ${incompleteCount} 张</div>
        </div>
        ${filter === 'all' ? `
        <div class="archive-index-group" style="margin-bottom:14px;">
          <div class="archive-index-title">待建档图片</div>
          <div class="pending-grid func-pending-grid">
            ${unusedImages.map(file => `
              <article class="archive-card">
                <div class="archive-cover"><img src="/assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}" alt="${esc(file)}"></div>
                <div class="archive-body">
                  <div class="pending-caption">这张图片还没有被任何功能牌使用。</div>
                  <div class="archive-actions">
                    <button class="btn-green" onclick="openFuncEditorFromImage('${esc(file)}')">[ 编辑 ]</button>
                    <button class="btn" onclick="openFuncEditorFromImage('${esc(file)}')">[ 建牌 ]</button>
                    <button class="btn-danger" onclick="deleteFuncImage('${esc(file)}')">[ 删除 ]</button>
                  </div>
            </div>
              </article>`).join('') || '<div class="empty">当前没有待建档图片</div>'}
          </div>
        </div>` : ''}
        <div class="archive-grid func-archive-grid">
          ${filteredEntries.map(entry => funcItem(entry.card, entry.index)).join('') || '<div class="empty">当前筛选下没有功能牌</div>'}
        </div>
      </section>
    </div>`;
  renderHeroAux();
}

function funcItem(card, i) {
  const has = card.filename && state.images.includes(card.filename);
  const src = has ? `/assets/${encodeURIComponent(card.filename)}?profile=${encodeURIComponent(state.currentProfile)}` : '';
  const tags = (card.tags || []).slice(0, 4).map(tag => `<span class="badge">${esc(humanizeTag(tag))}</span>`).join('') || '<span class="helper">未设定效果</span>';
  return `
    <article class="archive-card func-card rarity-${Number(card.rarity) || 1}">
      <div class="archive-cover">${has ? `<img src="${src}" alt="功能牌图片">` : '未绑定图片'}</div>
      <div class="archive-body">
        <div class="archive-title">${esc(card.card_name || '未命名功能牌')}</div>
        <div class="archive-meta">
          <span class="badge light">${esc(rarityLabelMap[Number(card.rarity) || 1] || '普通')}</span>
          <span class="badge">${esc(typeLabelMap[card.type] || '未分类')}</span>
        </div>
        <div class="archive-tag-row">${tags}</div>
        <div class="archive-desc">${esc(card.description || '当前还没有描述。')}</div>
        <div class="archive-actions">
          <button class="btn-strong" onclick="openFuncEditor(${i})">[ 编辑 ]</button>
          <button class="btn-green" onclick="duplicateFuncCard(${i})">[ 复制 ]</button>
          <button class="btn-danger" onclick="deleteFuncCard(${i})">[ 删除 ]</button>
        </div>
      </div>
    </article>`;
}

function buildFuncRarityDistribution() {
  const total = state.funcCards.length || 0;
  return Object.entries(rarityLabelMap).map(([level, label]) => {
    const rarity = Number(level);
    const count = state.funcCards.filter(card => Number(card.rarity || 1) === rarity).length;
    const palette = rarityWeightPalette.find(item => item.key === `rarity_${rarity}`);
    return {
      rarity,
      label,
      count,
      percent: total ? (count / total) * 100 : 0,
      color: palette?.color || '#6f7d8e',
    };
  });
}

// ===== [ page: stats ] =====================================================
function renderStats() {
  const holders = Object.entries(state.stats.card_holders || {}).sort((a, b) => b[1] - a[1]);
  const groups = [...(state.stats.groups || [])].sort((a, b) => (b.user_count || 0) - (a.user_count || 0));
  const groupMax = Math.max(1, ...groups.map(group => Number(group.user_count || 0)));
  const fateCompleted = state.fateCards.filter(card => !isFateCardIncomplete(card)).length;
  const fateBound = state.fateCards.filter(card => card.filename && state.fateImages.includes(card.filename)).length;
  const funcCompleted = state.funcCards.filter(card => !isFuncCardIncomplete(card)).length;
  const funcTypeDistribution = buildFuncTypeDistribution().items;
  const funcRarityDistribution = buildFuncRarityDistribution();
  const fateAvgGold = state.fateCards.length
    ? (state.fateCards.reduce((sum, card) => sum + Number(card.gold || 0), 0) / state.fateCards.length).toFixed(1)
    : '0.0';
  const fateCompletionPercent = state.fateCards.length ? (fateCompleted / state.fateCards.length) * 100 : 0;
  const fateBoundPercent = state.fateCards.length ? (fateBound / state.fateCards.length) * 100 : 0;
  const profileOptions = state.profiles.map(p => `<option value='${esc(p.profile_id)}' ${p.profile_id === state.currentProfile ? 'selected' : ''}>${esc(p.display_name)}</option>`).join('');
  const kpis = [
    { label: '群组数量', value: state.stats.total_groups || 0, note: '已接入当前方案的群组', accent: '#6f96ff' },
    { label: '用户数量', value: state.stats.total_users || 0, note: '方案下被统计到的用户', accent: '#69dec1' },
    { label: '功能牌卡池', value: state.funcCards.length, note: `已完善 ${funcCompleted} / ${state.funcCards.length || 0}`, accent: '#9f6cff' },
    { label: '命运牌卡池', value: state.fateCards.length, note: `已完善 ${fateCompleted} / ${state.fateCards.length || 0}`, accent: '#ff9a7c' },
  ];

  $('#page-stats').innerHTML = `
    <div class='grid'>
      <section class='panel col-12 stats-main'>
        <div class='stats-profile-bar'>
          <div>
            <div class='tiny'>[ PROFILE / ANALYTICS ]</div>
            <div class='stats-profile-title'>${esc(getProfileName())}</div>
            <div class='panel-note'>把方案概览、群组热度、持牌排行和卡池完成度压成一屏，切换方案后会同步更新所有统计。</div>
            <div class='stats-profile-meta'>
              <span class='badge light'>群组 ${state.stats.total_groups || 0}</span>
              <span class='badge'>用户 ${state.stats.total_users || 0}</span>
              <span class='badge orange'>排行条目 ${holders.length}</span>
            </div>
          </div>
          <div class='row'>
            <select class='select' style='width:220px;' onchange='useProfile(this.value)'>${profileOptions}</select>
          </div>
        </div>
        <div class='stats-kpi-grid'>
          ${kpis.map(item => `
            <article class='stats-kpi' style='--stats-accent:${item.accent};'>
              <span>${item.label}</span>
              <b>${item.value}</b>
              <small>${item.note}</small>
            </article>`).join('')}
        </div>
      </section>

      <section class='panel col-7'>
        <div class='panel-head'>
          <div>
            <div class='panel-title'>群组热度分布</div>
            <div class='panel-note'>按用户数量排序，用进度条快速看出当前方案下哪些群体量更高。</div>
          </div>
        </div>
        <div class='stats-group-list'>
          ${groups.map(group => {
      const count = Number(group.user_count || 0);
      const width = count ? Math.max(12, (count / groupMax) * 100) : 0;
      return `
              <article class='group-entry'>
                <div class='group-entry-head'>
                  <div>
                    <div class='group-entry-id'>${esc(group.group_id)}</div>
                    <div class='group-entry-meta'>群组成员统计</div>
                  </div>
                  <span class='badge'>${count} 用户</span>
                </div>
                <div class='group-bar'><div class='group-bar-fill' style='width:${width}%;'></div></div>
              </article>`;
    }).join('') || `<div class='empty'>暂无群组数据</div>`}
        </div>
      </section>

      <section class='panel col-5'>
        <div class='panel-head'>
          <div>
            <div class='panel-title'>持牌排行</div>
            <div class='panel-note'>榜单改成独立名次卡片，层级更清楚，不会像一列流水账。</div>
          </div>
        </div>
        <div class='leaderboard-list'>
          ${holders.slice(0, 10).map((item, idx) => `
            <article class='leaderboard-item'>
              <span class='rank-badge ${idx < 3 ? `rank-top-${idx + 1}` : ''}'>#${idx + 1}</span>
              <div>
                <div class='leaderboard-name'>${esc(item[0])}</div>
                <div class='group-entry-meta'>当前方案持牌人数排行</div>
              </div>
              <div class='leaderboard-count'>${item[1]} 人持有</div>
            </article>`).join('') || `<div class='empty'>暂无持牌排行</div>`}
        </div>
      </section>

      <section class='panel col-6'>
        <div class='panel-head'>
          <div>
            <div class='panel-title'>卡池概览</div>
            <div class='panel-note'>把命运牌和功能牌拆成两张统计卡，信息更完整，也更有真正的卡片感。</div>
          </div>
        </div>
        <div class='pool-summary-grid'>
          <article class='pool-card fate'>
            <div class='pool-card-head'>
              <div>
                <div class='tiny'>[ FATE DECK ]</div>
                <div class='pool-card-title'>命运牌</div>
              </div>
              <div class='pool-card-value'>${state.fateCards.length}</div>
            </div>
            <div class='pool-card-meta'>已完善 ${fateCompleted} 张 ｜ 平均金币值 ${fateAvgGold}</div>
            <div class='mini-list'>
              <div class='mini-metric'>
                <div class='mini-metric-row'><span>建档完成度</span><span>${fateCompletionPercent.toFixed(1)}%</span></div>
                <div class='mini-bar'><div class='mini-bar-fill' style='width:${fateCompletionPercent}%; --metric-start:#ffb08c; --metric-end:#ff7f8d;'></div></div>
              </div>
              <div class='mini-metric'>
                <div class='mini-metric-row'><span>图片绑定率</span><span>${fateBoundPercent.toFixed(1)}%</span></div>
                <div class='mini-bar'><div class='mini-bar-fill' style='width:${fateBoundPercent}%; --metric-start:#ffc46d; --metric-end:#ff8a72;'></div></div>
              </div>
            </div>
          </article>

          <article class='pool-card func'>
            <div class='pool-card-head'>
              <div>
                <div class='tiny'>[ FUNCTION DECK ]</div>
                <div class='pool-card-title'>功能牌</div>
              </div>
              <div class='pool-card-value'>${state.funcCards.length}</div>
            </div>
            <div class='pool-card-meta'>已完善 ${funcCompleted} 张 ｜ 未完成 ${Math.max(0, state.funcCards.length - funcCompleted)} 张</div>
            <div class='mini-list'>
              ${funcTypeDistribution.map(item => `
                <div class='mini-metric'>
                  <div class='mini-metric-row'><span>${item.label}</span><span>${item.count} / ${item.percent.toFixed(1)}%</span></div>
                  <div class='mini-bar'><div class='mini-bar-fill' style='width:${item.percent}%; --metric-start:${item.color}; --metric-end:${item.color};'></div></div>
                </div>`).join('')}
            </div>
          </article>
        </div>
      </section>

      <section class='panel col-6'>
        <div class='panel-head'>
          <div>
            <div class='panel-title'>功能牌稀有度分布</div>
            <div class='panel-note'>用更柔和但更分明的颜色显示稀有度占比，方便快速判断当前牌池结构。</div>
          </div>
        </div>
        <div class='stats-distribution-list'>
          ${funcRarityDistribution.map(item => `
            <article class='dist-item'>
              <div class='dist-item-head'>
                <span class='dist-dot' style='--dot-color:${item.color};'></span>
                <div class='dist-label'>${item.label}</div>
                <div class='dist-count'>${item.count} 张 / ${item.percent.toFixed(1)}%</div>
              </div>
              <div class='mini-bar'><div class='mini-bar-fill' style='width:${item.percent}%; --metric-start:${item.color}; --metric-end:${item.color};'></div></div>
            </article>`).join('')}
        </div>
      </section>
    </div>`;
}

function renderAll() {
  renderOverview();
  renderRuntime();
  renderSignin();
  renderFate();
  renderCards();
  renderStats();
  updateTop();
  setPage(state.activePage);
}

async function useProfile(id) {
  state.currentProfile = id;
  state.justActivatedProfile = id;
  await refreshActiveProfileData();
  renderAll();
  clearTimeout(useProfile.fxTimer);
  useProfile.fxTimer = setTimeout(() => {
    if (state.justActivatedProfile === id) {
      state.justActivatedProfile = '';
      renderOverview();
      updateTop();
      setPage(state.activePage);
    }
  }, 760);
  showToast(`已切换到方案：${getProfileName(id)}`);
}

async function editProfile(id) {
  const current = state.profiles.find(p => p.profile_id === id);
  state.editingProfileId = id;
  openDialog('编辑方案', `
    <div>
      <div>
        <div class="field">
          <label>方案名称</label><input class="input" id="newProfileName" value="${esc(current?.display_name || '')}">
        </div>
        <div class="field" style="margin-top:12px;"><label>绑定群号（每行一个）</label><textarea class="textarea" id="editProfileGroups">${esc((current?.groups || []).join('\n'))}</textarea></div>
        <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveProfileEdit()">[ 保存方案 ]</button><button class="btn-danger" onclick="deleteProfileConfirm()">[ 删除方案 ]</button></div>
      </div>
    </div>`, 'create');
}

async function saveProfileEdit() {
  const id = state.editingProfileId;
  const current = state.profiles.find(p => p.profile_id === id);
  const name = $('#newProfileName')?.value?.trim();
  const groupLines = ($('#editProfileGroups')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean);
  if (!id || !name) return showToast('方案名称不能为空。', true);
  const res = await apiPost('/api/profile_meta', { profile_id: id, display_name: name, cover_image: '' });
  if (!res.ok) return showToast(res.error || '保存失败。', true);
  const before = new Set(current?.groups || []);
  const after = new Set(groupLines);
  for (const gid of before) {
    if (!after.has(gid)) await apiPost('/api/profile_unbind_group', { profile_id: id, group_id: gid });
  }
  for (const gid of after) {
    if (!before.has(gid)) await apiPost('/api/profile_bind_group', { profile_id: id, group_id: gid });
  }
  closeDialog();
  await refreshProfilesAndStats();
  renderAll();
  showToast('方案编辑已保存。');
}

async function deleteProfileConfirm() {
  const id = state.editingProfileId;
  const current = state.profiles.find(p => p.profile_id === id);
  if (!id) return;
  if (current?.is_default) return showToast('默认方案不能删除。', true);
  if (!confirm(`确认删除方案「${current?.display_name || id}」吗？\n绑定到该方案的群组会自动切回默认方案。`)) return;
  try {
    const res = await apiDeleteProfileById(id);
    if (!res.ok) return showToast(`删除失败：${res.error || 'unknown error'}`, true);
    closeDialog();
    state.currentProfile = res.fallback_profile || 'default';
    state.profiles = state.profiles.filter(p => p.profile_id !== id);
    await loadProfiles();
    await refreshActiveProfileData();
    renderAll();
    showToast('方案已删除。');
  } catch (e) {
    console.error(e);
    showToast(`删除失败：${e?.message || e}`, true);
  }
}

async function bindGroupPrompt(id) {
  const gid = prompt('请输入群号');
  if (!gid) return;
  if (!/^\d+$/.test(gid)) return showToast('群号格式无效。', true);
  const res = await apiPost('/api/profile_bind_group', { profile_id: id, group_id: gid });
  if (res.ok) {
    await refreshProfilesAndStats();
    renderAll();
    showToast('群号绑定成功。');
  } else {
    showToast(res.error || '绑定失败。', true);
  }
}

async function unbindGroup(id, gid) {
  if (!confirm(`确认解绑群号 ${gid} 吗？`)) return;
  const res = await apiPost('/api/profile_unbind_group', { profile_id: id, group_id: gid });
  if (res.ok) {
    await refreshProfilesAndStats();
    renderAll();
    showToast('群号已解绑。');
  } else {
    showToast(res.error || '解绑失败。', true);
  }
}

// ===== [ dialogs / shared ui ] =============================================
function openDialog(title, html, mode = '') {
  $('#dialogTitle').textContent = title;
  $('#dialogBody').innerHTML = html;
  $('#dialog').classList.add('show');
  $('#dialog .dialog-card').classList.toggle('create-mode', mode === 'create');
}
function closeDialog() {
  $('#dialog').classList.remove('show');
  $('#dialog .dialog-card').classList.remove('create-mode');
}

function copySourceChoices() {
  return [
    { value: '__blank__', label: '无（空白方案）' },
    { value: '__builtin_default__', label: '内置默认模板' },
    ...state.profiles.map(p => ({ value: p.profile_id, label: p.display_name || p.profile_id })),
  ];
}
function renderCopySourceSelect(wrapperId, inputId, value) {
  const options = copySourceChoices();
  const current = options.find(item => item.value === value) || options[0];
  return `<div class="custom-select" id="${wrapperId}"><input type="hidden" id="${inputId}" value="${esc(current.value)}"><button type="button" class="custom-select-trigger" onclick="toggleCustomSelect('${wrapperId}', event)"><span class="custom-select-current">${esc(current.label)}</span></button><div class="custom-select-menu">${options.map(item => `<button type="button" class="custom-select-option ${item.value === current.value ? 'active' : ''}" data-value="${esc(item.value)}" data-label="${esc(item.label)}" onclick="selectCustomOption('${wrapperId}', event)">${esc(item.label)}</button>`).join('')}</div></div>`;
}
function closeAllCustomSelects() {
  $$('.custom-select.open').forEach(el => el.classList.remove('open'));
}
function toggleCustomSelect(wrapperId, event) {
  event?.stopPropagation();
  const root = document.getElementById(wrapperId);
  if (!root) return;
  const willOpen = !root.classList.contains('open');
  closeAllCustomSelects();
  if (willOpen) root.classList.add('open');
}
function selectCustomOption(wrapperId, event) {
  event?.stopPropagation();
  const root = document.getElementById(wrapperId);
  const btn = event?.currentTarget;
  if (!root || !btn) return;
  const input = root.querySelector('input[type="hidden"]');
  const current = root.querySelector('.custom-select-current');
  const value = btn.dataset.value || '';
  const label = btn.dataset.label || btn.textContent.trim();
  if (input) input.value = value;
  if (current) current.textContent = label;
  root.querySelectorAll('.custom-select-option').forEach(el => el.classList.toggle('active', el === btn));
  root.classList.remove('open');
}
function openCreateProfileDialog() {
  const selectedCopyFrom = state.currentProfile || state.profiles[0]?.profile_id || '__builtin_default__';
  openDialog('新建方案', `
    <div>
      <div>
        <div class="field"><label>方案名称</label><input class="input" id="newProfileName"></div>
        <div class="field-grid" style="margin-top:12px;grid-template-columns:minmax(0,1fr) 160px;align-items:end;">
          <div class="field"><label>复制来源</label>${renderCopySourceSelect('copyFromSelect', 'copyFrom', selectedCopyFrom)}</div>
          <div class="field"><label>快捷创建</label><button class="btn" onclick="createBuiltinDefaultProfile()">[ 新建默认配置 ]</button></div>
        </div>
        <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="createProfileConfirm()">[ 确认创建 ]</button></div>
      </div>
    </div>`, 'create');
}

async function createProfileConfirm() {
  const name = $('#newProfileName')?.value?.trim();
  const copy_from = $('#copyFrom')?.value || 'default';
  if (!name) return showToast('方案名称不能为空。', true);
  const res = await apiPost('/api/profiles', { name, copy_from });
  if (res.ok) {
    closeDialog();
    await loadProfiles();
    renderAll();
    showToast('新方案已创建。');
  } else {
    showToast(res.error || '创建失败。', true);
  }
}
async function createBuiltinDefaultProfile() {
  const name = $('#newProfileName')?.value?.trim();
  if (!name) return showToast('请先填写方案名称。', true);
  const res = await apiPost('/api/profiles', { name, copy_from: '__builtin_default__' });
  if (res.ok) {
    closeDialog();
    await loadProfiles();
    renderAll();
    showToast('默认模板方案已创建。');
  } else {
    showToast(res.error || '创建失败。', true);
  }
}

function setAccessMode(mode) {
  state.groupAccess.mode = mode;
  renderOverview();
  updateTop();
}

async function saveGroupAccess(show = true) {
  state.groupAccess.blacklist = state.groupAccess.mode === 'blacklist'
    ? ($('#blacklistInput')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean)
    : [];
  state.groupAccess.whitelist = state.groupAccess.mode === 'whitelist'
    ? ($('#whitelistInput')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean)
    : [];
  const res = await apiPost('/api/group_access', { config: state.groupAccess });
  if (res.ok) {
    if (show) showToast('访问控制已保存。');
  } else if (show) {
    showToast(res.error || '保存失败。', true);
  }
  return res;
}

function toggleRuntime(path) {
  const next = !getDeep(state.runtimeConfig, path);
  setDeep(state.runtimeConfig, path, next);
  renderRuntime();
}
function setRuntimeValue(path, value) {
  const finalVal = value === '' ? '' : (isNaN(value) ? value : Number(value));
  setDeep(state.runtimeConfig, path, finalVal);
  if (path.includes('custom_rarity_weights')) updateRarityChart();
}
async function saveRuntime(show = true) {
  const res = await apiPost('/api/runtime_config', { config: state.runtimeConfig });
  if (res.ok) {
    if (show) showToast('运行配置已保存。');
  } else if (show) {
    showToast(res.error || '保存失败。', true);
  }
  return res;
}

function toggleEventSelect(kind, idx, checked) {
  const target = kind === 'good' ? state.goodSelected : state.badSelected;
  if (checked && !target.includes(idx)) target.push(idx);
  if (!checked) {
    const pos = target.indexOf(idx);
    if (pos >= 0) target.splice(pos, 1);
  }
}
function removeEvent(kind, idx) {
  const arr = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
  arr.splice(idx, 1);
  if (kind === 'good') state.goodSelected = [];
  else state.badSelected = [];
  renderSignin();
}
function deleteSelectedEvents(kind) {
  const arr = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
  const selected = new Set(kind === 'good' ? state.goodSelected : state.badSelected);
  if (!selected.size) return showToast('请先勾选要删除的条目。', true);
  const remain = arr.filter((_, i) => !selected.has(i));
  if (kind === 'good') {
    state.signInTexts.good_things = remain;
    state.goodSelected = [];
  } else {
    state.signInTexts.bad_things = remain;
    state.badSelected = [];
  }
  renderSignin();
}
function addSingleEvent(kind) {
  const target = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
  target.push('');
  const focusIndex = target.length - 1;
  renderSignin();
  setTimeout(() => document.getElementById(`eventInput-${kind}-${focusIndex}`)?.focus(), 0);
}
function addRange() {
  state.signInTexts.luck_ranges.push({ label: '新区间', min: 1, max: 100, gold_delta: 0, comments: [] });
  renderSignin();
}
function removeRange(i) {
  state.signInTexts.luck_ranges.splice(i, 1);
  renderSignin();
}
function setRange(i, key, value) { state.signInTexts.luck_ranges[i][key] = value; }
function setRangeComments(i, value) { state.signInTexts.luck_ranges[i].comments = value.split(/\r?\n/).map(v => v.trim()).filter(Boolean); }
function previewSignin() {
  const ranges = state.signInTexts.luck_ranges || [];
  if (!ranges.length) return showToast('请先配置运势区间。', true);
  const range = ranges[Math.floor(Math.random() * ranges.length)];
  const comment = (range.comments || [])[Math.floor(Math.random() * (range.comments?.length || 1))] || '今日无额外批注。';
  const good = (state.signInTexts.good_things || [])[Math.floor(Math.random() * Math.max(1, state.signInTexts.good_things.length))] || '暂无宜项';
  const bad = (state.signInTexts.bad_things || [])[Math.floor(Math.random() * Math.max(1, state.signInTexts.bad_things.length))] || '暂无忌项';
  const score = Math.floor(Math.random() * Math.max(1, (range.max ?? 100) - (range.min ?? 1) + 1)) + (range.min ?? 1);
  $('#signinPreview').textContent = [
    `今日运势｜${range.label || '未知'}`,
    `数值｜${score}`,
    `金币修正｜${range.gold_delta || 0}`,
    `点评｜${comment}`,
    `宜｜${good}`,
    `忌｜${bad}`,
  ].join('\n');
}
async function saveSignin(show = true) {
  const res = await apiPost('/api/sign_in_texts', { texts: state.signInTexts });
  if (res.ok) {
    if (show) showToast('签到配置已保存。');
  } else if (show) {
    showToast(res.error || '保存失败。', true);
  }
  return res;
}

function openFateEditor(index) {
  state.editingFateIndex = index;
  const card = index >= 0 ? JSON.parse(JSON.stringify(state.fateCards[index])) : { text: '', gold: 0, filename: '' };
  openDialog(index >= 0 ? '编辑命运牌' : '新增命运牌', `
    <div class="split">
      <div>
        <div class="field-grid">
          <div class="field"><label>文案</label><input class="input" id="fateText" value="${esc(card.text || '')}"></div>
          <div class="field"><label>金币值</label><input class="input" type="number" id="fateGold" value="${esc(card.gold ?? 0)}"></div>
        </div>
        <div class="field" style="margin-top:12px;"><label>图片文件名</label><input class="input" id="fateFilename" value="${esc(card.filename || '')}"></div>
        <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveFateEditor()">[ 写入命运牌 ]</button></div>
      </div>
      <div>
        <div class="panel-title" style="font-size:14px;margin-bottom:10px;">可用图片</div>
        <div class="asset-grid">${state.fateImages.map(file => `<div class="asset-item"><div class="thumb"><img src="/fate_assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}"></div><div class="helper" style="margin:8px 0;word-break:break-all;">${esc(file)}</div><button class="btn-mini" onclick="pickFile('fateFilename','${esc(file)}')">选用</button></div>`).join('') || '<div class="empty">暂无图片</div>'}</div>
      </div>
    </div>`);
}
function pickFile(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}
async function saveFateEditor() {
  const payload = { text: $('#fateText')?.value?.trim() || '未命名命运牌', gold: Number($('#fateGold')?.value || 0), filename: $('#fateFilename')?.value?.trim() || '' };
  if (state.editingFateIndex >= 0) state.fateCards[state.editingFateIndex] = payload;
  else state.fateCards.push(payload);
  closeDialog();
  renderFate();
  await saveFateCards(false);
}
async function saveFateCards(show = true) {
  const res = await apiPost('/api/fate_cards', { cards: state.fateCards });
  if (res.ok) {
    if (show) showToast('命运牌已保存。');
  } else if (show) {
    showToast(res.error || '保存失败。', true);
  }
  return res;
}
async function deleteFateCard(i) {
  if (!confirm('确认删除该命运牌吗？')) return;
  state.fateCards.splice(i, 1);
  renderFate();
  await saveFateCards(false);
  showToast('命运牌已删除。');
}
async function uploadImages(endpoint, onReload, onRender, successText) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.multiple = true;
  input.onchange = async () => {
    if (!input.files?.length) return;
    const fd = new FormData();
    [...input.files].forEach(file => fd.append('files', file));
    const res = await fetch(`${endpoint}?profile=${encodeURIComponent(state.currentProfile)}`, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.ok) {
      await onReload();
      onRender();
      showToast(successText);
    } else {
      showToast(data.error || '上传失败。', true);
    }
  };
  input.click();
}
async function deleteAsset(apiBase, file, onReload, onRender) {
  if (!confirm(`确认删除图片 ${file} 吗？`)) return;
  const res = await apiDelete(`${apiBase}/${encodeURIComponent(file)}`);
  if (res.ok) {
    await onReload();
    onRender();
    showToast('图片已删除。');
  } else {
    showToast(res.error || '删除失败。', true);
  }
}
async function uploadFateImages() {
  return uploadImages('/api/upload_fate_image', loadFate, renderFate, '命运牌图片批量上传完成。');
}

function normalizeEffectsForCard(card) {
  const tags = card?.tags || [];
  const parsed = tags.map(tagToEffect).filter(Boolean);
  return parsed.length ? parsed : [{ key: card?.type === 'defense' ? 'add_shield' : card?.type === 'heal' ? 'cleanse' : 'steal', params: [] }];
}

function renderEffectRows(type) {
  const list = state.editingFuncEffects || [];
  return list.map((effect, idx) => {
    const options = effectCatalog[type] || [];
    const chosen = options.find(o => o.key === effect.key) || options[0] || { key: '', params: [] };
    const params = chosen.params || [];
    return `
      <div class="effect-row">
        <div class="field"><label>效果类别</label><select class="select" onchange="setEffectKey(${idx}, this.value)">${options.map(o => `<option value="${esc(o.key)}" ${o.key === effect.key ? 'selected' : ''}>${esc(o.name)}</option>`).join('')}</select></div>
        <div class="field"><label>效果摘要</label><div class="tag-preview">${esc(effectLabel(effect))}</div></div>
        <div class="field"><label>参数</label><div class="field-grid ${params.length >= 3 ? 'three' : params.length === 2 ? '' : ''}">${params.map((name, pi) => `<input class="input" placeholder="${esc(name)}" value="${esc(effect.params?.[pi] || '')}" onchange="setEffectParam(${idx}, ${pi}, this.value)">`).join('') || '<div class="helper">此效果无额外参数</div>'}</div></div>
        <div class="field"><label>操作</label><button class="btn-danger" onclick="removeEffectRow(${idx})">[ 删除效果 ]</button></div>
      </div>`;
  }).join('');
}

function effectPreviewHtml() {
  const tags = state.editingFuncEffects.map(effectToTag).filter(Boolean);
  return tags.length ? tags.map(tag => `<span class="badge">${esc(humanizeTag(tag))}</span>`).join('') : '<span class="helper">尚未生成任何效果。</span>';
}

function openFuncEditor(index) {
  state.editingFuncIndex = index;
  const card = index >= 0 ? JSON.parse(JSON.stringify(state.funcCards[index])) : { card_name: '', type: 'attack', rarity: 1, filename: '', description: '', tags: [] };
  state.editingFuncEffects = normalizeEffectsForCard(card);
  const type = card.type || 'attack';
  openDialog(index >= 0 ? '编辑功能牌' : '新增功能牌', funcEditorHtml(card, type));
}

function funcEditorHtml(card, type) {
  return `
    <div class="split">
      <div>
        <div class="field-grid">
          <div class="field"><label>卡牌名称</label><input class="input" id="funcName" value="${esc(card.card_name || '')}"></div>
          <div class="field"><label>稀有度</label><select class="select" id="funcRarity">${Object.entries(rarityLabelMap).map(([v, t]) => `<option value="${v}" ${Number(card.rarity) === Number(v) ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>
        </div>
        <div class="field-grid" style="margin-top:12px;">
          <div class="field"><label>大类</label><select class="select" id="funcType" onchange="changeFuncType(this.value)">${Object.entries(typeLabelMap).map(([v, t]) => `<option value="${v}" ${type === v ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>
          <div class="field"><label>图片文件名</label><input class="input" id="funcFilename" value="${esc(card.filename || '')}"></div>
        </div>
        <div class="field" style="margin-top:12px;"><label>描述</label><textarea class="textarea" id="funcDesc">${esc(card.description || '')}</textarea></div>
        <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">效果引导</div><div class="panel-note">先选大类，再选效果，再填参数。会自动转成标签，但展示给你的都是中文。</div></div><button class="btn" onclick="addEffectRow()">[ 新增效果 ]</button></div>
        <div class="effect-builder" id="effectBuilder">${renderEffectRows(type)}</div>
        <div class="field" style="margin-top:12px;"><label>标签预览</label><div class="tag-preview" id="effectPreview">${effectPreviewHtml()}</div></div>
        <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveFuncEditor()">[ 写入功能牌 ]</button></div>
      </div>
      <div>
        <div class="panel-title" style="font-size:14px;margin-bottom:10px;">图像库</div>
        <div class="asset-grid">${state.images.map(file => `<div class="asset-item"><div class="thumb"><img src="/assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}"></div><div class="helper" style="margin:8px 0;word-break:break-all;">${esc(file)}</div><button class="btn-mini" onclick="pickFile('funcFilename','${esc(file)}')">选用</button></div>`).join('') || '<div class="empty">暂无图片</div>'}</div>
      </div>
    </div>`;
}

function changeFuncType(type) {
  const options = effectCatalog[type] || [];
  state.editingFuncEffects = [{ key: options[0]?.key || '', params: [] }];
  const name = $('#funcName')?.value || '';
  const rarity = $('#funcRarity')?.value || 1;
  const filename = $('#funcFilename')?.value || '';
  const description = $('#funcDesc')?.value || '';
  $('#dialogBody').innerHTML = funcEditorHtml({ card_name: name, rarity: Number(rarity), filename, description }, type);
}
function addEffectRow() {
  const type = $('#funcType')?.value || 'attack';
  const key = effectCatalog[type]?.[0]?.key || '';
  state.editingFuncEffects.push({ key, params: [] });
  $('#effectBuilder').innerHTML = renderEffectRows(type);
  $('#effectPreview').innerHTML = effectPreviewHtml();
}
function removeEffectRow(idx) {
  state.editingFuncEffects.splice(idx, 1);
  const type = $('#funcType')?.value || 'attack';
  if (!state.editingFuncEffects.length) state.editingFuncEffects.push({ key: effectCatalog[type][0].key, params: [] });
  $('#effectBuilder').innerHTML = renderEffectRows(type);
  $('#effectPreview').innerHTML = effectPreviewHtml();
}
function setEffectKey(idx, key) {
  state.editingFuncEffects[idx] = { key, params: [] };
  const type = $('#funcType')?.value || 'attack';
  $('#effectBuilder').innerHTML = renderEffectRows(type);
  $('#effectPreview').innerHTML = effectPreviewHtml();
}
function setEffectParam(idx, pidx, val) {
  state.editingFuncEffects[idx].params ||= [];
  state.editingFuncEffects[idx].params[pidx] = val;
  $('#effectPreview').innerHTML = effectPreviewHtml();
}
async function saveFuncEditor() {
  const payload = {
    card_name: $('#funcName')?.value?.trim() || '未命名功能牌',
    type: $('#funcType')?.value || 'attack',
    rarity: Number($('#funcRarity')?.value || 1),
    filename: $('#funcFilename')?.value?.trim() || '',
    description: $('#funcDesc')?.value?.trim() || '',
    tags: state.editingFuncEffects.map(effectToTag).filter(Boolean)
  };
  if (state.editingFuncIndex >= 0) state.funcCards[state.editingFuncIndex] = payload;
  else state.funcCards.push(payload);
  closeDialog();
  renderCards();
  await saveFuncCards(false);
  await refreshCardAssets(false);
  renderCards();
  showToast('功能牌已写入。');
}
async function saveFuncCards(show = true) {
  const res = await apiPost('/api/func_cards', { cards: state.funcCards });
  if (res.ok) {
    if (show) showToast('功能牌已保存。');
  } else if (show) {
    showToast(res.error || '保存失败。', true);
  }
  return res;
}
async function deleteFuncCard(i) {
  if (!confirm('确认删除该功能牌吗？')) return;
  state.funcCards.splice(i, 1);
  renderCards();
  await saveFuncCards(false);
  await refreshCardAssets(false);
  renderCards();
  showToast('功能牌已删除。');
}
async function batchAddCards() {
  const raw = prompt('每行格式：卡牌名,大类(attack/heal/defense),稀有度');
  if (!raw) return;
  raw.split(/\r?\n/).map(v => v.trim()).filter(Boolean).forEach(line => {
    const [name, type, rarity] = line.split(',').map(s => s?.trim() || '');
    if (!name) return;
    state.funcCards.push({ card_name: name, type: type || 'attack', rarity: Number(rarity || 1), filename: '', description: '', tags: [] });
  });
  renderCards();
  await saveFuncCards(false);
  showToast('批量添加完成。');
}
async function uploadFuncImages() {
  return uploadImages('/api/upload_image', loadCards, renderCards, '功能牌图片批量上传完成。');
}
async function deleteFuncImage(file) {
  return deleteAsset('/api/images', file, loadCards, renderCards);
}
async function deleteFateImage(file) {
  return deleteAsset('/api/fate_images', file, loadFate, renderFate);
}
async function refreshCardAssets(show = true) {
  await loadCards();
  if (show) showToast('资源扫描完成。');
}

async function saveAllData() {
  const btn = $('#saveAllBtn');
  if (btn) {
    btn.disabled = true;
    btn.classList.add('busy');
  }
  try {
    const results = await Promise.all([
      saveRuntime(false),
      saveGroupAccess(false),
      saveSignin(false),
      saveFateCards(false),
      saveFuncCards(false),
    ]);
    const failed = results.find(res => !res?.ok);
    if (failed) {
      showToast(failed.error || '部分内容保存失败。', true);
      return;
    }
    showToast('当前方案已全部保存。');
  } catch (e) {
    console.error(e);
    showToast('全局保存失败，请检查接口。', true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove('busy');
    }
  }
}

// ===== [ boot / event binding ] ============================================
function bindEvents() {
  $$('.nav-btn').forEach(btn => btn.addEventListener('click', () => setPage(btn.dataset.page)));
  $('#reloadBtn').addEventListener('click', () => loadAll(true));
  $('#saveAllBtn')?.addEventListener('click', saveAllData);
  $('#closeDialogBtn').addEventListener('click', closeDialog);
  $('#dialog').addEventListener('click', (e) => { if (e.target.id === 'dialog') closeDialog(); });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-select')) closeAllCustomSelects();
  });
}

Object.assign(window, {
  useProfile,
  bindGroupPrompt,
  unbindGroup,
  openCreateProfileDialog,
  createProfileConfirm,
  createBuiltinDefaultProfile,
  setAccessMode,
  saveGroupAccess,
  toggleRuntime,
  setRuntimeValue,
  saveRuntime,
  toggleEventSelect,
  removeEvent,
  deleteSelectedEvents,
  addSingleEvent,
  addRange,
  removeRange,
  setRange,
  setRangeComments,
  previewSignin,
  saveSignin,
  openFateEditor,
  saveFateEditor,
  saveFateCards,
  deleteFateCard,
  uploadFateImages,
  pickFile,
  openFuncEditor,
  changeFuncType,
  addEffectRow,
  removeEffectRow,
  setEffectKey,
  setEffectParam,
  saveFuncEditor,
  saveFuncCards,
  deleteFuncCard,
  batchAddCards,
  uploadFuncImages,
  deleteFuncImage,
  deleteFateImage,
  refreshCardAssets,
  toggleCustomSelect,
  selectCustomOption,
  openBatchEventDialog,
  confirmBatchEventAdd,
  setEventText,
  openFateEditorFromImage,
  openFuncEditorFromImage,
  duplicateFateCard,
  duplicateFuncCard,
  detectIncompleteFateCards,
  setFuncFilter,
  editProfile,
  saveProfileEdit,
  deleteProfileConfirm,
});

async function bootstrapWebUi() {
  if (bootstrapWebUi.started) return;
  bootstrapWebUi.started = true;
  bindEvents();
  await loadAll();
}

window.__startWebUi = bootstrapWebUi;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrapWebUi, { once: true });
} else {
  bootstrapWebUi();
}