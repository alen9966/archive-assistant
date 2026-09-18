"""扫描待归档资料，计算哈希，标记敏感与重复。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

SENSITIVE_KEYWORDS = (
    "密码",
    "密钥",
    "证书",
    "私钥",
    "账号",
    "保密",
    "内部",
    "客户机密",
    "password",
    "secret",
    "privatekey",
    "credential",
)
SENSITIVE_EXTS = {".pem", ".key", ".pfx", ".p12", ".cer", ".crt"}

SKIP_DIR_NAMES = {".git", "__pycache__", ".svn", "thumbs.db", "history", "__previews"}
SKIP_DIR_PREFIXES = ("project logs",)
SKIP_FILE_NAMES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
    "00_归档索引.xlsx",
    "00_归档索引.csv",
    "00_缺失资料清单.xlsx",
    "00_缺失资料清单.csv",
    "00_待确认清单.xlsx",
    "00_待确认清单.csv",
    "00_重复文件清单.xlsx",
    "00_重复文件清单.csv",
    "00_归档报告.md",
}

CHUNK = 1024 * 1024


@dataclass
class SourceFile:
    path: Path
    rel: str
    name: str
    sha256: str
    size: int
    sensitive: bool
    sensitive_reason: str = ""
    duplicate_of: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def is_sensitive(path: Path) -> tuple[bool, str]:
    name = path.name
    lower = name.lower()
    ext = path.suffix.lower()
    reasons: list[str] = []
    if ext in SENSITIVE_EXTS:
        reasons.append(f"扩展名 {ext}")
    text = str(path)
    for kw in SENSITIVE_KEYWORDS:
        if kw.lower() in text.lower() or kw in name:
            reasons.append(f"关键词「{kw}」")
    if reasons:
        return True, "；".join(reasons)
    # 避免把 password 误伤到普通英文？已包含在关键词中
    _ = lower
    return False, ""


def _skip_dir_part(part: str) -> bool:
    name = (part or "").lower()
    if name in SKIP_DIR_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES)


def should_skip(path: Path, source: Path, output: Path) -> bool:
    if not path.is_file():
        return True
    name = path.name
    if name.startswith("~$"):
        return True
    if name.lower() in SKIP_FILE_NAMES or name in SKIP_FILE_NAMES:
        return True
    if any(_skip_dir_part(part) for part in path.parts):
        return True
    if name.startswith("项目归档包_") and name.lower().endswith(".zip"):
        return True
    try:
        path.resolve().relative_to(output.resolve())
        return True  # 位于输出目录内
    except ValueError:
        pass
    if path.suffix.lower() in {".py", ".pyc"} and "archive_assistant" in path.parts:
        return True
    return False


def scan_source(source: Path, output: Path) -> list[SourceFile]:
    source = source.resolve()
    output = output.resolve()
    files: list[SourceFile] = []
    if not source.exists():
        raise FileNotFoundError(f"源目录不存在: {source}")
    for path in sorted(source.rglob("*")):
        if should_skip(path, source, output):
            continue
        try:
            rel = str(path.relative_to(source)).replace("\\", "/")
        except ValueError:
            rel = path.name
        digest = sha256_file(path)
        sensitive, reason = is_sensitive(path)
        files.append(
            SourceFile(
                path=path,
                rel=rel,
                name=path.name,
                sha256=digest,
                size=path.stat().st_size,
                sensitive=sensitive,
                sensitive_reason=reason,
            )
        )
    seen: dict[str, str] = {}
    for item in files:
        if item.sha256 in seen:
            item.duplicate_of = seen[item.sha256]
        else:
            seen[item.sha256] = item.rel
    return files
