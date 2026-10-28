# 样式系统

## 目录
1. 样式如何组装
2. 设计变量契约(给外部设计 skill 的接口)
3. 组件类名
4. Anki 渲染环境的限制与坑
5. 按用户描述定制风格的方法
6. 自定义模板

## 1. 样式如何组装

构建时,每个 note type 的 CSS = 以下文件按顺序拼接:

1. `$SKILL/assets/base.css` — 所有组件的结构样式,只引用变量,不写死颜色/字体
2. `<项目>/style/theme.css` — 设计变量的取值(由 `set-theme` 从 `$SKILL/assets/themes/` 复制而来,之后可自由修改)
3. `<项目>/style/overrides.css` — 可选,项目特有的结构性调整

所有题型共享同一份 CSS,所以风格统一。只想改颜色/字体/圆角 → 只改 theme.css;想改布局 → overrides.css;想改 HTML 结构 → 见第 6 节。

## 2. 设计变量契约

theme.css 必须在 `.card` 上定义下列变量,并在夜间模式选择器上覆盖颜色类变量。外部设计 skill 只需要输出这样一份文件,就能给全部题型换装。

```css
.card {
  /* 颜色 */
  --bg:            #f7f7f5;  /* 整个卡片背景 */
  --surface:       #ffffff;  /* 内容面板 */
  --surface-2:     #f0f0ee;  /* 次级面板:选项、解释框 */
  --text:          #1f2328;
  --text-muted:    #6b7280;
  --border:        #e5e7eb;
  --accent:        #2563eb;  /* 强调:标题装饰、选中态、链接 */
  --accent-soft:   #dbeafe;  /* 强调色的浅底 */
  --accent-contrast:#ffffff; /* 放在 accent 上的文字 */
  --correct:       #15803d;
  --correct-soft:  #dcfce7;
  --wrong:         #b91c1c;
  --wrong-soft:    #fee2e2;
  --cloze:         #2563eb;  /* 填空答案文字 */
  --cloze-soft:    #dbeafe;  /* 填空背景 */
  /* 字体 */
  --font-body:     -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-heading:  var(--font-body);
  --font-mono:     "JetBrains Mono", Consolas, monospace;
  --font-size:     20px;     /* 正文基础字号,手机端会自动缩小 */
  --line-height:   1.6;
  /* 形状 */
  --radius:        14px;
  --radius-sm:     8px;
  --shadow:        0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.06);
  --max-width:     680px;
  --gap:           16px;
}

.card.nightMode, .nightMode .card, .card.night_mode, .night_mode .card {
  /* 只覆盖颜色类变量 */
}
```

设计时检查:正文对比度 ≥ 4.5:1(日夜两套都要);`--correct`/`--wrong` 不能只靠颜色区分(base.css 已加 ✓/✗ 符号);夜间背景不要用纯黑 `#000`(OLED 上拖影且刺眼),用 `#16171b` 一类的深灰。

## 3. 组件类名(base.css 中定义)

| 类名 | 用途 |
|---|---|
| `.ak` | 每张卡的根容器,`.ak-basic` / `.ak-cloze` / `.ak-mcq` / `.ak-tf` / `.ak-type` 区分题型 |
| `.ak-kind` | 左上角题型小标签 |
| `.ak-q` | 问题区 |
| `.ak-a` | 答案区 |
| `.ak-divider` | 问答分隔线 |
| `.ak-extra` | 解释框 |
| `.ak-source` | 出处脚注 |
| `.ak-opts` / `.ak-opt` | 选项列表 / 单个选项;状态类 `.is-selected` `.is-correct` `.is-wrong` `.is-missed` |
| `.ak-letter` | 选项字母圆标 |
| `.ak-tf-btns` / `.ak-tf-btn` | 判断题按钮 |
| `.ak-verdict` | 背面的"回答正确/错误"横幅,`.is-good` / `.is-bad` |
| `.ak-hint` | 小号提示文字 |
| `.cloze` / `.cloze-inactive` | Anki 原生填空类名 |
| `#typeans`, `.typeGood`, `.typeBad`, `.typeMissed` | Anki 原生输入比对类名 |

## 4. Anki 渲染环境的限制与坑

这些是实践中真实踩过的坑,改模板或 CSS 时逐条对照:

