"""定位《资料归档规范-模板.xlsx》。目录结构以代码内固化的模板原文为准。"""

from __future__ import annotations

from pathlib import Path


TEMPLATE_NAME = "资料归档规范-模板.xlsx"


def find_template(start: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if start:
        candidates.append(start / TEMPLATE_NAME)
        candidates.append(start.parent / TEMPLATE_NAME)
    candidates.append(Path.cwd() / TEMPLATE_NAME)
    here = Path(__file__).resolve().parent.parent
    candidates.append(here / TEMPLATE_NAME)
    seen: set[Path] = set()
    for c in candidates:
        try:
            r = c.resolve()
        except OSError:
            continue
        if r in seen:
            continue
        seen.add(r)
        if r.is_file():
            return r
    return None
