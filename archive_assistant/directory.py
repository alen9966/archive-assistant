"""生成便于人工核对和问题定位的归档目录树。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


MANIFEST_NAME = "00_归档目录.txt"


def _entries(directory: Path) -> list[Path]:
    try:
        return sorted(directory.iterdir(), key=lambda path: (not path.is_dir(), path.name.casefold()))
    except OSError:
        return []


def _tree_lines(directory: Path, prefix: str = "") -> tuple[list[str], int, int]:
    lines: list[str] = []
    directory_count = 0
    file_count = 0
    entries = _entries(directory)
    for index, entry in enumerate(entries):
        last = index == len(entries) - 1
        branch = "└── " if last else "├── "
        if entry.is_dir() and not entry.is_symlink():
            directory_count += 1
            lines.append(f"{prefix}{branch}{entry.name}/")
            child_prefix = prefix + ("    " if last else "│   ")
            child_lines, child_dirs, child_files = _tree_lines(entry, child_prefix)
            lines.extend(child_lines)
            directory_count += child_dirs
            file_count += child_files
        else:
            file_count += 1
            lines.append(f"{prefix}{branch}{entry.name}")
    return lines, directory_count, file_count


def write_directory_manifest(output: Path, *, project_name: str, mode: str) -> Path:
    """扫描实际输出目录并写入 UTF-8 目录树；目录文件自身也包含在树中。"""
    output.mkdir(parents=True, exist_ok=True)
    target = output / MANIFEST_NAME
    target.write_text("", encoding="utf-8")
    tree, directory_count, file_count = _tree_lines(output)
    title = project_name or "未命名项目"
    text = "\n".join(
        [
            "项目资料归档目录",
            f"项目：{title}",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"模式：{mode}",
            f"统计：{directory_count} 个文件夹，{file_count} 个文件",
            "",
            f"{output.name}/",
            *tree,
            "",
        ]
    )
    target.write_text(text, encoding="utf-8")
    return target
