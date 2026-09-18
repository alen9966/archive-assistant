"""读取项目配置。支持简易 YAML（无需 PyYAML）与 JSON。不编造空字段。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class AssemblyVariant:
    name: str = ""
    code: str = ""


@dataclass
class ProjectConfig:
    project_name: str = ""
    project_code: str = ""
    model: str = ""
    boards: list[str] = field(default_factory=list)
    assembly_variants: list[AssemblyVariant] = field(default_factory=list)
    quantity: str = ""
    owners: dict[str, str] = field(default_factory=dict)
    archive_date: str = ""
    allow_move: bool = False
    confirm_move: bool = False
    not_applicable: list[str] = field(default_factory=list)
    confirmers: dict[str, str] = field(default_factory=dict)
    source_path: str = ""

    def display_name(self) -> str:
        return self.project_name or "待确认项目"

    def date_yyyymmdd(self) -> str:
        if self.archive_date:
            return normalize_date(self.archive_date) or self.archive_date
        return date.today().strftime("%Y%m%d")


OWNER_KEYS = (
    "hardware",
    "quality",
    "test",
    "software",
    "purchase",
    "production",
    "structure",
)

ROLE_TO_OWNER_KEY = {
    "硬件": "hardware",
    "质量": "quality",
    "测试": "test",
    "软件": "software",
    "采购": "purchase",
    "生产": "production",
    "王杰": "structure",
    "结构": "structure",
}


def normalize_date(text: str) -> str:
    """把日期规范为 YYYYMMDD；无法识别则返回空，不编造。"""
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return digits
    if len(digits) == 6:
        return "20" + digits
    return ""


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    out = []
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s in ("null", "~"):
        return ""
    if s in ("[]",):
        return []
    if s in ("{}",):
        return {}
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """支持本项目配置所需的缩进 YAML 子集。"""
    raw_lines = text.splitlines()
    filtered: list[tuple[int, str]] = []
    for line in raw_lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cut = _strip_comment(line)
        if not cut.strip():
            continue
        indent = len(cut) - len(cut.lstrip(" "))
        filtered.append((indent, cut.strip()))

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def current_container() -> Any:
        return stack[-1][1]

    i = 0
    while i < len(filtered):
        indent, content = filtered[i]
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        container = current_container()

        if content.startswith("- "):
            item_text = content[2:].strip()
            if not isinstance(container, list):
                raise ValueError(f"YAML 列表项出现在非列表下: {content}")
            if ":" in item_text and not item_text.startswith("{") and not (
                item_text.startswith('"') or item_text.startswith("'")
            ):
                key, _, rest = item_text.partition(":")
                obj: dict[str, Any] = {key.strip(): _parse_scalar(rest)}
                container.append(obj)
                stack.append((indent, obj))
            else:
                container.append(_parse_scalar(item_text) if item_text else {})
                if item_text == "" or item_text.endswith(":"):
                    pass
            i += 1
            continue

        key, sep, rest = content.partition(":")
        if not sep:
            raise ValueError(f"无法解析 YAML 行: {content}")
        key = key.strip()
        rest = rest.strip()
        if not isinstance(container, dict):
            # 列表项后续字段
            if isinstance(container, list) and container and isinstance(container[-1], dict):
                container = container[-1]
            else:
                raise ValueError(f"YAML 键出现在非字典下: {content}")

        if rest == "":
            # 看下一行决定是 list 还是 dict
            nxt = filtered[i + 1] if i + 1 < len(filtered) else None
            if nxt and nxt[0] > indent and nxt[1].startswith("- "):
                value: Any = []
            else:
                value = {}
            container[key] = value
            stack.append((indent, value))
        else:
            container[key] = _parse_scalar(rest)
        i += 1
    return root


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def config_from_mapping(data: dict[str, Any], source_path: str = "") -> ProjectConfig:
    boards = [_as_str(x) for x in _as_list(data.get("boards")) if _as_str(x)]
    variants: list[AssemblyVariant] = []
    for item in _as_list(data.get("assembly_variants")):
        if isinstance(item, dict):
            variants.append(
                AssemblyVariant(name=_as_str(item.get("name")), code=_as_str(item.get("code")))
            )
        elif _as_str(item):
            variants.append(AssemblyVariant(name=_as_str(item), code=""))
    owners_raw = data.get("owners") or {}
    owners = {}
    if isinstance(owners_raw, dict):
        for k in OWNER_KEYS:
            owners[k] = _as_str(owners_raw.get(k))
    confirmers_raw = data.get("confirmers") or {}
    confirmers = {}
    if isinstance(confirmers_raw, dict):
        confirmers = {str(k): _as_str(v) for k, v in confirmers_raw.items() if _as_str(v)}
    archive_date = _as_str(data.get("archive_date"))
    nd = normalize_date(archive_date)
    if nd:
        archive_date = nd
    return ProjectConfig(
        project_name=_as_str(data.get("project_name")),
        project_code=_as_str(data.get("project_code")),
        model=_as_str(data.get("model")),
        boards=boards,
        assembly_variants=variants,
        quantity=_as_str(data.get("quantity")),
        owners=owners,
        archive_date=archive_date,
        allow_move=bool(data.get("allow_move", False)),
        confirm_move=bool(data.get("confirm_move", False)),
        not_applicable=[_as_str(x) for x in _as_list(data.get("not_applicable")) if _as_str(x)],
        confirmers=confirmers,
        source_path=source_path,
    )


def load_config(path: str | Path | None) -> ProjectConfig:
    if not path:
        return ProjectConfig()
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise ValueError("配置文件根节点必须是映射")
    return config_from_mapping(data, str(p))


def format_owners(roles_text: str, cfg: ProjectConfig) -> str:
    """索引「负责人」：模板角色 + 配置中的人名。"""
    if not roles_text:
        return ""
    parts = re.split(r"[/／、,，;；]+", roles_text)
    rendered: list[str] = []
    seen: set[str] = set()
    for part in parts:
        role = re.sub(r"[（(].*?[）)]", "", part).strip()
        if not role or role in seen:
            continue
        seen.add(role)
        key = ROLE_TO_OWNER_KEY.get(role)
        person = cfg.owners.get(key, "") if key else ""
        if person:
            rendered.append(f"{role}（{person}）")
        else:
            rendered.append(role)
    return "/".join(rendered)


def confirmer_remark(roles_text: str, cfg: ProjectConfig) -> str:
    names = [v for v in cfg.confirmers.values() if v]
    if names:
        return "实际确认人：" + "、".join(names)
    if any(cfg.owners.values()):
        filled = [f"{k}={v}" for k, v in cfg.owners.items() if v]
        return "配置负责人：" + "、".join(filled) + "；实际确认人待确认"
    return "实际确认人待确认"
