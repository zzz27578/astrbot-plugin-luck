# WebUI 前端架构说明

## 当前运行入口

### 主入口
- `webui/static/app.html`
- 加载：
  - `/static/styles.css`
  - `/static/js/main.js`

### 兼容入口
- `webui/static/index.html`
- 仅作为历史兼容壳保留
- 当前也直接加载 `/static/js/main.js`
- 历史内联内容仅作文本保留，不再参与执行

### 服务端入口
- `webui/server.py`
- `serve_index()` 当前优先返回：
  1. `app.html`
  2. `index.html`

---

## 文件职责

### `app.html`
负责页面骨架：
- 侧边栏
- 顶部 Hero
- 六个页面容器
- 弹窗容器
- Toast 容器

适合修改：
- 页面结构
- 区域增减
- 新增挂载点
- 脚本 / 样式引用

---

### `styles.css`
负责所有视觉样式：
- 布局
- 组件样式
- 页面样式
- 动画
- 响应式规则

适合修改：
- 颜色
- 尺寸
- 排版
- 卡片表现
- 响应式布局

---

### `js/main.js`
负责所有前端逻辑：
- 全局状态
- API 请求
- 页面渲染
- 表单交互
- 图片上传删除
- 弹窗逻辑
- 事件绑定
- 启动逻辑

适合修改：
- 功能逻辑
- 接口调用
- 页面数据渲染
- 交互行为

---

### `app.js`
兼容加载器：
- 不再承载业务逻辑
- 仅负责处理旧引用 `/static/app.js` 时，转向 `js/main.js`

用途：
- 防止旧缓存 / 旧入口 / 误引用继续加载历史乱码逻辑

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

- **改结构** → `app.html`
- **改样式** → `styles.css`
- **改逻辑** → `js/main.js`
- **改入口返回** → `server.py`

---

## 当前稳定策略

为避免再次出现乱码或历史文件污染：

1. 业务逻辑只维护在 `js/main.js`
2. `app.js` 只保留兼容加载能力
3. `index.html` 只保留兼容壳，不再维护内联逻辑
4. 默认以 `app.html` 为主入口

---

## 如果未来继续拆分

下一步推荐按页面拆 JS：

- `js/core.js`
- `js/pages/overview.js`
- `js/pages/runtime.js`
- `js/pages/signin.js`
- `js/pages/fate.js`
- `js/pages/cards.js`
- `js/pages/stats.js`

但当前阶段，先保证：
- 编码正常
- 入口稳定
- 功能不变
- 定位清晰

这四点已经是第一优先级。