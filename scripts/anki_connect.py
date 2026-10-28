#!/usr/bin/env python3
"""Push the project's current templates + CSS straight into a running Anki via AnkiConnect
(add-on 2055492159), so a restyle takes effect without re-importing and without touching
review history.

  anki_connect.py status                 # 检查 AnkiConnect 是否可用
  anki_connect.py push-style <project>   # 更新本项目已存在于 Anki 中的笔记类型的模板与样式
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Project  # noqa: E402

URL = "http://127.0.0.1:8765"


def call(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, body), timeout=10) as r:
            res = json.loads(r.read())
    except OSError:
        sys.exit("连不上 AnkiConnect:请确认 Anki 已打开并安装了 AnkiConnect 插件(代码 2055492159)")
    if res.get("error"):
        raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]


def push_style(project_dir):
    p = Project(project_dir)
    existing = set(call("modelNames"))
    types = sorted({c.get("type") for c in p.load_cards() if c.get("type")})
    for ctype in types:
        nt = p.note_type(ctype)
        if nt["name"] not in existing:
            print(f"  跳过 {nt['name']}:Anki 中还没有这个笔记类型(先导入一次 apkg)")
            continue
        have = set(call("modelFieldNames", modelName=nt["name"]))
        if have != set(nt["fields"]):
            print(f"  跳过 {nt['name']}:字段不一致 {sorted(have)} ≠ {sorted(nt['fields'])},需要重新导入并合并笔记类型")
            continue
        call("updateModelStyling", model={"name": nt["name"], "css": nt["css"]})
        tpl_names = set(call("modelTemplates", modelName=nt["name"]).keys())
        templates = {t["name"]: {"Front": t["qfmt"], "Back": t["afmt"]} for t in nt["templates"] if t["name"] in tpl_names}
        if templates:
            call("updateModelTemplates", model={"name": nt["name"], "templates": templates})
        print(f"  ✓ {nt['name']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    s = sub.add_parser("push-style")
    s.add_argument("project")
    a = ap.parse_args()
    if a.cmd == "status":
        print(f"AnkiConnect 版本 {call('version')}")
    else:
        push_style(a.project)


if __name__ == "__main__":
    main()