- **四个客户端**:桌面版(Qt WebEngine / Chromium)、AnkiDroid(Android WebView)、AnkiMobile(iOS WKWebView)、AnkiWeb(浏览器)。只用主流 CSS(flex、grid、变量、`clamp()` 都可以),不要用太新的特性(如 `:has()` 在旧 Android WebView 上不可用)。
- **夜间模式类名不统一**:桌面/AnkiMobile 给 `.card` 和 body 加 `nightMode`,AnkiDroid 旧版用 `night_mode`。四个选择器都要写(见契约)。桌面端夜间模式下 Anki 还会对图片做反色处理,不想反色的图片加 `class="ak-noinvert"`(base.css 已处理)。
- **变量要定义在 `.card` 上**,不能只写在 `:root`:有些客户端的默认样式会在 `.card` 上设置颜色,导致覆盖失败。
- **网络字体**:`@import` Google Fonts 在离线和部分客户端上会失败,并拖慢首屏。要用特殊字体,把 `.woff2` 文件放进项目 `media/`,文件名以下划线开头(如 `_LXGWWenKai.woff2`,下划线前缀防止 Anki 的"检查媒体"把它当成未使用文件删除),再用 `@font-face { src: url("_LXGWWenKai.woff2"); }` 引用。中文字体很大,优先用子集化版本或系统字体栈。
- **脚本会被重复执行**:桌面端复用同一个 webview 显示所有卡片,顶层的 `const`/`let` 在第二张卡就会抛"重复声明"错误。所有脚本必须包在 IIFE `(function(){ ... })();` 里。
- **正面和背面之间传递状态**:用 `sessionStorage`,key 里带上题目内容的哈希避免串题;读取后清除。必须有降级:读不到时背面仍然正常显示正确答案。
- **不能依赖外部 JS 库**(离线)。保持脚本小而无依赖。
- **字段里的 HTML**:Anki 编辑器会把换行存为 `<br>` 或 `<div>`,所以解析选项时这三种分隔都要支持(模板已处理)。
- **手机端**:不要在 `.card` 上设固定宽度;最小点击区域 44px;用 `@media (max-width: 480px)` 缩小字号和内边距。
- **`{{type:...}}`** 的比对区由 Anki 生成,只能通过 `#typeans` 等类名改样式,不能改结构。
- **MathJax**:`\( \)` 和 `\[ \]` 由 Anki 渲染,不需要也不应该引入 MathJax 脚本。

## 5. 按用户描述定制风格

1. 把用户的描述翻译成具体的设计决策,写进 `style/brief.md`,例如"手账风" → 暖米色纸张底 `#faf6ee`、手写感标题字体、虚线分隔、低饱和莫兰迪强调色、略大圆角、轻微纸张阴影。
2. 选最接近的内置主题作为起点(`project.py list-themes` 列出各主题的说明),改 `style/theme.css` 中的变量值。
3. 变量覆盖不了的(比如给问题区加左侧色条、换分隔线样式)写进 `style/overrides.css`,只针对第 3 节的类名写选择器。
4. build 后打开 `preview.html`,日/夜两种模式都检查,再给用户看。用户的反馈和你的调整也记进 brief。

### 接入外部设计 skill

如果用户指定了某个设计类 skill(或说"用我的设计系统"):调用它,把本文件第 2、3、4 节作为约束提供给它,要求它的产出是一份满足变量契约的 `theme.css`(必要时加一份 `overrides.css`)。拿到后放进项目 `style/`,build 并检查预览。不要让外部 skill 直接改 `assets/base.css` 或模板——那会影响所有项目;项目内的定制始终放在项目的 `style/` 里。

## 6. 自定义模板

需要改 HTML 结构时(比如在翻转卡正面加一张固定的图),把 `$SKILL/assets/note_types/<type>/` 整个目录复制到 `<项目>/style/templates/<type>/` 再修改。构建时项目内的模板优先。注意:

- `model.json` 里的 `fields` 列表决定 note type 的字段。**修改字段(增删、改名)会改变 note type 的结构**,用户重新导入时需要在 Anki 导入选项里勾选"合并笔记类型",并且要提醒用户。只改模板 HTML/CSS 不影响结构,可以放心。
- 模板中的 `[[t:key]]` 是界面文字占位符,构建时按项目语言(`project.yaml` 的 `lang`)替换,词表在 `$SKILL/assets/i18n.json`。
