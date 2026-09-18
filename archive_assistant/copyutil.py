"""复制/可选移动。默认只复制；禁止覆盖；不删除原文件。"""

from __future__ import annotations

import shutil
from pathlib import Path

from archive_assistant.catalog import iter_directory_relpaths
from archive_assistant.names import sanitize_filename


def ensure_tree(output: Path) -> list[str]:
    created = []
    for rel in iter_directory_relpaths():
        dest = output / Path(*rel.split("/"))
        dest.mkdir(parents=True, exist_ok=True)
        created.append(rel)
    return created


def unique_dest(directory: Path, filename: str, archive_date: str) -> tuple[Path, str]:
    """同名不覆盖，依次加 _重复1 _重复2 _v2 _YYYYMMDD。"""
    filename = sanitize_filename(filename)
    directory.mkdir(parents=True, exist_ok=True)
    p = Path(filename)
    stem, ext = p.stem, p.suffix
    candidate = directory / filename
    if not candidate.exists():
        return candidate, filename
    suffixes = [f"_重复1", f"_重复2", "_v2", f"_{archive_date}"]
    for suf in suffixes:
        name = stem + suf + ext
        cand = directory / name
        if not cand.exists():
            return cand, name
    n = 2
    while True:
        name = f"{stem}_{archive_date}_{n}{ext}"
        cand = directory / name
        if not cand.exists():
            return cand, name
        n += 1


def copy_or_move(
    src: Path,
    dest: Path,
    *,
    do_move: bool,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"拒绝覆盖已存在文件: {dest}")
    if do_move:
        shutil.copy2(src, dest)
        # 移动：复制成功后再删源。若删源失败，目标已存在且源仍在，不继续删除其它文件。
        try:
            src.unlink()
        except OSError:
            # 不强制删除；视为复制成功并留下源文件
            pass
    else:
        shutil.copy2(src, dest)


def zip_output(output: Path, zip_path: Path) -> None:
    import zipfile

    output = output.resolve()
    zip_path = zip_path.resolve()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output.rglob("*")):
            if not path.is_file():
                continue
            if path.resolve() == zip_path:
                continue
            arc = path.relative_to(output).as_posix()
            zf.write(path, arcname=arc)
