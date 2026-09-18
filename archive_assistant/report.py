"""归档报告 Markdown。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from archive_assistant.config import ProjectConfig
from archive_assistant.defaults import policy_markdown
from archive_assistant.records import ArchiveRecord


def write_report(
    path: Path,
    cfg: ProjectConfig,
    *,
    mode: str,
    source: Path,
    output: Path,
    files: list[ArchiveRecord],
    missing: list[ArchiveRecord],
    pending: list[ArchiveRecord],
    duplicates: list[ArchiveRecord],
    sensitive: list[ArchiveRecord],
    logs: list[str],
    copied: int,
) -> None:
    archived = [r for r in files if r.status == "已归档"]
    lines = [
        "# 归档报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 模式：{mode}（plan 不复制；apply 才复制）",
        f"- 源目录：`{source}`",
        f"- 归档根目录：`{output}`",
        "",
        "## 项目信息",
        "",
        f"- 项目名称：{cfg.project_name or '（未提供，未编造）'}",
        f"- 项目工号：{cfg.project_code or '（未提供，未编造）'}",
        f"- 型号：{cfg.model or '（未提供，未编造）'}",
        f"- 板号：{', '.join(cfg.boards) if cfg.boards else '（未提供，未编造）'}",
        f"- 装配变量：{', '.join((v.name or v.code) for v in cfg.assembly_variants) if cfg.assembly_variants else '（未提供，未编造）'}",
        f"- 套数：{cfg.quantity or '（未提供，未编造）'}",
        f"- 归档日期：{cfg.date_yyyymmdd()}",
        f"- 负责人配置：{cfg.owners if any(cfg.owners.values()) else '（未提供）'}",
        f"- 允许移动：{cfg.allow_move} / 二次确认参数：{cfg.confirm_move}（暂定默认关闭）",
        "",
        "## 统计",
        "",
        f"- 扫描文件总数：{len(files)}",
        f"- 已归档（已映射/已复制）：{len(archived)}",
        f"- 本次复制数：{copied}",
        f"- 缺失（矩阵必查）：{sum(1 for m in missing if m.status == '缺失')}",
        f"- 待确认是否必交：{sum(1 for m in missing if m.status == '待确认')}",
        f"- 待确认（分类/命名等）：{len(pending)}",
        f"- 重复（哈希）：{len(duplicates)}",
        f"- 敏感文件：{len(sensitive)}",
        "",
        "## 敏感文件提醒",
        "",
    ]
    if not sensitive:
        lines.append("无。仅做本地标记，未上传外部。")
    else:
        lines.append("以下文件被启发式标记为敏感（仅标记，未外传）：")
        lines.append("")
        for r in sensitive:
            lines.append(f"- `{r.original_name}` — {r.remark_text()}")
    lines += [
        "",
        "## 操作日志",
        "",
    ]
    for log in logs:
        lines.append(f"- {log}")
    lines += [
        "",
        "## 下一步建议",
        "",
        "1. 打开 `00_待确认清单`，补全分类、板号、装配变量、BOOT 用户/功能、实际确认人。",
        "2. 打开 `00_缺失资料清单`，按矩阵补齐 12 类必查资料；其余项确认是否必交。",
        "3. 核对原理图+调试记录是否完整（需硬件确认）。",
        "4. 会议纪要中补充「待补充文件及完成时间」。",
        "5. 多媒体记录核对应含包装箱图片（若项目涉及包装箱）。",
        "6. 确认方案后执行 `python -m archive_assistant apply ...`；需要压缩包再加 `--zip`。",
        "7. 不要删除或覆盖源文件。",
        "",
        "## 本次使用的暂定默认规则",
        "",
        policy_markdown(),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
