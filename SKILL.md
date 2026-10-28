---
name: anki-deck-builder
description: 把任何学习材料(PDF、Word/docx、PPT/pptx、txt/markdown、网页链接、YouTube/B站视频、本地音视频、字幕、图片、epub)转化为可直接导入 Anki 的 .apkg 卡包,支持翻转卡、双向卡、填空卡(cloze)、选择题(单选/多选)、判断题、输入答案卡,并带有精心设计、适配夜间模式和手机端的卡片样式。整个设计过程(知识点、卡片、样式、决策日志)保存在一个项目文件夹里,之后可以随时换风格、换卡片类型、增删卡片而不丢失 Anki 复习进度。只要用户提到 Anki、记忆卡、闪卡、flashcard、间隔重复、"把这份资料做成卡片/题目来背",或想修改之前生成的 Anki 卡包的样式/题型,就使用这个 skill——即使用户没有明确说"Anki"。
---

# Anki Deck Builder

把材料 → 知识点 → 卡片 → 样式 → `.apkg`,并且每一层都落盘,方便以后只改其中一层。

## 为什么要分层

用户以后最常见的诉求是"换个风格"或"把这些翻转卡改成选择题"。如果卡片是一次性从材料直接生成的,任何修改都要从头再来,还会产生新的 note,导致 Anki 里的复习记录丢失。所以本 skill 把产物拆成四层,每层独立可改:

| 层 | 文件 | 改它意味着 |
|---|---|---|
| 来源 | `sources/*.md`, `media/` | 加新材料 |
| 知识点(与题型无关) | `knowledge.yaml` | 改"学什么" |
| 卡片(题型 + 字段) | `cards.yaml` | 改"怎么考" |
| 样式 | `style/theme.css`, `style/overrides.css`, `style/brief.md`, 可选 `style/templates/` | 改"长什么样" |

再加上 `DESIGN_LOG.md`(人写的决策日志)和 `build/history.jsonl`(构建脚本自动追加)记录过程。项目格式的完整说明见 `references/project-format.md`。

所有脚本都在本 skill 的 `scripts/` 目录,下文用 `$SKILL` 指代本 skill 的根目录。依赖:`pip install genanki pyyaml`(其他依赖按材料类型可选,脚本缺什么会提示)。

## 工作流程

### 1. 弄清需求(只问缺的)

需要的信息:材料是什么、想要哪些卡片类型、风格偏好、卡片语言、牌组名称、粒度(大约多少张/覆盖多细)。用户已经说了的不要再问。能合理推断的直接给出建议并说明,比如:

- 定义/术语类材料 → 推荐翻转卡 + 填空卡
- 有易混概念、需要辨析 → 选择题(干扰项要来自易混概念)
- 有常见误解/事实陈述 → 判断题
- 拼写、公式、代码、外语单词 → 输入答案卡
- 语言学习词汇 → 双向卡

如果有提问工具(如 AskUserQuestion),用它一次性问完,每个问题给出带"(推荐)"的选项。卡片类型可多选。各类型的详细说明和写法见 `references/card-types.md`。

### 2. 建项目

```bash
python $SKILL/scripts/project.py init <项目目录> --name "牌组名" --theme minimal --lang zh
python $SKILL/scripts/project.py list-themes   # 查看内置主题
```

项目目录默认放在用户当前工作目录下,以牌组名命名。`init` 会生成稳定的 `uid`——它决定了所有 note 的 GUID 和 note type ID,**永远不要修改它**,否则重新导入时 Anki 会把所有卡当成新卡。

### 3. 导入材料

```bash
python $SKILL/scripts/ingest.py <文件或URL> [更多...] --project <项目目录>
```

它会把每份材料转成 `sources/<名字>.md`,图片提取到 `media/`。支持的格式和失败时的替代方案(例如视频没有字幕时用 whisper 转写、网页抓取失败时改用 WebFetch、扫描版 PDF 用视觉读取)见 `references/ingestion.md`。图片类材料直接用视觉能力读取并手写成 markdown。

导入后**读一遍**生成的 markdown——提取质量参差不齐(页眉页脚、乱序的 PPT 文本框、字幕口语化),后续步骤依赖你理解内容,而不是机械切分。

### 4. 提炼知识点 → `knowledge.yaml`

这是整个设计中最重要的一步。知识点是与题型无关的、原子化的事实/概念/关系,每个带稳定 `id` 和来源位置:

```yaml
points:
  - id: k001
    topic: 细胞结构
    fact: 线粒体是细胞进行有氧呼吸的主要场所,被称为"细胞的动力工厂"。
    detail: 具有双层膜,内膜向内折叠形成嵴,增大了酶附着面积。
    confusables: [叶绿体, 核糖体]      # 易混点 → 选择题干扰项来源
    misconceptions: ["所有细胞都有线粒体(原核细胞没有)"]  # → 判断题来源
    source: sources/biology-ch3.md#3.2
```

