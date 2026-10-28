# 项目文件夹格式

```
<项目>/
├── project.yaml        # 元数据:名称、uid、语言、主题、题型
├── DESIGN_LOG.md       # 决策日志(人写,追加)
├── sources/            # ingest.py 输出的 markdown,每份材料一个
├── media/              # 图片、音频、字体;卡片字段用文件名直接引用
├── knowledge.yaml      # 知识点(与题型无关)
├── cards.yaml          # 卡片;也可以拆成 cards/*.yaml 多个文件,构建时全部读取
├── style/
│   ├── brief.md        # 风格需求与设计意图
│   ├── theme.css       # 设计变量
│   ├── overrides.css   # 可选,结构性调整
│   └── templates/      # 可选,项目级模板覆盖
└── build/
    ├── <牌组名>.apkg
    ├── preview.html
    └── history.jsonl   # 每次构建自动追加
```

## project.yaml

```yaml
name: 高中生物必修一          # 顶层牌组名
uid: 7f3a9c1e2b4d             # 生成 GUID 和 note type ID 的种子 —— 永远不要改
lang: zh                       # 卡面界面文字语言(zh / en)
theme: minimal                 # 当前 theme.css 的来源主题(仅作记录)
card_types: [basic, cloze, mcq]# 用户选择的题型(仅作记录,实际以 cards.yaml 为准)
model_prefix: ""               # 可选。note type 名称前缀,默认用牌组名
sources:                       # ingest.py 自动维护
  - path: sources/ch3.md
    origin: F:/books/biology.pdf
    added: 2026-10-28
```

## ID 与 Anki 的对应关系

| 本项目 | Anki | 规则 |
|---|---|---|
| `uid` + 题型 | note type ID | 同一项目同一题型永远是同一个 note type,所以换样式只更新它而不新建 |
| `uid` + 卡片 `id` | note GUID | 卡片 `id` 不变 → 重新导入时更新已有 note,保留复习记录 |
| `name` + 卡片 `deck` | 牌组 / 子牌组 | `deck` 可以写 `第三章::细胞器` 形成多级 |

note type 名称为 `<牌组名> · <题型中文名>`,例如 `高中生物必修一 · 选择题`,方便用户在 Anki 中识别。

## 自动标签

每张卡构建时会自动加上:
- `ankiskill::type::<type>` — 按题型批量查找/删除
- `ankiskill::point::<point>` — 同一知识点的所有卡
- `topic` 的值(知识点的 topic,空格替换为 `_`)

加上 `cards.yaml` 中手写的 `tags`。

## DESIGN_LOG.md 写法

```markdown
## 2026-10-28 初版
- 材料:biology.pdf 第 3 章(42 页)
- 题型:翻转 + 填空 + 选择。用户希望"考前刷题",所以选择题占比较高(约 40%)。
- 风格:minimal。用户没有偏好,选最中性的,方便以后改。
- 取舍:3.4 节实验步骤没做卡片——是流程性内容,用户说只要概念。

## 2026-11-02 换风格
- 用户觉得太素,想要"手账风"。基于 paper 主题,强调色改莫兰迪绿,见 style/brief.md。
```
