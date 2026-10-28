# 卡片类型

所有类型共有两个可选字段:`Source`(出处,显示在背面底部)和各自的解释字段(`Extra` / `Explanation`)。解释字段很重要——背面只给答案不给"为什么",复习时就只能死记。

| type | 名称 | 必填字段 | 可选字段 | 每个 note 生成几张卡 |
|---|---|---|---|---|
| `basic` | 翻转卡 | Front, Back | Extra, Source | 1 |
| `reversed` | 双向卡 | Front, Back | Extra, Source | 2(正向 + 反向) |
| `cloze` | 填空卡 | Text | Extra, Source | 每个 cN 编号一张 |
| `mcq` | 选择题 | Question, Options, Answer | Explanation, Source | 1 |
| `truefalse` | 判断题 | Statement, Answer | Explanation, Source | 1 |
| `typein` | 输入答案卡 | Front, Answer | Extra, Source | 1 |

## 通用原则(来自间隔重复的经验)

- **最小信息原则**:一张卡只问一件事。"列出 TCP 三次握手的过程"应拆成三张填空或三张问答。
- **问题要唯一指向答案**:"线粒体的功能是?"可能有多个正确回答;"细胞有氧呼吸的主要场所是?"只有一个。
- **加上下文线索**:同一牌组里有多个相似主题时,用小标签或前缀(如"【有机化学】")区分,否则会出现"这问的是哪个?"的干扰。
- **不要照抄原文长句**:改写为问句,保留关键词。
- **答案短,解释长**:Back/Answer 放核心答案,Extra/Explanation 放推理、例子、记忆技巧。

## basic — 翻转卡

```yaml
- id: k012-basic
  type: basic
  fields:
    Front: HTTP 状态码 <code>304</code> 表示什么?
    Back: Not Modified(资源未修改,可使用缓存)
    Extra: 配合 <code>If-None-Match</code> / <code>If-Modified-Since</code> 请求头使用。
```

## reversed — 双向卡

适合两侧都需要主动回忆的配对:外语词 ↔ 释义、国家 ↔ 首都、缩写 ↔ 全称。如果反向问题不唯一(比如"动力工厂 → 线粒体"可以,但"线粒体 → ?"答案太发散),就用 basic 而不是 reversed。

## cloze — 填空卡

语法:`{{c1::答案}}` 或带提示 `{{c1::答案::提示}}`。相同编号的空在同一张卡里一起挖掉,不同编号生成不同的卡。

```yaml
- id: k020-cloze
  type: cloze
  fields:
    Text: 光合作用的光反应发生在{{c1::类囊体薄膜}}上,暗反应发生在{{c2::叶绿体基质}}中。
    Extra: 光反应产生 ATP 和 NADPH 供暗反应使用。
```

挖空要挖**关键词**而不是虚词;一张卡的上下文要足以唯一确定答案;一段文字里空不要超过 3–4 个编号,否则拆开。列举类("三个特点是 A、B、C")用同一编号挖整组会太难,用不同编号更好。

## mcq — 选择题

- `Options`:YAML 列表,每项一个选项(HTML 可用)。构建时转为 Anki 字段中以 `<br>` 分隔的文本,所以用户以后在 Anki 编辑器里一行一个选项即可修改。
- `Answer`:正确选项的字母,多选用逗号分隔,如 `B` 或 `A,C`。多选题在卡面上会自动提示"选择所有正确项"。
- **写进 `cards.yaml` 时就要让正确答案的位置分散**(A/B/C/D 大致均匀)。最自然的写法是把正确答案先写在第一个,但那样整套题的答案全是 A,学习者很快就会靠位置猜答案。`build.py` 发现某个字母占单选题答案一半以上时会给出警告。
- 可选 `Shuffle: true`:每次复习打乱选项顺序(防止记住位置而不是内容)。它是锦上添花,不能代替上一条:打乱靠卡片里的 JavaScript,在禁用脚本的客户端上会失效,这时显示的就是 `cards.yaml` 里的原始顺序。选项含"以上都对"之类依赖位置的内容时不要打乱。

```yaml
- id: k001-mcq
  type: mcq
  fields:
    Question: 被称为"细胞的动力工厂"的细胞器是?
    Options: [叶绿体, 线粒体, 核糖体, 高尔基体]
    Answer: B
    Explanation: 线粒体是有氧呼吸的主要场所。叶绿体是光合作用场所;核糖体合成蛋白质。
```

**干扰项的质量决定了选择题的价值。** 好的干扰项来自知识点的 `confusables`、同一主题下的其他概念、常见错误答案;每个干扰项都应该"对某个半懂的人看起来是对的"。避免:明显荒谬的选项、长度明显不同于正确答案、"以上都不对"之类的偷懒选项。在 `Explanation` 中简要说明干扰项为什么错——这是选择题相对于翻转卡最大的增益。选项一般 3–5 个。

## truefalse — 判断题

- `Answer`:`true` / `false`(也接受 对/错、T/F)。
- 判断题容易"送分",所以 **错误陈述要来自真实的误解**(知识点的 `misconceptions`),并且错得具体:改一个数字、换一个主语、把"通常"改成"总是"。对与错的数量大致平衡。
- `Explanation` 里对错误陈述给出正确说法。

```yaml
- id: k001-tf
  type: truefalse
  fields:
    Statement: 所有细胞都含有线粒体。
    Answer: false
    Explanation: 原核细胞(如细菌)没有线粒体;哺乳动物成熟红细胞也没有。
```

## typein — 输入答案卡

使用 Anki 原生的 `{{type:Answer}}`,复习时输入,翻面后逐字比较。适合拼写、单词、短公式、命令名。`Answer` 必须短而唯一(不能有 HTML 格式,不能有多种合理写法),否则比较结果没有意义。

```yaml
- id: k030-type
  type: typein
  fields:
    Front: Linux 中查看当前目录的命令
    Answer: pwd
    Extra: print working directory
```

## 题型转换

用户要求"把 X 换成 Y"时,**从 `knowledge.yaml` 重新生成**,而不是从旧卡片字段机械转换——比如 basic → mcq 需要干扰项,这只有回到知识点(和它的 `confusables`)才能出好。新卡用新 `id`(`<point>-<type>`,同一知识点同类型多张时加序号 `k001-mcq2`)。

是否保留旧卡由用户决定:
- 保留:旧卡继续在 `cards.yaml` 里,两种题型并存。
- 移除:从 `cards.yaml` 删除。但已经导入 Anki 的旧卡**不会因此消失**——告诉用户在 Anki 浏览器里搜索 `tag:ankiskill::type::basic` 之类的标签批量删除(构建脚本会自动给每张卡打上 `ankiskill::type::<类型>` 标签,正是为此准备的)。
