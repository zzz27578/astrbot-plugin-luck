/*
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
    const esc = (v) => String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

    const pageMeta = {
      overview: ['鎬昏涓庢柟妗?, '鎶婃柟妗堛€佽闂帶鍒朵笌鏍稿績淇℃伅鏀惧湪鍚屼竴灞忓唴锛屽垏鎹㈤『鎵嬶紝鐘舵€佹竻鏅般€?],
      runtime: ['杩愯閰嶇疆', '淇濈暀瀹屾暣鍔熻兘锛屼絾璁╅珮棰戝弬鏁拌皟鏁存洿杞绘澗銆佹洿鐩磋銆?],
      signin: ['绛惧埌閰嶇疆', '浜嬩欢姹犮€佽繍鍔垮尯闂翠笌棰勮闆嗕腑鎺掑竷锛屾柟渚胯竟鏀硅竟鐪嬨€?],
      fate: ['鍛借繍鐗屾。妗?, '鍛借繍鐗屻€佽祫婧愬浘鐗囦笌缂栬緫鍣ㄦ斁鍦ㄤ竴璧凤紝鍑忓皯鏉ュ洖璺宠浆銆?],
      cards: ['鍔熻兘鐗屾。妗?, '绔栫増鍗＄墖灞曠ず锛屾寜绫诲瀷蹇€熸煡鐪嬪苟缂栬緫鍔熻兘鐗屻€?],
      stats: ['鏁版嵁缁熻', '鎸夋柟妗堟煡鐪嬬兢缁勩€佺敤鎴蜂笌鎸佺墝鎺掕銆?],
    };

    const rarityLabelMap = {1:'鏅€?,2:'绋€鏈?,3:'鍙茶瘲',4:'浼犺',5:'绁炶瘽'};
    const typeLabelMap = {attack:'鏀诲嚮',heal:'杈呭姪',defense:'闃插尽'};
    const effectCatalog = {
      attack: [
        { key:'steal', name:'鍋峰彇閲戝竵', params:['鏁板€?] },
        { key:'freeze', name:'鍐荤粨', params:['灏忔椂'] },
        { key:'silence', name:'娌夐粯', params:['灏忔椂'] },
        { key:'seal_draw_all', name:'灏侀攣鎶界墝', params:['灏忔椂'] },
        { key:'luck_drain', name:'鎶藉彇鐖嗙巼', params:['灏忔椂','鐧惧垎姣?] },
        { key:'steal_fate', name:'鍋峰彇鍛借繍鏀剁泭', params:[] },
        { key:'borrow_blade', name:'鍊熷垁浼ゅ', params:['鏈€灏忓€?,'鏈€澶у€?] },
        { key:'bounty_mark', name:'鎮祻鍗拌', params:['灏忔椂','杩藉姞閲戝竵'] },
        { key:'strip_buff_gain', name:'澶哄彇澧炵泭骞跺姞鐖嗙巼', params:['鐧惧垎姣?,'灏忔椂'] },
        { key:'aoe_damage', name:'缇や綋鏀诲嚮', params:['鏈€灏忓€?,'鏈€澶у€?,'浜烘暟'] },
        { key:'dice_rule', name:'楠板瓙瑙勫垯', params:['瑙勫垯閿?] },
        { key:'dice_duel', name:'瀵硅祵', params:['搴曟敞'] }
      ],
      heal: [
        { key:'cleanse', name:'鍑€鍖?, params:[] },
        { key:'aoe_heal', name:'缇や綋鍥炲', params:['鏈€灏忓€?,'鏈€澶у€?,'浜烘暟'] },
        { key:'luck_bless', name:'濂借繍鍔犳姢', params:['灏忔椂','鐧惧垎姣?] },
        { key:'fate_roulette', name:'鍛借繍杞洏', params:[] },
        { key:'dice_reroll_lowest_once', name:'鏈€浣庣偣閲嶆姇涓€娆?, params:[] }
      ],
      defense: [
        { key:'add_shield', name:'鎶ょ浘', params:[] },
        { key:'thorn_armor', name:'鍙嶇敳', params:['灏忔椂','鍙嶄激姣斾緥'] },
        { key:'cleanse', name:'鍑€鍖?, params:[] }
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
      if (key === 'steal') return { key, params:[rest[0] || ''] };
      if (key === 'freeze') return { key, params:[rest[0] || ''] };
      if (key === 'silence') return { key, params:[rest[0] || ''] };
      if (key === 'seal_draw_all') return { key, params:[rest[0] || ''] };
      if (key === 'luck_drain') return { key, params:[rest[0] || '', rest[1] || ''] };
      if (key === 'steal_fate') return { key, params:[] };
      if (key === 'borrow_blade') return { key, params:[rest[0] || '', rest[1] || ''] };
      if (key === 'bounty_mark') return { key, params:[rest[0] || '', rest[1] || ''] };
      if (key === 'strip_buff_gain') return { key, params:[rest[0] || '', rest[1] || ''] };
      if (key === 'aoe_damage') return { key, params:[rest[0] || '', rest[1] || '', rest[2] || ''] };
      if (key === 'dice_rule') return { key, params:[rest.join(':') || 'all_in_raid_v1'] };
      if (key === 'dice_duel') return { key, params:[rest[0] || '20'] };
      if (key === 'cleanse') return { key, params:[] };
      if (key === 'aoe_heal') return { key, params:[rest[0] || '', rest[1] || '', rest[2] || ''] };
      if (key === 'luck_bless') return { key, params:[rest[0] || '', rest[1] || ''] };
      if (key === 'fate_roulette') return { key, params:[] };
      if (key === 'dice_reroll_lowest_once') return { key, params:[] };
      if (key === 'add_shield') return { key, params:[] };
      if (key === 'thorn_armor') return { key, params:[rest[0] || '', rest[1] || ''] };
      return { key: 'raw', raw };
    }

    function effectLabel(effect) {
      if (!effect) return '鏈瘑鍒晥鏋?;
      if (effect.key === 'raw') return `鍘熷鏍囩锛?{effect.raw}`;
      const dict = [...effectCatalog.attack, ...effectCatalog.heal, ...effectCatalog.defense].find(x => x.key === effect.key);
      return dict?.name || effect.key;
    }

    function humanizeTag(tag) {
      const effect = tagToEffect(tag);
      if (!effect) return '鏈瀹?;
      const p = effect.params || [];
      switch (effect.key) {
        case 'steal': return `鍋峰彇鐩爣 ${p[0]} 閲戝竵`;
        case 'freeze': return `鍐荤粨 ${p[0]} 灏忔椂`;
        case 'silence': return `娌夐粯 ${p[0]} 灏忔椂`;
        case 'seal_draw_all': return `灏侀攣鎶界墝 ${p[0]} 灏忔椂`;
        case 'luck_drain': return `鎶藉彇 ${p[1]}% 鐖嗙巼锛屾寔缁?${p[0]} 灏忔椂`;
        case 'steal_fate': return '鍋峰彇鍛借繍鏀剁泭';
        case 'borrow_blade': return `鍊熷垁閫犳垚 ${p[0]}-${p[1]} 浼ゅ`;
        case 'bounty_mark': return `鎮祻 ${p[0]} 灏忔椂锛屾瘡娆¤拷鍔?${p[1]} 閲戝竵`;
        case 'strip_buff_gain': return `澶哄彇澧炵泭骞惰幏寰?${p[0]}% 鐖嗙巼 ${p[1]} 灏忔椂`;
        case 'aoe_damage': return `缇ゆ敾 ${p[0]}-${p[1]}锛屾渶澶?${p[2]} 浜篳;
        case 'dice_rule': return `楠板瓙瑙勫垯 ${p[0]}`;
        case 'dice_duel': return `瀵硅祵搴曟敞 ${p[0]}`;
        case 'cleanse': return '鍑€鍖栬礋闈㈢姸鎬?;
        case 'aoe_heal': return `缇や綋鍥炲 ${p[0]}-${p[1]}锛屾渶澶?${p[2]} 浜篳;
        case 'luck_bless': return `${p[0]} 灏忔椂鍐呯垎鐜?+${p[1]}%`;
        case 'fate_roulette': return '鍛借繍杞洏';
        case 'dice_reroll_lowest_once': return '鏈€浣庣偣鑷姩閲嶆姇涓€娆?;
        case 'add_shield': return '鎸傝浇鎶ょ浘';
        case 'thorn_armor': return `鍙嶇敳 ${p[0]} 灏忔椂锛屽弽浼?${p[1]}%`;
        case 'raw': return `鍘熷鏍囩锛?{effect.raw}`;
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
    const apiPost = (path, body) => requestJson(path, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    const apiDelete = (path) => requestJson(path, { method:'DELETE' });
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
      c.webui_settings ||= { enable:true, port:4399 };
      c.fate_cards_settings ||= { enable:true, daily_draw_limit:3 };
      c.func_cards_settings ||= {
        enable:true,
        enable_dice_cards:true,
        enable_public_duel_mode:false,
        public_duel_daily_limit:3,
        public_duel_min_stake:10,
        public_duel_max_stake:200,
        enable_rarity_dedup:true,
        rarity_mode:'default',
        custom_rarity_weights:{ rarity_1:30, rarity_2:30, rarity_3:28, rarity_4:11, rarity_5:1 },
        economy_settings:{ draw_probability:5, free_daily_draw:1, draw_cost:20, pity_threshold:10 }
      };
      c.func_cards_settings.custom_rarity_weights ||= { rarity_1:30, rarity_2:30, rarity_3:28, rarity_4:11, rarity_5:1 };
      c.func_cards_settings.economy_settings ||= { draw_probability:5, free_daily_draw:1, draw_cost:20, pity_threshold:10 };
      state.runtimeConfig = c;
    }

    function setDeep(obj, path, value) {
      const keys = path.split('.');
      let t = obj;
      for (let i = 0; i < keys.length - 1; i++) { t[keys[i]] ||= {}; t = t[keys[i]]; }
      t[keys[keys.length - 1]] = value;
    }
    function getDeep(obj, path) { return path.split('.').reduce((a, k) => a?.[k], obj); }

    async function loadProfiles() {
      const res = await apiGet('/api/profile_overview');
      if (res.ok) state.profiles = res.profiles || [];
      if (!state.profiles.some(p => p.profile_id === state.currentProfile) && state.profiles[0]) state.currentProfile = state.profiles[0].profile_id;
    }
    async function loadRuntime() { const res = await apiGet('/api/runtime_config'); if (res.ok) state.runtimeConfig = res.config || {}; ensureRuntime(); }
    async function loadGroupAccess() { const res = await apiGet('/api/group_access'); if (res.ok) state.groupAccess = res.config || { mode:'off', blacklist:[], whitelist:[] }; }
    async function loadSignin() {
      const res = await apiGet('/api/sign_in_texts');
      if (res.ok) state.signInTexts = res.texts || {};
      state.signInTexts.good_things ||= [];
      state.signInTexts.bad_things ||= [];
      state.signInTexts.luck_ranges ||= [];
    }
    async function loadFate() {
      const [a,b] = await Promise.all([apiGet('/api/fate_cards'), apiGet('/api/fate_images')]);
      if (a.ok) state.fateCards = a.cards || [];
      if (b.ok) state.fateImages = b.images || [];
    }
    async function loadCards() {
      const [a, b] = await Promise.all([apiGet('/api/func_cards'), apiGet('/api/images')]);
      if (a.ok) state.funcCards = a.cards || [];
      if (b.ok) state.images = b.files || [];
    }
    async function loadStats() { const res = await apiGet('/api/user_stats'); if (res.ok) state.stats = res.stats || { total_groups:0, total_users:0, card_holders:{}, groups:[] }; }
    async function refreshActiveProfileData() {
      await Promise.all([loadRuntime(), loadGroupAccess(), loadSignin(), loadFate(), loadCards(), loadStats()]);
    }
    async function refreshProfilesAndStats() {
      await Promise.all([loadProfiles(), loadStats()]);
    }

    async function loadAll(showMessage = false) {
      try {
        await loadProfiles();
        await refreshActiveProfileData();
        renderAll();
        if (showMessage) showToast('杞藉叆鎴愬姛');
      } catch (e) {
        console.error(e);
        showToast('杞藉叆澶辫触锛岃妫€鏌ュ悗绔帴鍙ｃ€?, true);
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
      { key:'rarity_1', label:'鏅€?, color:'#6f7d8e' },
      { key:'rarity_2', label:'绋€鏈?, color:'#58a7ff' },
      { key:'rarity_3', label:'鍙茶瘲', color:'#9f6cff' },
      { key:'rarity_4', label:'浼犺', color:'#ffbf5f' },
      { key:'rarity_5', label:'绁炶瘽', color:'#ff7078' },
    ];
    const funcTypePalette = {
      attack: { label:'鏀诲嚮', color:'#ff8d78' },
      heal: { label:'杈呭姪', color:'#69dec1' },
      defense: { label:'闃插尽', color:'#6f96ff' },
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
      if (state.activePage !== 'cards') {
        el.innerHTML = '';
        hero.classList.remove('with-aux');
        return;
      }
      hero.classList.add('with-aux');
      const preview = buildFuncTypeDistribution();
      el.innerHTML = `
        <div class="hero-pie">
          <div class="hero-pie-chart" style="background:${preview.ringBackground};"></div>
          <div class="hero-pie-meta">
            <b>${preview.total}</b>
            <span>鍔熻兘绫诲瀷鍒嗗竷</span>
            <div class="hero-pie-legend">
              ${preview.items.map(item => `
                <div class="hero-pie-item">
                  <span class="hero-pie-dot" style="--dot-color:${item.color}"></span>
                  <span>${item.label}</span>
                  <span>${item.count}</span>
                </div>`).join('')}
            </div>
          </div>
        </div>`;
    }
    function openBatchEventDialog(kind) {
      const label = kind === 'good' ? '瀹滈」' : '蹇岄」';
      openDialog(`鎵归噺澧炲姞${label}`, `
        <div>
          <div class="field"><label>${label}鏂囨锛堟瘡琛屼竴鏉★級</label><textarea class="textarea" id="batchEventInput" style="min-height:220px;"></textarea></div>
          <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="confirmBatchEventAdd('${kind}')">[ 鍐欏叆${label} ]</button></div>
        </div>`, 'create');
    }
    function confirmBatchEventAdd(kind) {
      const raw = $('#batchEventInput')?.value || '';
      const list = raw.split(/\r?\n/).map(v => v.trim()).filter(Boolean);
      if (!list.length) return showToast('璇疯嚦灏戣緭鍏ヤ竴鏉℃枃妗堛€?, true);
      const target = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
      target.push(...list);
      closeDialog();
      renderSignin();
      showToast('鎵归噺鏂囨宸插啓鍏ャ€?);
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
      copy.text = `${copy.text || '鏈懡鍚嶅懡杩愮墝'} 鍓湰`;
      state.fateCards.splice(i + 1, 0, copy);
      renderFate();
      await saveFateCards(false);
      showToast('鍛借繍鐗屽凡澶嶅埗銆?);
    }
    async function duplicateFuncCard(i) {
      const original = state.funcCards[i];
      if (!original) return;
      const copy = JSON.parse(JSON.stringify(original));
      copy.card_name = `${copy.card_name || '鏈懡鍚嶅姛鑳界墝'} 鍓湰`;
      state.funcCards.splice(i + 1, 0, copy);
      renderCards();
      await saveFuncCards(false);
      showToast('鍔熻兘鐗屽凡澶嶅埗銆?);
    }
    function isFateCardIncomplete(card) {
      return !(card.text || '').trim() || !card.filename || !state.fateImages.includes(card.filename);
    }
    function ensureFateDraftCards() {
      const boundFiles = new Set(state.fateCards.map(card => card.filename).filter(Boolean));
      state.fateImages.filter(file => !boundFiles.has(file)).forEach(file => {
        state.fateCards.push({ text:'', gold:0, filename:file });
      });
    }
    function detectIncompleteFateCards() {
      ensureFateDraftCards();
      state.fateCards.sort((a, b) => Number(isFateCardIncomplete(b)) - Number(isFateCardIncomplete(a)));
      renderFate();
      const pendingCount = state.fateCards.filter(isFateCardIncomplete).length;
      showToast(pendingCount ? `宸茬疆椤?${pendingCount} 寮犳湭瀹屾垚鍛借繍鐗屻€俙 : '褰撳墠娌℃湁鏈畬鎴愮殑鍛借繍鐗屻€?);
    }
    function isFuncCardIncomplete(card) {
      return !(card.card_name || '').trim() || !card.filename || !state.images.includes(card.filename) || !(card.description || '').trim() || !(card.tags || []).length;
    }
    function setFuncFilter(value) {
      state.funcFilter = value || 'all';
      renderCards();
    }
    function renderOverview() {
      const page = $('#page-overview');
      page.innerHTML = `
        <div class="grid">
          <section class="panel col-8">
            <div class="panel-head">
              <div>
                <div class="panel-title">鏂规绠＄悊</div>
                <div class="panel-note">鐩存帴鏀惧湪涓荤晫闈€傚垏鎹€侀噸鍛藉悕銆佺粦瀹氱兢鍙烽兘鍦ㄨ繖閲屽畬鎴愩€?/div>
              </div>
              <button class="btn-strong" onclick="openCreateProfileDialog()">[ 鏂板缓鏂规 ]</button>
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
                      ${p.is_default ? '<span class="badge light">榛樿鏂规</span>' : ''}
                      <span class="badge">缁戝畾缇ょ粍 ${(p.group_count || 0)}</span>
                    </div>
                    <div class="meta">鐢ㄦ埛 ${p.user_count || 0} 锝?鍔熻兘鐗?${p.func_card_count || 0} 锝?鍛借繍鐗?${p.fate_card_count || 0}</div>
                    <div class="row" style="margin:4px 0;">
                      ${(p.groups || []).slice(0,3).map(g => `<span class="badge">缇?${esc(g)}</span>`).join('') || '<span class="helper">鏆傛棤缁戝畾缇ょ粍</span>'}
                    </div>
                    <div class="row">
                      <button class="btn" onclick="editProfile('${esc(p.profile_id)}')">[ 缂栬緫 ]</button>
                      <button class="btn" onclick="bindGroupPrompt('${esc(p.profile_id)}')">[ 缁戝畾缇ゅ彿 ]</button>
                    </div>
                    ${(p.groups || []).slice(0,3).length ? `<div class="row" style="margin-top:4px;">${(p.groups || []).slice(0,3).map(g => `<button class="btn-mini" onclick="unbindGroup('${esc(p.profile_id)}','${esc(g)}')">瑙ｇ粦 ${esc(g)}</button>`).join('')}</div>` : ''}
                  </div>
                  <div class="profile-switch-slot">
                    <button class="profile-switch-btn" ${active ? 'disabled' : `onclick="useProfile('${esc(p.profile_id)}')"`}>
                      ${active ? '浣跨敤涓? : '鍒囨崲'}
                    </button>
                  </div>
                </article>`;
              }).join('')}
            </div>
          </section>

          <section class="panel col-4">
            <div class="panel-head">
              <div>
                <div class="panel-title">璁块棶鎺у埗</div>
                <div class="panel-note">榛戝悕鍗曚笌鐧藉悕鍗曚簰鏂ワ紝鍙兘鏈変竴绉嶆ā寮忓浜庡惎鐢ㄧ姸鎬併€?/div>
              </div>
            </div>
            <div class="switch-group" style="margin-bottom:12px;">
              <button class="mode-btn ${state.groupAccess.mode === 'off' ? 'active' : ''}" onclick="setAccessMode('off')">鍏抽棴闄愬埗</button>
              <button class="mode-btn black ${state.groupAccess.mode === 'blacklist' ? 'active' : ''}" onclick="setAccessMode('blacklist')">榛戝悕鍗曟ā寮?/button>
              <button class="mode-btn white ${state.groupAccess.mode === 'whitelist' ? 'active' : ''}" onclick="setAccessMode('whitelist')">鐧藉悕鍗曟ā寮?/button>
            </div>
            ${state.groupAccess.mode === 'blacklist' ? `
            <div class="field" style="margin-bottom:10px;">
              <label>榛戝悕鍗曠兢鍙凤紙姣忚涓€涓級</label>
              <textarea class="textarea" id="blacklistInput">${esc((state.groupAccess.blacklist || []).join('\n'))}</textarea>
            </div>` : ''}
            ${state.groupAccess.mode === 'whitelist' ? `
            <div class="field">
              <label>鐧藉悕鍗曠兢鍙凤紙姣忚涓€涓級</label>
              <textarea class="textarea" id="whitelistInput">${esc((state.groupAccess.whitelist || []).join('\n'))}</textarea>
            </div>` : ''}
            <div class="row" style="margin-top:10px;">
              <button class="btn-strong" onclick="saveGroupAccess()">[ 淇濆瓨璁块棶鎺у埗 ]</button>
            </div>
            <div class="overview-stats">
              <div class="overview-stat"><b id="quickProfileCount">${state.profiles.length || 0}</b><span>鏂规鏁伴噺</span></div>
              <div class="overview-stat"><b id="quickGroupCount">${state.stats.total_groups || 0}</b><span>缇ょ粍鎬婚噺</span></div>
              <div class="overview-stat"><b id="quickUserCount">${state.stats.total_users || 0}</b><span>鐢ㄦ埛鎬婚噺</span></div>
            </div>
          </section>
        </div>`;
    }

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
            <div class="panel-head"><div><div class="panel-title">妯″潡寮€鍏?/div><div class="panel-note">寮€鍏虫墦寮€鍚庯紝鍙充晶瀵瑰簲鍙傛暟鎵嶄細杩涘叆鍙皟鐘舵€併€?/div></div></div>
            ${toggleBox('鍛借繍鐗岀郴缁?, '寮€鍚悗鎵嶄細鍚敤鍛借繍鐗岀浉鍏虫娊鍙栦笌姣忔棩涓婇檺閰嶇疆銆?, 'fate_cards_settings.enable', c.fate_cards_settings.enable)}
            ${toggleBox('鍔熻兘鐗岀郴缁?, '鍏抽棴鏃讹紝鍔熻兘鐗岀殑缁忔祹銆佺█鏈夊害鍜屽璧岀浉鍏抽厤缃兘浼氶攣瀹氥€?, 'func_cards_settings.enable', f.enable)}
            ${toggleBox('楠板瓙鐗岀郴缁?, '鎺у埗楠板瓙鍔熻兘鐗屼笌鐩稿叧瑙勫垯鍏ュ彛鏄惁寮€鏀俱€?, 'func_cards_settings.enable_dice_cards', f.enable_dice_cards)}
            ${toggleBox('鍏紑瀵硅祵妯″紡', '寮€鍚悗锛屾墠鍏佽閰嶇疆姣忔棩娆℃暟涓庤祵娉ㄨ寖鍥淬€?, 'func_cards_settings.enable_public_duel_mode', f.enable_public_duel_mode)}
            ${toggleBox('鍚岀█鏈夊害浼樺厛涓嶉噸澶?, '寮€鍚悗锛屾娊鍒板姛鑳界墝鏃朵細灏介噺閬垮厤杩炵画缁欏嚭鍚岀█鏈夊害閲嶅鍐呭銆?, 'func_cards_settings.enable_rarity_dedup', f.enable_rarity_dedup)}
          </section>

          <section class="panel col-8">
            <div class="panel-head">
              <div>
                <div class="panel-title">鍙傛暟閰嶇疆</div>
                <div class="panel-note">绋€鏈夊害鍚嶇О宸叉敼涓猴細鏅€?/ 绋€鏈?/ 鍙茶瘲 / 浼犺 / 绁炶瘽銆?/div>
              </div>
              <button class="btn-strong" onclick="saveRuntime()">[ 淇濆瓨杩愯閰嶇疆 ]</button>
            </div>

            <div class="runtime-split">
              <div class="config-block ${fateEnabled ? '' : 'locked'}">
                ${numField('鍛借繍鐗屾瘡鏃ヤ笂闄?,'fate_cards_settings.daily_draw_limit',c.fate_cards_settings.daily_draw_limit,!fateEnabled)}
              </div>
              <div class="config-block ${funcEnabled ? '' : 'locked'}">
                ${selectField('绋€鏈夊害妯″紡','func_cards_settings.rarity_mode',f.rarity_mode,[['default','榛樿'],['custom','鑷畾涔?]],!funcEnabled)}
              </div>
            </div>

            <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">鍏紑瀵硅祵閰嶇疆</div><div class="panel-note">鎶婂璧屾鏁颁笌璧屾敞鑼冨洿鏀惧埌鍚屼竴琛岋紝鏂逛究鏁翠綋璋冩暣銆?/div></div></div>
            <div class="runtime-three config-block ${duelEnabled ? '' : 'locked'}">
              ${numField('瀵硅祵姣忔棩娆℃暟','func_cards_settings.public_duel_daily_limit',f.public_duel_daily_limit,!duelEnabled)}
              ${numField('鏈€灏忚祵娉?,'func_cards_settings.public_duel_min_stake',f.public_duel_min_stake,!duelEnabled)}
              ${numField('鏈€澶ц祵娉?,'func_cards_settings.public_duel_max_stake',f.public_duel_max_stake,!duelEnabled)}
            </div>

            <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">鎶藉崱缁忔祹</div><div class="panel-note">涓婃帓鎺у埗鎺夌巼涓庡厤璐规鏁帮紝涓嬫帓鎺у埗鍗曟娑堣€椾笌淇濆簳銆?/div></div></div>
            <div class="runtime-split config-block ${funcEnabled ? '' : 'locked'}">
              ${numField('鍩虹鎺夌巼','func_cards_settings.economy_settings.draw_probability',e.draw_probability,!funcEnabled)}
              ${numField('姣忔棩鍏嶈垂鎶藉彇','func_cards_settings.economy_settings.free_daily_draw',e.free_daily_draw,!funcEnabled)}
              ${numField('瓒呭嚭鍏嶈垂鍚庣殑鍗曟娑堣€?,'func_cards_settings.economy_settings.draw_cost',e.draw_cost,!funcEnabled)}
              ${numField('淇濆簳娆℃暟','func_cards_settings.economy_settings.pity_threshold',e.pity_threshold,!funcEnabled)}
            </div>

            <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">绋€鏈夊害鏉冮噸</div><div class="panel-note">宸︿晶閫愰」杈撳叆锛屽彸渚у疄鏃堕瑙堝悇绋€鏈夊害鍗犳瘮銆?/div></div></div>
            <div class="rarity-weight-layout config-block ${weightEnabled ? '' : 'locked'}">
              <div class="rarity-weight-fields">
                ${numField('鏅€?,'func_cards_settings.custom_rarity_weights.rarity_1',w.rarity_1,!weightEnabled)}
                ${numField('绋€鏈?,'func_cards_settings.custom_rarity_weights.rarity_2',w.rarity_2,!weightEnabled)}
                ${numField('鍙茶瘲','func_cards_settings.custom_rarity_weights.rarity_3',w.rarity_3,!weightEnabled)}
                ${numField('浼犺','func_cards_settings.custom_rarity_weights.rarity_4',w.rarity_4,!weightEnabled)}
                ${numField('绁炶瘽','func_cards_settings.custom_rarity_weights.rarity_5',w.rarity_5,!weightEnabled)}
              </div>
              <div class="rarity-ring-wrap">
                <div class="rarity-ring" id="rarityRing" style="background:${preview.ringBackground};">
                  <div class="rarity-ring-center"><div><b id="rarityWeightTotal">${preview.total}</b><span>鏉冮噸鎬诲€?/span></div></div>
                </div>
                <div class="rarity-legend-title">瀹炴椂姒傜巼鍒嗗竷</div>
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
      return `<div class="field"><label>${label}</label><select class="select" ${disabled ? 'disabled' : ''} onchange="setRuntimeValue('${path}', this.value)">${options.map(([v,t]) => `<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(t)}</option>`).join('')}</select></div>`;
    }

    function renderSignin() {
      const ranges = state.signInTexts.luck_ranges || [];
      $('#page-signin').innerHTML = `
        <div class="grid signin-layout">
          <section class="panel col-7">
            <div class="panel-head">
              <div>
                <div class="panel-title">浜嬩欢鏂囨湰姹?/div>
                <div class="panel-note">绛惧埌棰勮浼氭寜鈥滃疁 / 蹇屸€濇牸寮忕敓鎴愶紝杩欓噷鐩存帴缁存姢瀵瑰簲鏂囨銆?/div>
              </div>
            </div>
            <div class="signin-columns">
              <div>
                <div class="signin-list-head">
                  <div class="signin-list-title">瀹滈」鍒楄〃</div>
                  <div class="signin-actions">
                    <button class="btn" onclick="openBatchEventDialog('good')">[ 鎵归噺澧炲姞瀹滈」 ]</button>
                    <button class="btn-danger" onclick="deleteSelectedEvents('good')">[ 鎵归噺鍒犻櫎宸插嬀閫?]</button>
                  </div>
                </div>
                <div class="event-list">
                  ${(state.signInTexts.good_things || []).map((item, i) => eventItem('good', item, i)).join('') || '<div class="empty">鏆傛棤瀹滈」鏂囨湰</div>'}
                </div>
                <div class="row" style="margin-top:8px;">
                  <button class="btn" onclick="addSingleEvent('good')">[ 澧炲姞涓€鏉″疁椤?]</button>
                </div>
              </div>
              <div>
                <div class="signin-list-head">
                  <div class="signin-list-title">蹇岄」鍒楄〃</div>
                  <div class="signin-actions">
                    <button class="btn" onclick="openBatchEventDialog('bad')">[ 鎵归噺澧炲姞蹇岄」 ]</button>
                    <button class="btn-danger" onclick="deleteSelectedEvents('bad')">[ 鎵归噺鍒犻櫎宸插嬀閫?]</button>
                  </div>
                </div>
                <div class="event-list">
                  ${(state.signInTexts.bad_things || []).map((item, i) => eventItem('bad', item, i)).join('') || '<div class="empty">鏆傛棤蹇岄」鏂囨湰</div>'}
                </div>
                <div class="row" style="margin-top:8px;">
                  <button class="btn" onclick="addSingleEvent('bad')">[ 澧炲姞涓€鏉″繉椤?]</button>
                </div>
              </div>
            </div>
          </section>

          <section class="panel col-5">
            <div class="panel-head">
              <div>
                <div class="panel-title">绛惧埌棰勮</div>
                <div class="panel-note">鎸?QQ 鍐呭疄闄呯敓鎴愪範鎯垎琛屾樉绀猴紝鏂逛究鐩存帴姣斿鏈€缁堟晥鏋溿€?/div>
              </div>
              <button class="btn-strong" onclick="saveSignin()">[ 淇濆瓨绛惧埌閰嶇疆 ]</button>
            </div>
            <div class="row" style="margin-bottom:10px;">
              <button class="btn-strong" onclick="previewSignin()">[ 鐢熸垚绛惧埌棰勮 ]</button>
            </div>
            <div class="tag-preview signin-preview" id="signinPreview">灏氭湭鐢熸垚棰勮銆?/div>
            <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">杩愬娍鍖洪棿</div><div class="panel-note">鏍囩銆佹暟鍊煎尯闂村拰鐐硅瘎鏂囨浼氱洿鎺ュ奖鍝嶉瑙堢粨鏋溿€?/div></div><button class="btn" onclick="addRange()">[ 鏂板鍖洪棿 ]</button></div>
            <div class="stack">
              ${ranges.map((r, i) => `
                <div class="profile-card signin-range">
                  <div class="field-grid four">
                    <div class="field"><label>鏍囩</label><input class="input" value="${esc(r.label || '')}" onchange="setRange(${i}, 'label', this.value)"></div>
                    <div class="field"><label>鏈€灏忓€?/label><input class="input" type="number" value="${esc(r.min ?? 0)}" onchange="setRange(${i}, 'min', Number(this.value))"></div>
                    <div class="field"><label>鏈€澶у€?/label><input class="input" type="number" value="${esc(r.max ?? 0)}" onchange="setRange(${i}, 'max', Number(this.value))"></div>
                    <div class="field"><label>閲戝竵淇</label><input class="input" type="number" value="${esc(r.gold_delta ?? 0)}" onchange="setRange(${i}, 'gold_delta', Number(this.value))"></div>
                  </div>
                  <div class="field" style="margin-top:10px;"><label>鐐硅瘎鏂囨锛堟瘡琛屼竴鏉★級</label><textarea class="textarea" onchange="setRangeComments(${i}, this.value)">${esc((r.comments || []).join('\n'))}</textarea></div>
                  <div class="row" style="margin-top:10px;"><button class="btn-danger" onclick="removeRange(${i})">[ 鍒犻櫎鍖洪棿 ]</button></div>
                </div>`).join('') || '<div class="empty">鏆傛棤杩愬娍鍖洪棿</div>'}
            </div>
          </section>
        </div>`;
    }

    function eventItem(kind, item, i) {
      const checked = (kind === 'good' ? state.goodSelected : state.badSelected).includes(i) ? 'checked' : '';
      const placeholder = kind === 'good' ? '杈撳叆瀹滈」鏂囨' : '杈撳叆蹇岄」鏂囨';
      return `<div class="event-item"><input class="event-check" type="checkbox" ${checked} onchange="toggleEventSelect('${kind}', ${i}, this.checked)"><input class="input" id="eventInput-${kind}-${i}" value="${esc(item)}" placeholder="${placeholder}" oninput="setEventText('${kind}', ${i}, this.value)"><button class="btn-danger" onclick="removeEvent('${kind}', ${i})">[ 鍒犻櫎 ]</button></div>`;
    }

    function renderFate() {
      ensureFateDraftCards();
      $('#page-fate').innerHTML = `
        <div class="grid">
          <section class="panel col-12 fate-main">
            <div class="panel-head">
              <div>
                <div class="panel-title">鍛借繍鐗屾。妗?/div>
                <div class="panel-note">涓婁紶鍥剧墖鍚庡彲鐢ㄢ€滄娴嬫湭瀹屾垚缂栬緫鐨勭墝鈥濇妸鏈畬鍠勭殑鐗岀洿鎺ョ疆椤躲€?/div>
              </div>
              <div class="row">
                <button class="btn-strong" onclick="openFateEditor(-1)">[ 鏂板鍛借繍鐗?]</button>
                <button class="btn" onclick="uploadFateImages()">[ 鎵归噺涓婁紶鍥剧墖 ]</button>
                <button class="btn-danger" onclick="detectIncompleteFateCards()">[ 妫€娴嬫湭瀹屾垚缂栬緫鐨勭墝 ]</button>
                <button class="btn" onclick="saveFateCards()">[ 淇濆瓨鍏ㄩ儴 ]</button>
              </div>
            </div>
            <div class="archive-grid">
              ${state.fateCards.map((card, i) => fateItem(card, i)).join('') || '<div class="empty">鏆傛棤鍛借繍鐗?/div>'}
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
          <div class="archive-cover">${has ? `<img src="${src}" alt="鍛借繍鐗屽浘鐗?>` : '鏈粦瀹氬浘鐗?}</div>
          <div class="archive-body">
            <div class="archive-title">${esc(card.text || '鏈懡鍚嶅懡杩愮墝')}</div>
            <div class="archive-meta">
              <span class="badge orange">閲戝竵 ${esc(card.gold ?? 0)}</span>
              ${incomplete ? '<span class="badge">鏈畬鎴?/span>' : ''}
            </div>
            <div class="archive-actions">
              <button class="btn-strong" onclick="openFateEditor(${i})">[ 缂栬緫 ]</button>
              <button class="btn-green" onclick="duplicateFateCard(${i})">[ 澶嶅埗 ]</button>
              <button class="btn-danger" onclick="deleteFateCard(${i})">[ 鍒犻櫎 ]</button>
            </div>
          </div>
        </article>`;
    }

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
                <div class="panel-title">鍔熻兘鐗屾。妗?/div>
                <div class="panel-note">鐢ㄤ笅鎷夌瓫閫変笉鍚岀被鍨嬬殑鐗岋紝绋€鏈夊害杈圭紭浼氬彂鍑烘洿鏄庢樉鐨勬贰鍏夈€?/div>
              </div>
              <div class="row">
                <button class="btn-strong" onclick="openFuncEditor(-1)">[ 鏂板鍔熻兘鐗?]</button>
                <button class="btn" onclick="batchAddCards()">[ 鎵归噺娣诲姞 ]</button>
                <button class="btn" onclick="uploadFuncImages()">[ 鎵归噺涓婁紶鍥剧墖 ]</button>
                <button class="btn" onclick="saveFuncCards()">[ 淇濆瓨鍏ㄩ儴 ]</button>
              </div>
            </div>
            <div class="filter-bar">
              <div class="filter-bar-title">绫诲瀷绛涢€?/div>
              <select class="select filter-select" onchange="setFuncFilter(this.value)">
                <option value="all" ${filter === 'all' ? 'selected' : ''}>鍏ㄩ儴</option>
                <option value="attack" ${filter === 'attack' ? 'selected' : ''}>鏀诲嚮</option>
                <option value="heal" ${filter === 'heal' ? 'selected' : ''}>杈呭姪</option>
                <option value="defense" ${filter === 'defense' ? 'selected' : ''}>闃插尽</option>
                <option value="other" ${filter === 'other' ? 'selected' : ''}>鍏朵粬</option>
              </select>
              <div class="filter-summary">褰撳墠鏄剧ず ${filteredEntries.length} / ${state.funcCards.length} 锝?鏈畬鎴?${incompleteCount} 寮?/div>
            </div>
            ${filter === 'all' ? `
            <div class="archive-index-group" style="margin-bottom:14px;">
              <div class="archive-index-title">寰呭缓妗ｅ浘鐗?/div>
              <div class="pending-grid">
                ${unusedImages.map(file => `
                  <article class="archive-card">
                    <div class="archive-cover"><img src="/assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}" alt="${esc(file)}"></div>
                    <div class="archive-body">
                      <div class="pending-caption">杩欏紶鍥剧墖杩樻病鏈夎浠讳綍鍔熻兘鐗屼娇鐢ㄣ€?/div>
                      <div class="archive-actions">
                        <button class="btn-green" onclick="openFuncEditorFromImage('${esc(file)}')">[ 缂栬緫 ]</button>
                        <button class="btn" onclick="openFuncEditorFromImage('${esc(file)}')">[ 寤虹墝 ]</button>
                        <button class="btn-danger" onclick="deleteFuncImage('${esc(file)}')">[ 鍒犻櫎 ]</button>
                      </div>
                </div>
                  </article>`).join('') || '<div class="empty">褰撳墠娌℃湁寰呭缓妗ｅ浘鐗?/div>'}
              </div>
            </div>` : ''}
            <div class="archive-grid">
              ${filteredEntries.map(entry => funcItem(entry.card, entry.index)).join('') || '<div class="empty">褰撳墠绛涢€変笅娌℃湁鍔熻兘鐗?/div>'}
            </div>
          </section>
        </div>`;
      renderHeroAux();
    }

    function funcItem(card, i) {
      const has = card.filename && state.images.includes(card.filename);
      const src = has ? `/assets/${encodeURIComponent(card.filename)}?profile=${encodeURIComponent(state.currentProfile)}` : '';
      const tags = (card.tags || []).slice(0, 4).map(tag => `<span class="badge">${esc(humanizeTag(tag))}</span>`).join('') || '<span class="helper">鏈瀹氭晥鏋?/span>';
      return `
        <article class="archive-card rarity-${Number(card.rarity) || 1}">
          <div class="archive-cover">${has ? `<img src="${src}" alt="鍔熻兘鐗屽浘鐗?>` : '鏈粦瀹氬浘鐗?}</div>
          <div class="archive-body">
            <div class="archive-title">${esc(card.card_name || '鏈懡鍚嶅姛鑳界墝')}</div>
            <div class="archive-meta">
              <span class="badge light">${esc(rarityLabelMap[Number(card.rarity) || 1] || '鏅€?)}</span>
              <span class="badge">${esc(typeLabelMap[card.type] || '鏈垎绫?)}</span>
            </div>
            <div class="archive-tag-row">${tags}</div>
            <div class="archive-desc">${esc(card.description || '褰撳墠杩樻病鏈夋弿杩般€?)}</div>
            <div class="archive-actions">
              <button class="btn-strong" onclick="openFuncEditor(${i})">[ 缂栬緫 ]</button>
              <button class="btn-green" onclick="duplicateFuncCard(${i})">[ 澶嶅埗 ]</button>
              <button class="btn-danger" onclick="deleteFuncCard(${i})">[ 鍒犻櫎 ]</button>
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
        { label: '缇ょ粍鏁伴噺', value: state.stats.total_groups || 0, note: '宸叉帴鍏ュ綋鍓嶆柟妗堢殑缇ょ粍', accent: '#6f96ff' },
        { label: '鐢ㄦ埛鏁伴噺', value: state.stats.total_users || 0, note: '鏂规涓嬭缁熻鍒扮殑鐢ㄦ埛', accent: '#69dec1' },
        { label: '鍔熻兘鐗屽崱姹?, value: state.funcCards.length, note: `宸插畬鍠?${funcCompleted} / ${state.funcCards.length || 0}`, accent: '#9f6cff' },
        { label: '鍛借繍鐗屽崱姹?, value: state.fateCards.length, note: `宸插畬鍠?${fateCompleted} / ${state.fateCards.length || 0}`, accent: '#ff9a7c' },
      ];

      $('#page-stats').innerHTML = `
        <div class='grid'>
          <section class='panel col-12 stats-main'>
            <div class='stats-profile-bar'>
              <div>
                <div class='tiny'>[ PROFILE / ANALYTICS ]</div>
                <div class='stats-profile-title'>${esc(getProfileName())}</div>
                <div class='panel-note'>鎶婃柟妗堟瑙堛€佺兢缁勭儹搴︺€佹寔鐗屾帓琛屽拰鍗℃睜瀹屾垚搴﹀帇鎴愪竴灞忥紝鍒囨崲鏂规鍚庝細鍚屾鏇存柊鎵€鏈夌粺璁°€?/div>
                <div class='stats-profile-meta'>
                  <span class='badge light'>缇ょ粍 ${state.stats.total_groups || 0}</span>
                  <span class='badge'>鐢ㄦ埛 ${state.stats.total_users || 0}</span>
                  <span class='badge orange'>鎺掕鏉＄洰 ${holders.length}</span>
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
                <div class='panel-title'>缇ょ粍鐑害鍒嗗竷</div>
                <div class='panel-note'>鎸夌敤鎴锋暟閲忔帓搴忥紝鐢ㄨ繘搴︽潯蹇€熺湅鍑哄綋鍓嶆柟妗堜笅鍝簺缇や綋閲忔洿楂樸€?/div>
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
                        <div class='group-entry-meta'>缇ょ粍鎴愬憳缁熻</div>
                      </div>
                      <span class='badge'>${count} 鐢ㄦ埛</span>
                    </div>
                    <div class='group-bar'><div class='group-bar-fill' style='width:${width}%;'></div></div>
                  </article>`;
              }).join('') || `<div class='empty'>鏆傛棤缇ょ粍鏁版嵁</div>`}
            </div>
          </section>

          <section class='panel col-5'>
            <div class='panel-head'>
              <div>
                <div class='panel-title'>鎸佺墝鎺掕</div>
                <div class='panel-note'>姒滃崟鏀规垚鐙珛鍚嶆鍗＄墖锛屽眰绾ф洿娓呮锛屼笉浼氬儚涓€鍒楁祦姘磋处銆?/div>
              </div>
            </div>
            <div class='leaderboard-list'>
              ${holders.slice(0, 10).map((item, idx) => `
                <article class='leaderboard-item'>
                  <span class='rank-badge ${idx < 3 ? `rank-top-${idx + 1}` : ''}'>#${idx + 1}</span>
                  <div>
                    <div class='leaderboard-name'>${esc(item[0])}</div>
                    <div class='group-entry-meta'>褰撳墠鏂规鎸佺墝浜烘暟鎺掕</div>
                  </div>
                  <div class='leaderboard-count'>${item[1]} 浜烘寔鏈?/div>
                </article>`).join('') || `<div class='empty'>鏆傛棤鎸佺墝鎺掕</div>`}
            </div>
          </section>

          <section class='panel col-6'>
            <div class='panel-head'>
              <div>
                <div class='panel-title'>鍗℃睜姒傝</div>
                <div class='panel-note'>鎶婂懡杩愮墝鍜屽姛鑳界墝鎷嗘垚涓ゅ紶缁熻鍗★紝淇℃伅鏇村畬鏁达紝涔熸洿鏈夌湡姝ｇ殑鍗＄墖鎰熴€?/div>
              </div>
            </div>
            <div class='pool-summary-grid'>
              <article class='pool-card fate'>
                <div class='pool-card-head'>
                  <div>
                    <div class='tiny'>[ FATE DECK ]</div>
                    <div class='pool-card-title'>鍛借繍鐗?/div>
                  </div>
                  <div class='pool-card-value'>${state.fateCards.length}</div>
                </div>
                <div class='pool-card-meta'>宸插畬鍠?${fateCompleted} 寮?锝?骞冲潎閲戝竵鍊?${fateAvgGold}</div>
                <div class='mini-list'>
                  <div class='mini-metric'>
                    <div class='mini-metric-row'><span>寤烘。瀹屾垚搴?/span><span>${fateCompletionPercent.toFixed(1)}%</span></div>
                    <div class='mini-bar'><div class='mini-bar-fill' style='width:${fateCompletionPercent}%; --metric-start:#ffb08c; --metric-end:#ff7f8d;'></div></div>
                  </div>
                  <div class='mini-metric'>
                    <div class='mini-metric-row'><span>鍥剧墖缁戝畾鐜?/span><span>${fateBoundPercent.toFixed(1)}%</span></div>
                    <div class='mini-bar'><div class='mini-bar-fill' style='width:${fateBoundPercent}%; --metric-start:#ffc46d; --metric-end:#ff8a72;'></div></div>
                  </div>
                </div>
              </article>

              <article class='pool-card func'>
                <div class='pool-card-head'>
                  <div>
                    <div class='tiny'>[ FUNCTION DECK ]</div>
                    <div class='pool-card-title'>鍔熻兘鐗?/div>
                  </div>
                  <div class='pool-card-value'>${state.funcCards.length}</div>
                </div>
                <div class='pool-card-meta'>宸插畬鍠?${funcCompleted} 寮?锝?鏈畬鎴?${Math.max(0, state.funcCards.length - funcCompleted)} 寮?/div>
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
                <div class='panel-title'>鍔熻兘鐗岀█鏈夊害鍒嗗竷</div>
                <div class='panel-note'>鐢ㄦ洿鏌斿拰浣嗘洿鍒嗘槑鐨勯鑹叉樉绀虹█鏈夊害鍗犳瘮锛屾柟渚垮揩閫熷垽鏂綋鍓嶇墝姹犵粨鏋勩€?/div>
              </div>
            </div>
            <div class='stats-distribution-list'>
              ${funcRarityDistribution.map(item => `
                <article class='dist-item'>
                  <div class='dist-item-head'>
                    <span class='dist-dot' style='--dot-color:${item.color};'></span>
                    <div class='dist-label'>${item.label}</div>
                    <div class='dist-count'>${item.count} 寮?/ ${item.percent.toFixed(1)}%</div>
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
      showToast(`宸插垏鎹㈠埌鏂规锛?{getProfileName(id)}`);
    }

    async function editProfile(id) {
      const current = state.profiles.find(p => p.profile_id === id);
      state.editingProfileId = id;
      openDialog('缂栬緫鏂规', `
        <div>
          <div>
            <div class="field">
              <label>鏂规鍚嶇О</label><input class="input" id="newProfileName" value="${esc(current?.display_name || '')}">
            </div>
            <div class="field" style="margin-top:12px;"><label>缁戝畾缇ゅ彿锛堟瘡琛屼竴涓級</label><textarea class="textarea" id="editProfileGroups">${esc((current?.groups || []).join('\n'))}</textarea></div>
            <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveProfileEdit()">[ 淇濆瓨鏂规 ]</button><button class="btn-danger" onclick="deleteProfileConfirm()">[ 鍒犻櫎鏂规 ]</button></div>
          </div>
        </div>`, 'create');
    }

    async function saveProfileEdit() {
      const id = state.editingProfileId;
      const current = state.profiles.find(p => p.profile_id === id);
      const name = $('#newProfileName')?.value?.trim();
      const groupLines = ($('#editProfileGroups')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean);
      if (!id || !name) return showToast('鏂规鍚嶇О涓嶈兘涓虹┖銆?, true);
      const res = await apiPost('/api/profile_meta', { profile_id:id, display_name:name, cover_image: '' });
      if (!res.ok) return showToast(res.error || '淇濆瓨澶辫触銆?, true);
      const before = new Set(current?.groups || []);
      const after = new Set(groupLines);
      for (const gid of before) {
        if (!after.has(gid)) await apiPost('/api/profile_unbind_group', { profile_id:id, group_id:gid });
      }
      for (const gid of after) {
        if (!before.has(gid)) await apiPost('/api/profile_bind_group', { profile_id:id, group_id:gid });
      }
      closeDialog();
      await refreshProfilesAndStats();
      renderAll();
      showToast('鏂规缂栬緫宸蹭繚瀛樸€?);
    }

    async function deleteProfileConfirm() {
      const id = state.editingProfileId;
      const current = state.profiles.find(p => p.profile_id === id);
      if (!id) return;
      if (current?.is_default) return showToast('榛樿鏂规涓嶈兘鍒犻櫎銆?, true);
      if (!confirm(`纭鍒犻櫎鏂规銆?{current?.display_name || id}銆嶅悧锛焅n缁戝畾鍒拌鏂规鐨勭兢缁勪細鑷姩鍒囧洖榛樿鏂规銆俙)) return;
      try {
        const res = await apiDeleteProfileById(id);
        if (!res.ok) return showToast(`鍒犻櫎澶辫触锛?{res.error || 'unknown error'}`, true);
        closeDialog();
        state.currentProfile = res.fallback_profile || 'default';
        state.profiles = state.profiles.filter(p => p.profile_id !== id);
        await loadProfiles();
        await refreshActiveProfileData();
        renderAll();
        showToast('鏂规宸插垹闄ゃ€?);
      } catch (e) {
        console.error(e);
        showToast(`鍒犻櫎澶辫触锛?{e?.message || e}`, true);
      }
    }

    async function bindGroupPrompt(id) {
      const gid = prompt('璇疯緭鍏ョ兢鍙?);
      if (!gid) return;
      if (!/^\d+$/.test(gid)) return showToast('缇ゅ彿鏍煎紡鏃犳晥銆?, true);
      const res = await apiPost('/api/profile_bind_group', { profile_id:id, group_id:gid });
      if (res.ok) { await refreshProfilesAndStats(); renderAll(); showToast('缇ゅ彿缁戝畾鎴愬姛銆?); }
      else showToast(res.error || '缁戝畾澶辫触銆?, true);
    }

    async function unbindGroup(id, gid) {
      if (!confirm(`纭瑙ｇ粦缇ゅ彿 ${gid} 鍚楋紵`)) return;
      const res = await apiPost('/api/profile_unbind_group', { profile_id:id, group_id:gid });
      if (res.ok) { await refreshProfilesAndStats(); renderAll(); showToast('缇ゅ彿宸茶В缁戙€?); }
      else showToast(res.error || '瑙ｇ粦澶辫触銆?, true);
    }

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
        { value:'__blank__', label:'鏃狅紙绌虹櫧鏂规锛? },
        { value:'__builtin_default__', label:'鍐呯疆榛樿妯℃澘' },
        ...state.profiles.map(p => ({ value:p.profile_id, label:p.display_name || p.profile_id })),
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
      openDialog('鏂板缓鏂规', `
        <div>
          <div>
            <div class="field"><label>鏂规鍚嶇О</label><input class="input" id="newProfileName"></div>
            <div class="field-grid" style="margin-top:12px;grid-template-columns:minmax(0,1fr) 160px;align-items:end;">
              <div class="field"><label>澶嶅埗鏉ユ簮</label>${renderCopySourceSelect('copyFromSelect', 'copyFrom', selectedCopyFrom)}</div>
              <div class="field"><label>蹇嵎鍒涘缓</label><button class="btn" onclick="createBuiltinDefaultProfile()">[ 鏂板缓榛樿閰嶇疆 ]</button></div>
            </div>
            <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="createProfileConfirm()">[ 纭鍒涘缓 ]</button></div>
          </div>
        </div>`, 'create');
    }

    async function createProfileConfirm() {
      const name = $('#newProfileName')?.value?.trim();
      const copy_from = $('#copyFrom')?.value || 'default';
      if (!name) return showToast('鏂规鍚嶇О涓嶈兘涓虹┖銆?, true);
      const res = await apiPost('/api/profiles', { name, copy_from });
      if (res.ok) {
        closeDialog();
        await loadProfiles();
        renderAll();
        showToast('鏂版柟妗堝凡鍒涘缓銆?);
      }
      else showToast(res.error || '鍒涘缓澶辫触銆?, true);
    }
    async function createBuiltinDefaultProfile() {
      const name = $('#newProfileName')?.value?.trim();
      if (!name) return showToast('璇峰厛濉啓鏂规鍚嶇О銆?, true);
      const res = await apiPost('/api/profiles', { name, copy_from:'__builtin_default__' });
      if (res.ok) {
        closeDialog();
        await loadProfiles();
        renderAll();
        showToast('榛樿妯℃澘鏂规宸插垱寤恒€?);
      }
      else showToast(res.error || '鍒涘缓澶辫触銆?, true);
    }

    function setAccessMode(mode) {
      state.groupAccess.mode = mode;
      renderOverview();
      updateTop();
    }

    async function saveGroupAccess() {
      state.groupAccess.blacklist = state.groupAccess.mode === 'blacklist'
        ? ($('#blacklistInput')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean)
        : [];
      state.groupAccess.whitelist = state.groupAccess.mode === 'whitelist'
        ? ($('#whitelistInput')?.value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean)
        : [];
      const res = await apiPost('/api/group_access', { config: state.groupAccess });
      if (res.ok) showToast('璁块棶鎺у埗宸蹭繚瀛樸€?);
      else showToast(res.error || '淇濆瓨澶辫触銆?, true);
    }

    function toggleRuntime(path, el) {
      const next = !getDeep(state.runtimeConfig, path);
      setDeep(state.runtimeConfig, path, next);
      renderRuntime();
    }
    function setRuntimeValue(path, value) {
      const finalVal = value === '' ? '' : (isNaN(value) ? value : Number(value));
      setDeep(state.runtimeConfig, path, finalVal);
      if (path.includes('custom_rarity_weights')) updateRarityChart();
    }
    async function saveRuntime() {
      const res = await apiPost('/api/runtime_config', { config: state.runtimeConfig });
      if (res.ok) showToast('杩愯閰嶇疆宸蹭繚瀛樸€?);
      else showToast(res.error || '淇濆瓨澶辫触銆?, true);
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
      if (kind === 'good') state.goodSelected = []; else state.badSelected = [];
      renderSignin();
    }
    function deleteSelectedEvents(kind) {
      const arr = kind === 'good' ? state.signInTexts.good_things : state.signInTexts.bad_things;
      const selected = new Set(kind === 'good' ? state.goodSelected : state.badSelected);
      if (!selected.size) return showToast('璇峰厛鍕鹃€夎鍒犻櫎鐨勬潯鐩€?, true);
      const remain = arr.filter((_, i) => !selected.has(i));
      if (kind === 'good') { state.signInTexts.good_things = remain; state.goodSelected = []; }
      else { state.signInTexts.bad_things = remain; state.badSelected = []; }
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
      state.signInTexts.luck_ranges.push({ label:'鏂板尯闂?, min:1, max:100, gold_delta:0, comments:[] });
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
      if (!ranges.length) return showToast('璇峰厛閰嶇疆杩愬娍鍖洪棿銆?, true);
      const range = ranges[Math.floor(Math.random() * ranges.length)];
      const comment = (range.comments || [])[Math.floor(Math.random() * (range.comments?.length || 1))] || '浠婃棩鏃犻澶栨壒娉ㄣ€?;
      const good = (state.signInTexts.good_things || [])[Math.floor(Math.random() * Math.max(1, state.signInTexts.good_things.length))] || '鏆傛棤瀹滈」';
      const bad = (state.signInTexts.bad_things || [])[Math.floor(Math.random() * Math.max(1, state.signInTexts.bad_things.length))] || '鏆傛棤蹇岄」';
      const score = Math.floor(Math.random() * Math.max(1, (range.max ?? 100) - (range.min ?? 1) + 1)) + (range.min ?? 1);
      $('#signinPreview').textContent = [
        `浠婃棩杩愬娍锝?{range.label || '鏈煡'}`,
        `鏁板€硷綔${score}`,
        `閲戝竵淇锝?{range.gold_delta || 0}`,
        `鐐硅瘎锝?{comment}`,
        `瀹滐綔${good}`,
        `蹇岋綔${bad}`,
      ].join('\n');
    }
    async function saveSignin() {
      const res = await apiPost('/api/sign_in_texts', { texts: state.signInTexts });
      if (res.ok) showToast('绛惧埌閰嶇疆宸蹭繚瀛樸€?);
      else showToast(res.error || '淇濆瓨澶辫触銆?, true);
    }

    function openFateEditor(index) {
      state.editingFateIndex = index;
      const card = index >= 0 ? JSON.parse(JSON.stringify(state.fateCards[index])) : { text:'', gold:0, filename:'' };
      openDialog(index >= 0 ? '缂栬緫鍛借繍鐗? : '鏂板鍛借繍鐗?, `
        <div class="split">
          <div>
            <div class="field-grid">
              <div class="field"><label>鏂囨</label><input class="input" id="fateText" value="${esc(card.text || '')}"></div>
              <div class="field"><label>閲戝竵鍊?/label><input class="input" type="number" id="fateGold" value="${esc(card.gold ?? 0)}"></div>
            </div>
            <div class="field" style="margin-top:12px;"><label>鍥剧墖鏂囦欢鍚?/label><input class="input" id="fateFilename" value="${esc(card.filename || '')}"></div>
            <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveFateEditor()">[ 鍐欏叆鍛借繍鐗?]</button></div>
          </div>
          <div>
            <div class="panel-title" style="font-size:14px;margin-bottom:10px;">鍙敤鍥剧墖</div>
            <div class="asset-grid">${state.fateImages.map(file => `<div class="asset-item"><div class="thumb"><img src="/fate_assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}"></div><div class="helper" style="margin:8px 0;word-break:break-all;">${esc(file)}</div><button class="btn-mini" onclick="pickFile('fateFilename','${esc(file)}')">閫夌敤</button></div>`).join('') || '<div class="empty">鏆傛棤鍥剧墖</div>'}</div>
          </div>
        </div>`);
    }
    function pickFile(id, value) { const el = document.getElementById(id); if (el) el.value = value; }
    async function saveFateEditor() {
      const payload = { text: $('#fateText')?.value?.trim() || '鏈懡鍚嶅懡杩愮墝', gold: Number($('#fateGold')?.value || 0), filename: $('#fateFilename')?.value?.trim() || '' };
      if (state.editingFateIndex >= 0) state.fateCards[state.editingFateIndex] = payload; else state.fateCards.push(payload);
      closeDialog();
      renderFate();
      await saveFateCards(false);
    }
    async function saveFateCards(show = true) {
      const res = await apiPost('/api/fate_cards', { cards: state.fateCards });
      if (res.ok) { if (show) showToast('鍛借繍鐗屽凡淇濆瓨銆?); }
      else showToast(res.error || '淇濆瓨澶辫触銆?, true);
    }
    async function deleteFateCard(i) {
      if (!confirm('纭鍒犻櫎璇ュ懡杩愮墝鍚楋紵')) return;
      state.fateCards.splice(i, 1);
      renderFate();
      await saveFateCards(false);
      showToast('鍛借繍鐗屽凡鍒犻櫎銆?);
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
        const res = await fetch(`${endpoint}?profile=${encodeURIComponent(state.currentProfile)}`, { method:'POST', body:fd });
        const data = await res.json();
        if (data.ok) {
          await onReload();
          onRender();
          showToast(successText);
        } else {
          showToast(data.error || '涓婁紶澶辫触銆?, true);
        }
      };
      input.click();
    }
    async function deleteAsset(apiBase, file, onReload, onRender) {
      if (!confirm(`纭鍒犻櫎鍥剧墖 ${file} 鍚楋紵`)) return;
      const res = await apiDelete(`${apiBase}/${encodeURIComponent(file)}`);
      if (res.ok) {
        await onReload();
        onRender();
        showToast('鍥剧墖宸插垹闄ゃ€?);
      } else {
        showToast(res.error || '鍒犻櫎澶辫触銆?, true);
      }
    }
    async function uploadFateImages() {
      return uploadImages('/api/upload_fate_image', loadFate, renderFate, '鍛借繍鐗屽浘鐗囨壒閲忎笂浼犲畬鎴愩€?);
    }

    function normalizeEffectsForCard(card) {
      const tags = card?.tags || [];
      const parsed = tags.map(tagToEffect).filter(Boolean);
      return parsed.length ? parsed : [{ key: card?.type === 'defense' ? 'add_shield' : card?.type === 'heal' ? 'cleanse' : 'steal', params:[] }];
    }

    function renderEffectRows(type) {
      const list = state.editingFuncEffects || [];
      return list.map((effect, idx) => {
        const options = effectCatalog[type] || [];
        const chosen = options.find(o => o.key === effect.key) || options[0] || { key:'', params:[] };
        const params = chosen.params || [];
        return `
          <div class="effect-row">
            <div class="field"><label>鏁堟灉绫诲埆</label><select class="select" onchange="setEffectKey(${idx}, this.value)">${options.map(o => `<option value="${esc(o.key)}" ${o.key === effect.key ? 'selected' : ''}>${esc(o.name)}</option>`).join('')}</select></div>
            <div class="field"><label>鏁堟灉鎽樿</label><div class="tag-preview">${esc(effectLabel(effect))}</div></div>
            <div class="field"><label>鍙傛暟</label><div class="field-grid ${params.length >= 3 ? 'three' : params.length === 2 ? '' : ''}">${params.map((name, pi) => `<input class="input" placeholder="${esc(name)}" value="${esc(effect.params?.[pi] || '')}" onchange="setEffectParam(${idx}, ${pi}, this.value)">`).join('') || '<div class="helper">姝ゆ晥鏋滄棤棰濆鍙傛暟</div>'}</div></div>
            <div class="field"><label>鎿嶄綔</label><button class="btn-danger" onclick="removeEffectRow(${idx})">[ 鍒犻櫎鏁堟灉 ]</button></div>
          </div>`;
      }).join('');
    }

    function effectPreviewHtml() {
      const tags = state.editingFuncEffects.map(effectToTag).filter(Boolean);
      return tags.length ? tags.map(tag => `<span class="badge">${esc(humanizeTag(tag))}</span>`).join('') : '<span class="helper">灏氭湭鐢熸垚浠讳綍鏁堟灉銆?/span>';
    }

    function openFuncEditor(index) {
      state.editingFuncIndex = index;
      const card = index >= 0 ? JSON.parse(JSON.stringify(state.funcCards[index])) : { card_name:'', type:'attack', rarity:1, filename:'', description:'', tags:[] };
      state.editingFuncEffects = normalizeEffectsForCard(card);
      const type = card.type || 'attack';
      openDialog(index >= 0 ? '缂栬緫鍔熻兘鐗? : '鏂板鍔熻兘鐗?, funcEditorHtml(card, type));
    }

    function funcEditorHtml(card, type) {
      return `
        <div class="split">
          <div>
            <div class="field-grid">
              <div class="field"><label>鍗＄墝鍚嶇О</label><input class="input" id="funcName" value="${esc(card.card_name || '')}"></div>
              <div class="field"><label>绋€鏈夊害</label><select class="select" id="funcRarity">${Object.entries(rarityLabelMap).map(([v,t]) => `<option value="${v}" ${Number(card.rarity) === Number(v) ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>
            </div>
            <div class="field-grid" style="margin-top:12px;">
              <div class="field"><label>澶х被</label><select class="select" id="funcType" onchange="changeFuncType(this.value)">${Object.entries(typeLabelMap).map(([v,t]) => `<option value="${v}" ${type === v ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>
              <div class="field"><label>鍥剧墖鏂囦欢鍚?/label><input class="input" id="funcFilename" value="${esc(card.filename || '')}"></div>
            </div>
            <div class="field" style="margin-top:12px;"><label>鎻忚堪</label><textarea class="textarea" id="funcDesc">${esc(card.description || '')}</textarea></div>
            <div class="panel-head" style="margin-top:14px;"><div><div class="panel-title">鏁堟灉寮曞</div><div class="panel-note">鍏堥€夊ぇ绫伙紝鍐嶉€夋晥鏋滐紝鍐嶅～鍙傛暟銆備細鑷姩杞垚鏍囩锛屼絾灞曠ず缁欎綘鐨勯兘鏄腑鏂囥€?/div></div><button class="btn" onclick="addEffectRow()">[ 鏂板鏁堟灉 ]</button></div>
            <div class="effect-builder" id="effectBuilder">${renderEffectRows(type)}</div>
            <div class="field" style="margin-top:12px;"><label>鏍囩棰勮</label><div class="tag-preview" id="effectPreview">${effectPreviewHtml()}</div></div>
            <div class="row" style="margin-top:12px;"><button class="btn-strong" onclick="saveFuncEditor()">[ 鍐欏叆鍔熻兘鐗?]</button></div>
          </div>
          <div>
            <div class="panel-title" style="font-size:14px;margin-bottom:10px;">鍥惧儚搴?/div>
            <div class="asset-grid">${state.images.map(file => `<div class="asset-item"><div class="thumb"><img src="/assets/${encodeURIComponent(file)}?profile=${encodeURIComponent(state.currentProfile)}"></div><div class="helper" style="margin:8px 0;word-break:break-all;">${esc(file)}</div><button class="btn-mini" onclick="pickFile('funcFilename','${esc(file)}')">閫夌敤</button></div>`).join('') || '<div class="empty">鏆傛棤鍥剧墖</div>'}</div>
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
      $('#dialogBody').innerHTML = funcEditorHtml({ card_name:name, rarity:Number(rarity), filename, description }, type);
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
        card_name: $('#funcName')?.value?.trim() || '鏈懡鍚嶅姛鑳界墝',
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
      showToast('鍔熻兘鐗屽凡鍐欏叆銆?);
    }
    async function saveFuncCards(show = true) {
      const res = await apiPost('/api/func_cards', { cards: state.funcCards });
      if (res.ok) { if (show) showToast('鍔熻兘鐗屽凡淇濆瓨銆?); }
      else showToast(res.error || '淇濆瓨澶辫触銆?, true);
    }
    async function deleteFuncCard(i) {
      if (!confirm('纭鍒犻櫎璇ュ姛鑳界墝鍚楋紵')) return;
      state.funcCards.splice(i, 1);
      renderCards();
      await saveFuncCards(false);
      await refreshCardAssets(false);
      renderCards();
      showToast('鍔熻兘鐗屽凡鍒犻櫎銆?);
    }
    async function batchAddCards() {
      const raw = prompt('姣忚鏍煎紡锛氬崱鐗屽悕,澶х被(attack/heal/defense),绋€鏈夊害');
      if (!raw) return;
      raw.split(/\r?\n/).map(v => v.trim()).filter(Boolean).forEach(line => {
        const [name, type, rarity] = line.split(',').map(s => s?.trim() || '');
        if (!name) return;
        state.funcCards.push({ card_name:name, type:type || 'attack', rarity:Number(rarity || 1), filename:'', description:'', tags:[] });
      });
      renderCards();
      await saveFuncCards(false);
      showToast('鎵归噺娣诲姞瀹屾垚銆?);
    }
    async function uploadFuncImages() {
      return uploadImages('/api/upload_image', loadCards, renderCards, '鍔熻兘鐗屽浘鐗囨壒閲忎笂浼犲畬鎴愩€?);
    }
    async function deleteFuncImage(file) {
      return deleteAsset('/api/images', file, loadCards, renderCards);
    }
    async function deleteFateImage(file) {
      return deleteAsset('/api/fate_images', file, loadFate, renderFate);
    }
    async function refreshCardAssets(show = true) {
      await loadCards();
      if (show) showToast('璧勬簮鎵弿瀹屾垚銆?);
    }

    function bindEvents() {
      $$('.nav-btn').forEach(btn => btn.addEventListener('click', () => setPage(btn.dataset.page)));
      $('#reloadBtn').addEventListener('click', () => loadAll(true));
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

    document.addEventListener('DOMContentLoaded', async () => {
      bindEvents();
      await loadAll();
    });
*/

(function loadModernWebUi() {
  if (window.__legacyAppJsLoaderInstalled) return;
  window.__legacyAppJsLoaderInstalled = true;

  if (window.__startWebUi) {
    window.__startWebUi();
    return;
  }

  const existing = Array.from(document.scripts).find(script => script.src && script.src.includes('/static/js/main.js'));
  if (existing) {
    existing.addEventListener('load', () => {
      if (window.__startWebUi) window.__startWebUi();
    }, { once: true });
    return;
  }

  const script = document.createElement('script');
  script.src = '/static/js/main.js';
  script.defer = true;
  script.onload = () => {
    if (window.__startWebUi) window.__startWebUi();
  };
  document.head.appendChild(script);
})();
