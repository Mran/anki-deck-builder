#!/usr/bin/env python3
"""Validate cards, build build/<name>.apkg and build/preview.html, append build/history.jsonl.

  build.py <project_dir> [--no-preview] [--preview-only] [--check]
"""
import argparse
import collections
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TYPES, Project, field_value, stable_int, validate  # noqa: E402

SAFE_NAME = re.compile(r'[\\/:*?"<>|]+')


def collect(project):
    """Load + validate cards. Returns (notes, errors) where notes are normalized dicts."""
    points = project.points = project.load_points()
    cards = project.load_cards()
    specs = {}
    notes, errors, seen = [], [], {}
    for idx, c in enumerate(cards):
        where = f"{c.get('_file')} 第 {idx + 1} 张 (id={c.get('id')!r})"
        cid, ctype = c.get("id"), c.get("type")
        if not cid:
            errors.append(f"{where}: 缺少 id")
            continue
        if cid in seen:
            errors.append(f"{where}: id 与 {seen[cid]} 重复")
            continue
        seen[cid] = where
        if ctype not in TYPES:
            errors.append(f"{where}: 未知题型 {ctype!r},可用 {TYPES}")
            continue
        if ctype not in specs:
            specs[ctype] = project.note_type(ctype)
        nt = specs[ctype]
        errs = validate(c, nt["fields"])
        errors += [f"{where}: {e}" for e in errs]
        if errs:
            continue
        f = c.get("fields") or {}
        values = {name: field_value(ctype, name, f.get(name)) for name in nt["fields"]}
        point = points.get(c.get("point")) if c.get("point") else None
        tags = [str(t) for t in (c.get("tags") or [])]
        tags.append(f"ankiskill::type::{ctype}")
        if c.get("point"):
            tags.append(f"ankiskill::point::{c['point']}")
        if point and point.get("topic"):
            tags.append(str(point["topic"]))
        tags = list(dict.fromkeys(re.sub(r"\s+", "_", t.strip()) for t in tags if t.strip()))
        deck = project.name + (f"::{c['deck']}" if c.get("deck") else "")
        notes.append({"id": cid, "type": ctype, "values": values, "tags": tags, "deck": deck})
    if not cards:
        errors.append("cards.yaml 中没有卡片")
    return notes, specs, errors


def warnings(notes):
    """Quality problems that don't block the build but should be fixed."""
    out = []
    singles = [n["values"]["Answer"].strip().upper() for n in notes
               if n["type"] == "mcq" and len(re.findall(r"[A-Z]|\d+", n["values"]["Answer"].upper())) == 1]
    if len(singles) >= 4:
        letter, count = collections.Counter(singles).most_common(1)[0]
        if count / len(singles) > 0.5:
            out.append(f"单选题中 {count}/{len(singles)} 题的答案都是 {letter}:学习者会靠位置猜答案,"
                       f"请在 cards.yaml 中调整选项顺序,让正确答案分散在各个位置(Shuffle 依赖 JS,不能代替)")
    tfs = [n["values"]["Answer"].strip().lower() for n in notes if n["type"] == "truefalse"]
    if len(tfs) >= 6:
        share = sum(v == "true" for v in tfs) / len(tfs)
        if not 0.3 <= share <= 0.7:
            out.append(f"判断题中正确陈述占 {share:.0%},对错比例失衡,学习者容易猜中")
    return out


def media_refs(notes, css):
    refs = set()
    for n in notes:
        for v in n["values"].values():
            refs.update(re.findall(r'src=["\']([^"\']+)["\']', v))
            refs.update(re.findall(r"\[sound:([^\]]+)\]", v))
    refs.update(re.findall(r'url\(["\']?([^"\')]+)["\']?\)', css))
    return {r for r in refs if not re.match(r"^(https?:|data:|//)", r)}


def build_apkg(project, notes, specs, out_path):
    import genanki

    models = {}
    for ctype, nt in specs.items():
        models[ctype] = genanki.Model(
            nt["id"], nt["name"],
            fields=[{"name": f} for f in nt["fields"]],
            templates=nt["templates"], css=nt["css"],
            model_type=genanki.Model.CLOZE if nt["cloze"] else genanki.Model.FRONT_BACK,
        )
    decks = {}
    for n in notes:
        if n["deck"] not in decks:
            decks[n["deck"]] = genanki.Deck(stable_int(project.uid, "deck", n["deck"]), n["deck"])
        note = genanki.Note(
            model=models[n["type"]],
            fields=[n["values"][f] for f in specs[n["type"]]["fields"]],
            tags=n["tags"],
            guid=genanki.guid_for(project.uid, n["id"]),
        )
        decks[n["deck"]].add_note(note)

    media_dir = project.root / "media"
    css = next(iter(specs.values()))["css"]
    files, missing = [], []
    for ref in sorted(media_refs(notes, css)):
        p = media_dir / ref
        (files if p.exists() else missing).append(str(p))
    if media_dir.is_dir():  # 下划线开头的文件(字体等)总是打包
        files += [str(p) for p in media_dir.glob("_*") if str(p) not in files]
    pkg = genanki.Package(list(decks.values()))
    pkg.media_files = files
    pkg.write_to_file(str(out_path))
    return len(files), missing


