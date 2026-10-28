#!/usr/bin/env python3
"""Project management.

  project.py init <dir> --name 名称 [--theme minimal] [--lang zh] [--types basic,cloze]
  project.py set-theme <dir> <theme>      # 旧 theme.css 自动备份到 style/history/
  project.py list-themes
  project.py log <dir> "一句话说明"         # 往 DESIGN_LOG.md 追加一条简短记录
"""
import argparse
import datetime as dt
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ASSETS, TYPES, dump_yaml, load_yaml  # noqa: E402

THEMES = ASSETS / "themes"


def theme_desc(path):
    first = path.read_text(encoding="utf-8").lstrip().splitlines()[0]
    return first.strip("/* ").strip()


def today():
    return dt.date.today().isoformat()


def append_log(root, text):
    with open(root / "DESIGN_LOG.md", "a", encoding="utf-8") as f:
        f.write(text)


def cmd_init(a):
    root = Path(a.dir).resolve()
    if (root / "project.yaml").exists():
        sys.exit(f"{root} 已经是项目目录,不会覆盖。")
    theme = THEMES / f"{a.theme}.css"
    if not theme.exists():
        sys.exit(f"没有主题 {a.theme}。可用:{', '.join(p.stem for p in THEMES.glob('*.css'))}")
    types = [t.strip() for t in a.types.split(",") if t.strip()] if a.types else []
    bad = [t for t in types if t not in TYPES]
    if bad:
        sys.exit(f"未知题型 {bad}。可用:{TYPES}")

    for d in ("sources", "media", "style", "build"):
        (root / d).mkdir(parents=True, exist_ok=True)
    dump_yaml({
        "name": a.name,
        "uid": secrets.token_hex(6),
        "lang": a.lang,
        "theme": a.theme,
        "card_types": types,
        "sources": [],
    }, root / "project.yaml")
    shutil.copy(theme, root / "style" / "theme.css")
    (root / "style" / "overrides.css").write_text("/* 项目特有的结构性样式调整 */\n", encoding="utf-8")
    (root / "style" / "brief.md").write_text(
        f"# 风格说明\n\n## 用户需求\n\n(用户的原话)\n\n## 设计意图\n\n起点主题:{a.theme} — {theme_desc(theme)}\n",
        encoding="utf-8")
    (root / "knowledge.yaml").write_text("points: []\n", encoding="utf-8")
    (root / "cards.yaml").write_text("cards: []\n", encoding="utf-8")
    (root / ".gitignore").write_text("build/*.apkg\nbuild/preview.html\n", encoding="utf-8")
    append_log(root, f"# {a.name} · 设计日志\n\n## {today()} 创建项目\n- 主题:{a.theme}\n- 题型:{', '.join(types) or '待定'}\n- 语言:{a.lang}\n")
    print(f"已创建项目 {root}")


def cmd_set_theme(a):
    root = Path(a.dir).resolve()
    meta = load_yaml(root / "project.yaml") or sys.exit("不是项目目录")
    theme = THEMES / f"{a.theme}.css"
    if not theme.exists():
        sys.exit(f"没有主题 {a.theme}。可用:{', '.join(p.stem for p in THEMES.glob('*.css'))}")
    cur = root / "style" / "theme.css"
    backup = None
    if cur.exists():
        hist = root / "style" / "history"
        hist.mkdir(exist_ok=True)
        backup = hist / f"theme-{dt.datetime.now():%Y%m%d-%H%M%S}-{meta.get('theme', 'custom')}.css"
        shutil.copy(cur, backup)
    shutil.copy(theme, cur)
    meta["theme"] = a.theme
    dump_yaml(meta, root / "project.yaml")
    note = f"(旧样式备份为 style/history/{backup.name})" if backup else ""
    append_log(root, f"\n## {today()} 切换主题 → {a.theme}\n- {theme_desc(theme)}{note}\n")
    print(f"主题已切换为 {a.theme}{note}")


def cmd_list_themes(a):
    for p in sorted(THEMES.glob("*.css")):
        print(f"{p.stem:10s} {theme_desc(p)}")


def cmd_log(a):
    root = Path(a.dir).resolve()
    append_log(root, f"\n## {today()}\n- {a.text}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("dir")
    p.add_argument("--name", required=True)
    p.add_argument("--theme", default="minimal")
    p.add_argument("--lang", default="zh", choices=["zh", "en"])
    p.add_argument("--types", default="")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("set-theme")
    p.add_argument("dir")
    p.add_argument("theme")
    p.set_defaults(fn=cmd_set_theme)
    p = sub.add_parser("list-themes")
    p.set_defaults(fn=cmd_list_themes)
    p = sub.add_parser("log")
    p.add_argument("dir")
    p.add_argument("text")
    p.set_defaults(fn=cmd_log)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