原则:一个点只讲一件事;保留 `detail` 供卡片背面解释用;主动记录 `confusables` 和 `misconceptions`,因为以后转换成选择/判断题时需要它们,而那时可能已经没人记得原文了。材料很长时按章节分批处理。`topic` 会自动成为卡片标签;想要子牌组则在卡片上写 `deck` 字段。

### 5. 生成卡片 → `cards.yaml`

为每个知识点按用户选择的题型生成卡片,一个知识点可以有多张不同题型的卡。格式:

```yaml
cards:
  - id: k001-basic          # 稳定 ID,决定 GUID。改内容不改 ID → Anki 里更新而非新增
    point: k001
    type: basic
    deck: 细胞结构           # 可选,成为 "牌组名::细胞结构" 子牌组
    tags: [ch3]
    fields:
      Front: 被称为"细胞的动力工厂"的细胞器是?
      Back: 线粒体
      Extra: 双层膜,内膜折叠成<b>嵴</b>。
      Source: 生物必修一 3.2
```

每种类型的字段、写法要点(选择题干扰项怎么出、填空挖哪里、判断题怎么避免"送分")见 `references/card-types.md`,生成前先读它。`examples/cell-biology/` 是一个覆盖全部六种题型的完整示例项目,拿不准格式时参考它。字段内容是 HTML,可以用 `<b>`、`<code>`、`<ul>`、`<img src="文件名.png">`(图片放在项目 `media/`)、MathJax `\( ... \)`。

### 6. 设计样式

三种来源,按用户意愿选择:

1. **内置主题**:`project.py set-theme <项目> <主题名>`。
2. **用户描述的风格**("像 Notion 那样""手账风""暗黑赛博朋克"):基于最接近的内置主题,改写 `style/theme.css` 里的设计变量;结构性调整写进 `style/overrides.css`。
3. **外部设计类 skill**:把 `references/styling.md` 中的"设计变量契约"和 Anki 渲染限制交给那个 skill,让它产出满足契约的 CSS,写入 `style/theme.css`。

无论哪种,都把用户的原话和你的设计意图写进 `style/brief.md`——以后任何人(或另一个设计 skill)都可以根据 brief 重新生成样式。

Anki 的渲染环境有很多坑(桌面端/AnkiDroid/iOS 夜间模式类名不同、网络字体离线不可用、桌面端 webview 复用导致脚本重复执行……)。改模板或写大量自定义 CSS 前,**务必读 `references/styling.md`**。

### 7. 构建与预览

```bash
python $SKILL/scripts/build.py <项目目录>
```

它会校验 `cards.yaml`(必填字段、cloze 语法、选择题答案越界、ID 重复)、生成 `build/<牌组名>.apkg` 和 `build/preview.html`,并在 `build/history.jsonl` 追加一条构建记录。校验报错就修 `cards.yaml` 再构建;出现警告(比如选择题正确答案集中在同一个字母、判断题对错失衡)也要修掉,它们不会阻止构建,却会让卡片能被"猜"中。

用浏览器打开 `preview.html` 自查(有日/夜间切换,正面/背面并排,选择题判断题可点击),然后把它给用户看。预览是近似渲染,最终以 Anki 为准,但样式问题在预览里基本都能发现。

### 8. 记录决策

在 `DESIGN_LOG.md` 追加一条:日期、做了什么、为什么(用户的要求、你的取舍、放弃的方案)。这是给以后修改的人看的,写"为什么"比写"做了什么"更有价值——"做了什么"在文件和 history.jsonl 里已经有了。

### 9. 交付

告诉用户 `.apkg` 的位置和导入方法(Anki → 文件 → 导入),说明卡片数量与题型分布,并提示:以后想换风格或题型,只要带着这个项目文件夹回来即可。

## 后续修改

先读项目的 `DESIGN_LOG.md` 和 `style/brief.md` 了解之前的决策,然后:

- **换风格**:只改 `style/`,重新 build。告诉用户导入时在导入选项里把"更新笔记类型"设为"如果更新则更新"(Anki 23.10+),复习进度不受影响。如果用户装了 AnkiConnect 插件,可以直接推送样式而无需重新导入:`python $SKILL/scripts/anki_connect.py push-style <项目>`。
- **改内容**:改 `cards.yaml` 中的字段,**保持 `id` 不变**,重新 build 导入即覆盖更新。
- **换题型/加题型**:从 `knowledge.yaml` 重新生成对应卡片(而不是从旧卡片硬转),用新 `id`(如 `k001-mcq`)。要说明:改变已有卡片的题型等于在 Anki 里新建卡片,原卡的复习记录不会迁移;如果用户想去掉旧卡,告诉他们在 Anki 中用 `tag:` 或卡片浏览器删除,脚本不会替用户删除 Anki 里的数据。
- **加材料**:ingest → 追加知识点(继续编号)→ 追加卡片。

每次修改都追加 `DESIGN_LOG.md`。