# ---------------- preview ----------------

def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def render_cloze(text, ord_, side):
    def rep(m):
        n, ans, hint = int(m.group(1)), m.group(2), m.group(3)
        if n != ord_:
            return f'<span class="cloze-inactive">{ans}</span>'
        if side == "front":
            return f'<span class="cloze">[{hint or "..."}]</span>'
        return f'<span class="cloze">{ans}</span>'
    return re.sub(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", rep, text, flags=re.S)


def render(tpl, values, ord_, side):
    def section(m):
        has = strip_html(values.get(m.group(2).strip(), "")).strip() != "" or "<img" in values.get(m.group(2).strip(), "")
        return m.group(3) if has == (m.group(1) == "#") else ""
    prev = None
    while prev != tpl:
        prev = tpl
        tpl = re.sub(r"\{\{([#^])([^}]+)\}\}(.*?)\{\{/\2\}\}", section, tpl, flags=re.S)

    def field(m):
        parts = [p.strip() for p in m.group(1).split(":")]
        name, filters = parts[-1], parts[:-1]
        val = values.get(name, "")
        if "type" in filters:
            if side == "front":
                return '<input type="text" id="typeans" autocomplete="off">'
            return f'<code id="typeans"><span class="typeGood">{html.escape(strip_html(val))}</span></code>'
        if "cloze" in filters:
            val = render_cloze(val, ord_, side)
        if "text" in filters:
            val = html.escape(strip_html(val))
        return val
    return re.sub(r"\{\{([^#^/}][^}]*)\}\}", field, tpl)


FRAME = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><base href="{base}">
<style>{css}</style><style>html,body{{margin:0}}</style></head>
<body class="card card{ord}">{body}
<script>
(function(){{
  // 用 body 的内容高度而非 scrollHeight:后者不小于视口高度,配合 resize 会无限增高
  function h(){{ parent.postMessage({{akh: Math.ceil(document.body.getBoundingClientRect().height), id: "{fid}"}}, "*"); }}
  window.addEventListener("load", h); window.addEventListener("resize", h);
  document.addEventListener("click", function(){{ setTimeout(h, 30); }});
  window.addEventListener("message", function(e){{
    if (e.data && "night" in e.data) {{
      document.body.classList.toggle("nightMode", e.data.night);
      document.body.classList.toggle("night_mode", e.data.night);
      setTimeout(h, 30);
    }}
  }});
  setTimeout(h, 50); setTimeout(h, 400);
}})();
</script></body></html>"""

PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 预览</title>
<style>
:root {{ --bg:#f6f6f4; --fg:#1d1d1f; --muted:#6e6e73; --line:#e3e3e0; --chip:#ffffff; --on:#1d1d1f; --onfg:#fff; }}
body.dark {{ --bg:#111214; --fg:#ececee; --muted:#9a9aa2; --line:#2a2b30; --chip:#1b1c20; --on:#ececee; --onfg:#111; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
header {{ position:sticky; top:0; z-index:5; background:var(--bg); border-bottom:1px solid var(--line); padding:14px 20px; display:flex; flex-wrap:wrap; gap:10px 16px; align-items:center; }}
h1 {{ font-size:17px; margin:0; font-weight:650; }}
.stats {{ color:var(--muted); }}
.spacer {{ flex:1; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; }}
button, input {{ font:inherit; color:var(--fg); background:var(--chip); border:1px solid var(--line); border-radius:999px; padding:5px 12px; cursor:pointer; }}
input {{ border-radius:8px; cursor:text; width:180px; }}
button.on {{ background:var(--on); color:var(--onfg); border-color:var(--on); }}
main {{ padding:20px; max-width:1500px; margin:0 auto; }}
.row {{ margin-bottom:28px; }}
.meta {{ color:var(--muted); font-size:12px; margin:0 0 8px 2px; display:flex; flex-wrap:wrap; gap:4px 12px; }}
.meta b {{ color:var(--fg); font-weight:600; }}
.pair {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.side {{ font-size:11px; letter-spacing:.06em; color:var(--muted); margin:0 0 4px 4px; }}
iframe {{ width:100%; border:0; border-radius:12px; display:block; height:220px; background:transparent; }}
@media (max-width: 900px) {{ .pair {{ grid-template-columns:1fr; }} header {{ padding:12px 16px; }} main {{ padding:16px; }} }}
</style></head>
<body>
<header>
  <h1>{title}</h1><span class="stats">{stats}</span><span class="spacer"></span>
  <div class="chips" id="types">{type_buttons}</div>
  <input id="q" placeholder="搜索内容 / id / 标签">
  <button id="night">夜间模式</button>
</header>
<main>{rows}</main>
<script>
var night = false, active = "all";
window.addEventListener("message", function(e){{
  if (e.data && e.data.akh) {{ var f = document.getElementById(e.data.id); if (f) f.style.height = e.data.akh + "px"; }}
}});
document.getElementById("night").onclick = function(){{
  night = !night; this.classList.toggle("on", night); document.body.classList.toggle("dark", night);
  document.querySelectorAll("iframe").forEach(function(f){{ f.contentWindow.postMessage({{night: night}}, "*"); }});
}};
function filter(){{
  var q = document.getElementById("q").value.trim().toLowerCase();
  document.querySelectorAll(".row").forEach(function(r){{
    var ok = (active === "all" || r.dataset.type === active) && (!q || r.dataset.text.indexOf(q) >= 0);
    r.style.display = ok ? "" : "none";
  }});
}}
document.getElementById("q").oninput = filter;
document.querySelectorAll("#types button").forEach(function(b){{
  b.onclick = function(){{
    active = b.dataset.type;
    document.querySelectorAll("#types button").forEach(function(x){{ x.classList.toggle("on", x === b); }});
    filter();
  }};
}});
</script></body></html>"""


def build_preview(project, notes, specs, out_path):
    base = (project.root / "media").as_uri() + "/"
    rows, counter = [], 0
    for n in notes:
        nt = specs[n["type"]]
        if nt["cloze"]:
            ords = sorted({int(x) for x in re.findall(r"\{\{c(\d+)::", n["values"]["Text"])})
            variants = [(o, nt["templates"][0], f"c{o}") for o in ords]
        else:
            multi = len(nt["templates"]) > 1
            variants = [(i + 1, t, t["name"] if multi else "") for i, t in enumerate(nt["templates"])]
        for ord_, tpl, label in variants:
            frames = []
            for side, src in (("front", tpl["qfmt"]), ("back", tpl["afmt"])):
                counter += 1
                fid = f"f{counter}"
                body = render(src, n["values"], ord_, side)
                doc = FRAME.format(base=base, css=nt["css"], ord=ord_ if not nt["cloze"] else 1, body=body, fid=fid)
                frames.append(f'<div><p class="side">{"正面 · 可交互" if side == "front" else "背面"}</p>'
                              f'<iframe id="{fid}" srcdoc="{html.escape(doc, quote=True)}"></iframe></div>')
            search = " ".join([n["id"], n["type"], n["deck"], " ".join(n["tags"])] +
                              [strip_html(v) for v in n["values"].values()]).lower()
            meta = (f'<b>{html.escape(n["id"])}</b><span>{html.escape(project.strings.get("name_" + n["type"], n["type"]))}'
                    f'{" · " + html.escape(label) if label else ""}</span><span>{html.escape(n["deck"])}</span>'
                    f'<span>{html.escape(" ".join(t for t in n["tags"] if not t.startswith("ankiskill::")))}</span>')
            rows.append(f'<section class="row" data-type="{n["type"]}" data-text="{html.escape(search, quote=True)}">'
                        f'<div class="meta">{meta}</div><div class="pair">{"".join(frames)}</div></section>')
    by_type = collections.Counter(n["type"] for n in notes)
    buttons = '<button class="on" data-type="all">全部</button>' + "".join(
        f'<button data-type="{t}">{html.escape(project.strings.get("name_" + t, t))} {c}</button>'
        for t, c in by_type.items())
    stats = f"{len(notes)} 条笔记 · {len(rows)} 张卡 · 主题 {html.escape(str(project.meta.get('theme', 'custom')))}"
    out_path.write_text(PAGE.format(title=html.escape(project.name), stats=stats, type_buttons=buttons,
                                    rows="\n".join(rows)), encoding="utf-8")
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--preview-only", action="store_true", help="只生成预览,不打包 apkg")
    ap.add_argument("--check", action="store_true", help="只校验")
    a = ap.parse_args()

    project = Project(a.project)
    notes, specs, errors = collect(project)
    if errors:
        print(f"校验失败,共 {len(errors)} 个问题:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    by_type = dict(collections.Counter(n["type"] for n in notes))
    print(f"校验通过:{len(notes)} 条笔记 {by_type}")
    for w in warnings(notes):
        print(f"  警告:{w}")
    if a.check:
        return

    build = project.root / "build"
    build.mkdir(exist_ok=True)
    record = {"time": dt.datetime.now().isoformat(timespec="seconds"), "notes": len(notes), "by_type": by_type,
              "theme": project.meta.get("theme"),
              "css_sha1": hashlib.sha1(next(iter(specs.values()))["css"].encode("utf-8")).hexdigest()[:10],
              "custom_templates": sorted(t for t, s in specs.items() if s["custom"])}

    if not a.preview_only:
        apkg = build / (SAFE_NAME.sub("_", project.name) + ".apkg")
        n_media, missing = build_apkg(project, notes, specs, apkg)
        for m in missing:
            print(f"  警告:引用的媒体文件不存在 {m}")
        print(f"已生成 {apkg}(媒体文件 {n_media} 个)")
        record.update(apkg=apkg.name, media=n_media, missing_media=len(missing))
    if not a.no_preview:
        pv = build / "preview.html"
        n_cards = build_preview(project, notes, specs, pv)
        print(f"已生成 {pv}({n_cards} 张卡)")
        record["cards"] = n_cards
    with open(build / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
