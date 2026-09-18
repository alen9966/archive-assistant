"""文件名清洗、字段提取。不编造编号。"""

from __future__ import annotations

import re
from pathlib import Path

from archive_assistant.config import ProjectConfig, normalize_date

FORBIDDEN = re.compile(r'[\\/:*?"<>|]')
BOARD_RE = re.compile(r"ZC\d+(?:[._]\d+){2}(?:-V[\d.]+)?", re.I)
CODE_RE = re.compile(r"ZCJY\d{6}", re.I)
DATE8_RE = re.compile(r"(20\d{6})")
DATE6_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
VERSION_RE = re.compile(r"\bV\d+(?:\.\d+)+\b", re.I)
QTY_RE = re.compile(r"(\d+)\s*套")
BOOT_RE = re.compile(
    r"^BOOT_([^_]+)_([^_]+)(?:_([^_]+))?_(\d{6,8})(?:_.*)?$",
    re.I,
)


def sanitize_filename(name: str) -> str:
    """禁止字符全部替换为 _；压缩连续下划线（保留扩展名）。"""
    if not name:
        return "待确认"
    p = Path(name)
    stem, ext = p.stem, p.suffix
    stem = FORBIDDEN.sub("_", stem)
    stem = stem.replace("/", "_")
    stem = re.sub(r"_+", "_", stem).strip(" .")
    ext = FORBIDDEN.sub("_", ext)
    if not stem:
        stem = "待确认"
    return stem + ext


def join_parts(*parts: str, ext: str = "") -> str:
    cleaned = []
    for p in parts:
        s = (p or "").strip()
        if not s:
            continue
        s = FORBIDDEN.sub("_", s).replace("/", "_")
        s = re.sub(r"_+", "_", s).strip(" ._")
        if s:
            cleaned.append(s)
    name = "_".join(cleaned) if cleaned else "待确认"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return sanitize_filename(name + (ext or ""))


def extract_board(text: str, cfg: ProjectConfig) -> str:
    for b in cfg.boards:
        if b and b in text:
            return b
    m = BOARD_RE.search(text)
    if m:
        return m.group(0)
    if len(cfg.boards) == 1:
        return cfg.boards[0]
    return ""


def extract_code(text: str, cfg: ProjectConfig) -> str:
    if cfg.project_code and cfg.project_code in text:
        return cfg.project_code
    m = CODE_RE.search(text)
    if m:
        return m.group(0)
    return cfg.project_code


def extract_date(text: str, cfg: ProjectConfig, *, fallback_archive: bool = True) -> tuple[str, str]:
    """返回 (YYYYMMDD, 备注)。不把历史文件日期编造出来；无日期时可用归档日。"""
    m8 = DATE8_RE.search(text)
    if m8:
        return m8.group(1), ""
    m6 = DATE6_RE.search(text)
    if m6:
        raw = m6.group(1)
        # 避免把工号后 6 位误当日期：ZCJY260101 中 260101
        idx = m6.start(1)
        prefix = text[max(0, idx - 4) : idx]
        if prefix.upper().endswith("ZCJY"):
            pass
        else:
            return "20" + raw, f"原日期 {raw} 已规范为 YYYYMMDD"
    if fallback_archive:
        return cfg.date_yyyymmdd(), "日期取自归档日期（暂定默认，可改）"
    return "", "文件名中未提取到日期"


def extract_qty(text: str, cfg: ProjectConfig) -> str:
    m = QTY_RE.search(text)
    if m:
        return m.group(1) + "套"
    return cfg.quantity


def extract_version(text: str) -> str:
    # 板号自带版本不单独拆；其它 V1.0
    m = VERSION_RE.search(text)
    return m.group(0) if m else ""


def extract_variant(text: str, cfg: ProjectConfig) -> tuple[str, str]:
    """(name, code)"""
    for v in cfg.assembly_variants:
        if v.name and v.name in text:
            return v.name, v.code or cfg.project_code
        if v.code and v.code in text:
            return v.name, v.code
    if len(cfg.assembly_variants) == 1:
        v = cfg.assembly_variants[0]
        return v.name, v.code or cfg.project_code
    return "", cfg.project_code


def parse_boot(stem: str) -> dict[str, str]:
    """从 BOOT_ 原名提取用户/产品/功能/日期，提取不到不编造。"""
    m = BOOT_RE.match(stem)
    if not m:
        parts = stem.split("_")
        result = {"user": "", "product": "", "function": "", "date": "", "note": "未能按 BOOT_用户_产品_功能_日期 解析，已标待确认"}
        if len(parts) >= 2 and parts[0].upper() == "BOOT":
            result["user"] = parts[1]
            result["note"] = "仅提取到部分 BOOT 字段，其余待确认"
        return result
    user, product, func, raw_date = m.group(1), m.group(2), m.group(3) or "", m.group(4)
    return {
        "user": user,
        "product": product,
        "function": func,
        "date": normalize_date(raw_date) or raw_date,
        "note": "" if func else "功能字段未提取到，已标待确认",
    }


def placeholder(value: str) -> str:
    return value.strip() if value and value.strip() else "待确认"
