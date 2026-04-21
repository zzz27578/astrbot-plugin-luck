# WebUI 前端架构说明

## 当前运行入口

### 主入口
- `webui/static/app.html`
- **当前为单文件集成入口**
- 已内联：
  - 样式
  - 前端逻辑
  - 本地 `file://` 预览 mock
- 可直接双击打开本地预览

### 服务端入口
- `webui/server.py`
- `serve_index()` 当前应返回 `app.html`

---

## 文件职责

### `app.html`
当前为**单文件前端主文件**，内部已集成：
- 页面骨架
- 样式
- 前端逻辑
- 本地预览 mock

适合修改：
- 页面结构
- 区域增减
- 样式
- 交互逻辑
- 本地预览效果

---

## `main.js` 逻辑分区

建议以后优先按下面关键字定位：

### 1. 基础工具
可搜索：
- `const state =`
- `const pageMeta =`
- `function showToast`
- `function apiUrl`

用途：
- 全局状态
- 页面标题文案
- 通用提示
- API 基础封装

---

### 2. 数据加载层
可搜索：
- `async function loadProfiles`
- `async function loadRuntime`
- `async function loadGroupAccess`
- `async function loadSignin`
- `async function loadFate`
- `async function loadCards`
- `async function loadStats`
- `async function loadAll`

用途：
- 所有后端接口读取
- 页面刷新联动

如果以后你说：
- “这个页面切换后没刷新”
- “方案切换后统计没更新”
- “某个接口取数不对”

优先看这里。

---

### 3. 总览页
可搜索：
- `function renderOverview`
- `async function useProfile`
- `async function editProfile`
- `async function saveProfileEdit`
- `async function deleteProfileConfirm`
- `async function bindGroupPrompt`
- `async function unbindGroup`
- `function setAccessMode`
- `async function saveGroupAccess`

用途：
- 方案管理
- 当前方案切换
- 群组绑定解绑
- 访问控制

如果以后你说：
- “把方案卡片改成别的样子”
- “增加一个方案字段”
- “调整黑白名单逻辑”

优先看这里。

---

### 4. 运行配置页
可搜索：
- `function renderRuntime`
- `function toggleBox`
- `function numField`
- `function selectField`
- `function toggleRuntime`
- `function setRuntimeValue`
- `async function saveRuntime`
- `function buildRarityWeightPreview`
- `function updateRarityChart`

用途：
- 模块开关
- 抽卡经济
- 稀有度权重
- 公开对赌配置

如果以后你说：
- “这里加一个新配置项”
- “改一个配置字段名”
- “修改权重图表现”

优先看这里。

---

### 5. 签到配置页
可搜索：
- `function renderSignin`
- `function eventItem`
- `function openBatchEventDialog`
- `function confirmBatchEventAdd`
- `function addSingleEvent`
- `function addRange`
- `function previewSignin`
- `async function saveSignin`

用途：
- 宜 / 忌事件池
- 运势区间
- 预览生成

如果以后你说：
- “签到文案结构改一下”
- “增加新字段”
- “预览格式重做”

优先看这里。

---

### 6. 命运牌页
可搜索：
- `function renderFate`
- `function fateItem`
- `function openFateEditor`
- `async function saveFateEditor`
- `async function saveFateCards`
- `async function deleteFateCard`
- `async function uploadFateImages`
- `function detectIncompleteFateCards`

用途：
- 命运牌列表
- 命运牌编辑
- 图片绑定
- 未完成检测

如果以后你说：
- “命运牌卡片样式 / 字段 / 编辑器改一下”
- “增加新属性”
- “修改保存逻辑”

优先看这里。

---

### 7. 功能牌页
可搜索：
- `function renderCards`
- `function funcItem`
- `function openFuncEditor`
- `function funcEditorHtml`
- `function changeFuncType`
- `function addEffectRow`
- `function setEffectKey`
- `function setEffectParam`
- `async function saveFuncEditor`
- `async function saveFuncCards`
- `async function deleteFuncCard`
- `async function batchAddCards`
- `async function uploadFuncImages`
- `async function deleteFuncImage`

用途：
- 功能牌展示
- 功能牌编辑器
- 标签效果系统
- 图片资源处理

如果以后你说：
- “加一个新效果”
- “改某种卡牌字段”
- “批量导入改格式”
- “图片绑定方式调整”

优先看这里。

---

### 8. 统计页
可搜索：
- `function renderStats`
- `function buildFuncRarityDistribution`
- `function buildFuncTypeDistribution`

用途：
- 群组统计
- 持牌排行
- 卡池统计
- 稀有度分布

如果以后你说：
- “统计项增加一个”
- “图表显示改一下”
- “排行规则调整”

优先看这里。

---

### 9. 公共资源与弹窗
可搜索：
- `function openDialog`
- `function closeDialog`
- `function pickFile`
- `async function uploadImages`
- `async function deleteAsset`
- `async function refreshCardAssets`

用途：
- 弹窗
- 资源上传
- 资源删除
- 图片选择

---

### 10. 启动与事件绑定
可搜索：
- `function bindEvents`
- `async function bootstrapWebUi`
- `window.__startWebUi`

用途：
- 页面初始化
- DOM 事件绑定
- 启动入口

如果以后你说：
- “页面初始加载逻辑改一下”
- “增加初始化动作”
- “某个按钮没绑定”

优先看这里。

---

## 后续修改建议

以后如果你让我改动，我会优先按下面方式定位：

- **改结构 / 样式 / 逻辑 / 本地预览** → `app.html`
- **改服务端入口返回** → `server.py`

---

## 当前稳定策略

当前采用**单文件维护优先**策略：

1. `app.html` 是唯一主维护文件
2. 直接双击 `app.html` 即可本地预览
3. `app.html` 内已带 file 模式 mock，可脱离后端查看完整页面
4. 服务端仍可继续返回 `app.html`

---

当前阶段，先保证：
- 单文件维护
- 本地可直接预览
- 编码正常
- 入口稳定
- 功能不变
