"""Shared helpers: project loading, note type assembly, card normalization."""
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("缺少依赖:pip install pyyaml")

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
TYPES = ["basic", "reversed", "cloze", "mcq", "truefalse", "typein"]
REQUIRED = {
    "basic": ["Front", "Back"],
    "reversed": ["Front", "Back"],
    "cloze": ["Text"],
    "mcq": ["Question", "Options", "Answer"],
    "truefalse": ["Statement", "Answer"],
    "typein": ["Front", "Answer"],
}
TRUE_WORDS = {"1", "true", "t", "yes", "y", "对", "是", "正确", "√", "✓"}
FALSE_WORDS = {"0", "false", "f", "no", "n", "错", "否", "错误", "×", "✗"}


def load_yaml(path):
    path = Path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)


def stable_int(*parts, lo=1 << 30, span=1 << 30):
    """Deterministic id in genanki's recommended range, derived from project uid."""
    h = hashlib.sha1(":".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return lo + int(h[:12], 16) % span


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        meta = load_yaml(self.root / "project.yaml")
        if not meta:
            sys.exit(f"{self.root} 不是项目目录(缺少 project.yaml)。先运行 project.py init。")
        if not meta.get("uid"):
            sys.exit("project.yaml 缺少 uid")
        self.meta = meta
        self.name = meta["name"]
        self.uid = str(meta["uid"])
        self.lang = meta.get("lang", "zh")
        i18n = json.loads((ASSETS / "i18n.json").read_text(encoding="utf-8"))
        self.strings = i18n.get(self.lang, i18n["zh"])

    # ---------- content ----------
    def load_cards(self):
        cards = []
        files = []
        if (self.root / "cards.yaml").exists():
            files.append(self.root / "cards.yaml")
        if (self.root / "cards").is_dir():
            files += sorted((self.root / "cards").glob("*.yaml"))
        for f in files:
            data = load_yaml(f) or {}
            items = data.get("cards", []) if isinstance(data, dict) else data
            for c in items or []:
                c["_file"] = f.name
                cards.append(c)
        return cards

    def load_points(self):
        data = load_yaml(self.root / "knowledge.yaml") or {}
        return {p["id"]: p for p in data.get("points", []) or [] if "id" in p}

    # ---------- style ----------
    def css(self):
        parts = [(ASSETS / "base.css").read_text(encoding="utf-8")]
        for name in ("theme.css", "overrides.css"):
            p = self.root / "style" / name
            if p.exists():
                parts.append(f"/* ---- style/{name} ---- */\n" + p.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    def t(self, text):
        text = re.sub(r"\[\[include:([\w.\-]+)\]\]", lambda m: self._include(m.group(1)), text)
        return re.sub(r"\[\[t:(\w+)\]\]", lambda m: self.strings.get(m.group(1), m.group(1)), text)

    def _include(self, name):
        for d in (self.root / "style" / "templates" / "js", ASSETS / "js"):
            if (d / name).exists():
                return (d / name).read_text(encoding="utf-8")
        sys.exit(f"模板引用了不存在的脚本 {name}")

    def note_type(self, ctype):
        """Return dict(name, id, fields, templates[{name,qfmt,afmt}], cloze, css)."""
        local = self.root / "style" / "templates" / ctype
        src = local if (local / "model.json").exists() else ASSETS / "note_types" / ctype
        spec = json.loads((src / "model.json").read_text(encoding="utf-8"))
        templates = []
        for tpl in spec["templates"]:
            templates.append({
                "name": self.t(tpl["name"]),
                "qfmt": self.t((src / tpl["front"]).read_text(encoding="utf-8")),
                "afmt": self.t((src / tpl["back"]).read_text(encoding="utf-8")),
            })
        prefix = self.meta.get("model_prefix") or self.name
        return {
            "name": f"{prefix} · {self.strings.get('name_' + ctype, ctype)}",
            "id": stable_int(self.uid, "model", ctype),
            "fields": spec["fields"],
            "templates": templates,
            "cloze": bool(spec.get("cloze")),
            "css": self.css(),
            "custom": src == local,
        }


def field_value(ctype, name, value):
    """Convert a YAML field value to the string stored in Anki."""
    if value is None:
        return ""
    if isinstance(value, bool):
        if ctype == "truefalse" and name == "Answer":
            return "true" if value else "false"
        return "1" if value else ""
    if isinstance(value, (list, tuple)):
        if ctype == "mcq" and name == "Answer":
            return ",".join(str(v) for v in value)
        return "<br>".join(str(v).strip() for v in value)
    return str(value).strip()


def validate(card, fields_spec):
    """Return list of error strings for one card (already has type)."""
    errs = []
    ctype = card.get("type")
    f = card.get("fields") or {}
    for req in REQUIRED[ctype]:
        if f.get(req) in (None, "", []):
            errs.append(f"缺少必填字段 {req}")
    unknown = [k for k in f if k not in fields_spec]
    if unknown:
        errs.append(f"未知字段 {unknown}(该题型字段为 {fields_spec})")
    if ctype == "cloze" and f.get("Text") and not re.search(r"\{\{c\d+::", str(f["Text"])):
        errs.append("Text 中没有 {{c1::...}} 填空")
    if ctype == "mcq" and f.get("Options") and f.get("Answer") not in (None, ""):
        opts = f["Options"]
        n = len(opts) if isinstance(opts, list) else len([s for s in re.split(r"<br\s*/?>|\n", str(opts)) if s.strip()])
        if n < 2:
            errs.append("选项少于 2 个")
        ans = field_value("mcq", "Answer", f["Answer"]).upper()
        for tok in re.findall(r"[A-Z]|\d+", ans):
            i = int(tok) - 1 if tok.isdigit() else ord(tok) - 65
            if not 0 <= i < n:
                errs.append(f"答案 {tok} 超出选项范围(共 {n} 个)")
        if not re.findall(r"[A-Z]|\d+", ans):
            errs.append(f"无法解析答案 {f['Answer']!r},应为字母如 B 或 A,C")
    if ctype == "truefalse" and f.get("Answer") is not None and not isinstance(f["Answer"], bool):
        v = str(f["Answer"]).strip().lower()
        if v not in TRUE_WORDS | FALSE_WORDS:
            errs.append(f"判断题答案 {f['Answer']!r} 无法识别,用 true/false")
    if ctype == "typein" and f.get("Answer") and re.search(r"<[^>]+>", str(f["Answer"])):
        errs.append("输入答案卡的 Answer 不能包含 HTML(比对会失败)")
    return errs
