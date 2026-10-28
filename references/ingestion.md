# 材料导入

`scripts/ingest.py` 把各类材料统一转为 `sources/<名字>.md`(带 YAML front matter 记录来源),图片提取到 `media/`。缺少可选依赖时脚本会打印安装命令并跳过该文件,不会中断其他文件。

| 材料 | 方式 | 依赖 | 失败时的替代方案 |
|---|---|---|---|
| `.txt` `.md` | 直接复制 | — | — |
| `.pdf` | 逐页提取文字,标注页码 `## 第 N 页`;尝试提取图片 | `pypdf`(图片需 `pymupdf`) | 输出几乎为空 = 扫描版。用 pdf skill 的 OCR,或把页面转成图片后用视觉读取 |
| `.docx` | 保留标题层级、列表、表格;提取图片 | `python-docx` | 有 pandoc 可用 `pandoc x.docx -t gfm` |
| `.pptx` | 每页一节:标题、正文、表格、**演讲者备注**;提取图片 | `python-pptx` | 文本框顺序可能错乱,读 markdown 时按语义理顺 |
| `.html` / 网页 URL | 抓取 → 去掉导航/脚本 → 转 markdown | `beautifulsoup4`(可选 `trafilatura` 效果更好) | 需要登录或 JS 渲染的页面:改用 WebFetch 工具或浏览器工具读取,再手写进 `sources/` |
| `.epub` | 按章节解析 XHTML | `beautifulsoup4` | — |
| `.srt` `.vtt` | 去掉序号,合并为段落,每约 60 秒保留一个时间戳 `[mm:ss]` | — | — |
| YouTube / B 站等视频 URL | `yt-dlp` 下载字幕(人工字幕优先,其次自动字幕),不下载视频 | `yt-dlp` | 没有字幕:下载音频后走本地转写 |
| 本地音视频 `.mp4 .mkv .mov .webm .mp3 .m4a .wav` | `ffmpeg` 抽音轨 → `faster-whisper`(或 `openai-whisper`)转写,带时间戳 | `ffmpeg`, `faster-whisper` | 都没有:告诉用户需要安装哪个,或请用户提供字幕/讲稿 |
| 图片 `.png .jpg` 等 | 复制到 `media/`,生成占位 markdown | — | 用视觉能力读取图片内容,补全那份 markdown |

用法:

```bash
python $SKILL/scripts/ingest.py lecture.pptx notes.pdf https://example.com/article --project ./我的牌组
python $SKILL/scripts/ingest.py "https://www.youtube.com/watch?v=..." --project ./我的牌组 --lang zh
```

`--lang` 影响字幕语言优先级和 whisper 的语言参数。

## 导入后的处理

- **读一遍输出**。删掉页眉页脚、目录页、版权声明;PPT 的碎片文字按语义合并。可以直接编辑 `sources/*.md`。
- **视频转写**是口语,有重复和错别字(尤其专有名词)。提炼知识点时以语义为准,必要时向用户确认术语。保留时间戳:写进知识点的 `source`(如 `sources/lecture.md#12:30`),卡片的 `Source` 字段可以显示"视频 12:30",方便用户回看。
- **图片**:材料中的图表如果对理解关键(结构图、流程图),可以在卡片里直接引用 `media/` 中的文件。提取出来的图片文件名形如 `<来源名>_p3_1.png`。
- **很长的材料**(> 50 页或 > 1 小时视频):按章节分段提炼知识点,每段完成后再进入下一段,避免一次读太多导致遗漏后半部分。
- **版权**:材料只用于为用户本人制作学习卡片,不要把材料原文大段塞进卡片——卡片应是改写后的问答。
