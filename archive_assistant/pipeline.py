"""两阶段归档流水线：plan 默认不复制，apply 才复制。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from archive_assistant.catalog import UNKNOWN_FOLDER, parse_folder_label, spec_by_path
from archive_assistant.classify import classify_file, classify_override
from archive_assistant.config import ProjectConfig, confirmer_remark, format_owners
from archive_assistant.copyutil import copy_or_move, ensure_tree, unique_dest, zip_output
from archive_assistant.index import write_table
from archive_assistant.names import sanitize_filename
from archive_assistant.records import ArchiveRecord, build_missing, number_records
from archive_assistant.rename import generate_name
from archive_assistant.report import write_report
from archive_assistant.scan import scan_source, sha256_file
from archive_assistant.template import find_template


@dataclass
class RunResult:
    output: Path
    records: list[ArchiveRecord]
    missing: list[ArchiveRecord]
    pending: list[ArchiveRecord]
    duplicates: list[ArchiveRecord]
    copied: int
    logs: list[str] = field(default_factory=list)


def _existing_hashes(output: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not output.exists():
        return found
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("00_"):
            continue
        if path.name.startswith("项目归档包_") and path.suffix.lower() == ".zip":
            continue
        try:
            found[sha256_file(path)] = str(path)
        except OSError:
            continue
    return found


def run_archive(
    *,
    source: Path,
    output: Path,
    cfg: ProjectConfig,
    apply: bool,
    make_zip: bool = False,
    confirm_move: bool = False,
    write_outputs: bool | None = None,
    overrides: dict[str, dict] | None = None,
) -> RunResult:
    """
    write_outputs: 默认与 CLI 一致（plan/apply 都写五件套和目录树）。
    网页预览传 False，不写盘。apply 时强制写盘。
    overrides: {相对路径: {main, sub, extra_sub, new_name}}
    """
    if write_outputs is None:
        write_outputs = True
    if apply:
        write_outputs = True
    logs: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"{now} 读取配置：{cfg.source_path or '（无配置文件，字段留空不编造）'}")
    tpl = find_template(source)
    logs.append(f"模板：{tpl if tpl else '未找到 xlsx，使用内置目录原文（与模板一致）'}")
    source = source.resolve()
    output = output.resolve()
    logs.append(f"扫描源目录：{source}")
    files = scan_source(source, output)
    logs.append(f"扫描到文件 {len(files)} 个")

    if write_outputs:
        ensure_tree(output)
        logs.append("已建立标准归档目录（含 99_待确认与其他）")

    dest_hashes = _existing_hashes(output) if apply else {}
    records: list[ArchiveRecord] = []
    planned_names: dict[str, int] = {}
    copied = 0
    do_move = bool(apply and cfg.allow_move and (cfg.confirm_move or confirm_move))
    if apply and (cfg.allow_move or confirm_move) and not do_move:
        logs.append("移动未执行：需要配置 allow_move=true 且 --confirm-move（暂定默认只复制）")
    if not apply:
        logs.append("plan 模式：只输出方案，不复制文件")
    else:
        logs.append("apply 模式：" + ("移动（先复制再删源）" if do_move else "仅复制，不删除源文件"))

    ov_map = overrides or {}
    for item in files:
        ov = ov_map.get(item.rel) or ov_map.get(item.name) or {}
        if ov.get("main") or ov.get("sub") or ov.get("label"):
            main, sub, extra = ov.get("main", ""), ov.get("sub", ""), ov.get("extra_sub", "")
            if ov.get("label") and not main:
                main, sub, extra = parse_folder_label(str(ov["label"]))
            cls = classify_override(item, main, sub, extra)
        else:
            cls = classify_file(item)
        new_name, parent, fields, rename_remarks = generate_name(item, cls, cfg)
        if ov.get("new_name"):
            custom = sanitize_filename(str(ov["new_name"]))
            if custom:
                new_name = custom
                parent = f"{cls.main}/{cls.sub}" if cls.sub else cls.main
                if cls.extra_sub:
                    parent = f"{parent}/{cls.extra_sub}"
                rename_remarks.append("新文件名由网页用户指定")
        spec = spec_by_path(cls.main, cls.sub)
        status = "待确认" if cls.pending or cls.main == UNKNOWN_FOLDER else "已归档"
        remarks = list(rename_remarks)
        remarks.append(f"分类依据：{cls.reason}（置信度 {cls.confidence}）")
        if spec and spec.confirm_required:
            remarks.append(spec.confirm_required)
        remarks.append(confirmer_remark(spec.owners_roles if spec else "", cfg))
        if item.sensitive:
            remarks.append(f"敏感文件标记：{item.sensitive_reason}（仅本地标记，未外传）")
            status = "待确认" if status == "已归档" else status

        if item.duplicate_of:
            status = "重复"
            remarks.append(f"与 {item.duplicate_of} 哈希相同（sha256）")

        key = parent + "/" + new_name
        planned_names[key] = planned_names.get(key, 0) + 1
        if planned_names[key] > 1:
            remarks.append("目标新文件名冲突，apply 时自动加后缀且不覆盖")

        dest_dir = output.joinpath(*parent.split("/"))
        final_name = new_name
        dest_path = dest_dir / new_name
        if apply:
            if item.sha256 in dest_hashes:
                dest_path = Path(dest_hashes[item.sha256])
                final_name = dest_path.name
                remarks.append(f"归档目录已存在相同哈希，跳过复制（未覆盖）：{dest_path}")
                if item.duplicate_of:
                    status = "重复"
            else:
                dest_path, final_name = unique_dest(dest_dir, new_name, cfg.date_yyyymmdd())
                if final_name != new_name:
                    remarks.append(f"同名不覆盖，实际写入 {final_name}")
                try:
                    copy_or_move(item.path, dest_path, do_move=do_move)
                    copied += 1
                    dest_hashes[item.sha256] = str(dest_path)
                    if status != "重复":
                        status = "待确认" if cls.pending or cls.main == UNKNOWN_FOLDER or item.sensitive else "已归档"
                    logs.append(f"复制 {item.rel} -> {dest_path.relative_to(output).as_posix()}")
                except FileExistsError as exc:
                    remarks.append(str(exc))
                    status = "待确认"
        else:
            dest_path = dest_dir / new_name
            remarks.append("plan 模式尚未复制")

        rec = ArchiveRecord(
            main=cls.main,
            sub=cls.sub,
            extra_sub=cls.extra_sub,
            template_required=spec.required_files if spec else "",
            actual_name=final_name if apply else new_name,
            new_name=new_name,
            original_name=item.name,
            owner=format_owners(spec.owners_roles if spec else "", cfg),
            naming_rule=spec.naming_rule if spec else "项目工号_项目名称_文件类型_日期",
            project_code=fields.get("code") or cfg.project_code,
            project_name=cfg.project_name,
            model=cfg.model,
            board=fields.get("board", ""),
            variant=fields.get("variant", ""),
            quantity=fields.get("qty") or cfg.quantity,
            version=fields.get("version", ""),
            date=fields.get("date") or cfg.date_yyyymmdd(),
            source_path=str(item.path),
            archive_path=str(dest_path),
            sha256=item.sha256,
            status=status,
            remarks=remarks,
            sensitive=item.sensitive,
            confidence=cls.confidence,
            rel=item.rel,
        )
        records.append(rec)

    missing = build_missing(cfg, records)
    pending = [r for r in records if r.status == "待确认"]
    for r in records:
        if r.status == "已归档" and any("需" in x and "确认" in x for x in r.remarks):
            if r not in pending:
                pending.append(r)
    duplicates = [r for r in records if r.status == "重复"]
    sensitive = [r for r in records if r.sensitive]

    all_index = list(records) + [m for m in missing]
    number_records(all_index)
    number_records(missing)
    number_records(pending)
    number_records(duplicates)

    if write_outputs:
        write_table(output, "00_归档索引", [r.to_row() for r in all_index], "归档索引")
        write_table(output, "00_缺失资料清单", [r.to_row() for r in missing], "缺失资料")
        write_table(output, "00_待确认清单", [r.to_row() for r in pending], "待确认")
        write_table(output, "00_重复文件清单", [r.to_row() for r in duplicates], "重复文件")

        mode = "apply" if apply else "plan"
        write_report(
            output / "00_归档报告.md",
            cfg,
            mode=mode,
            source=source,
            output=output,
            files=records,
            missing=missing,
            pending=pending,
            duplicates=duplicates,
            sensitive=sensitive,
            logs=logs,
            copied=copied,
        )
        logs.append("已写入 00_归档索引 / 缺失 / 待确认 / 重复 / 归档报告")

        if apply and make_zip:
            name = f"项目归档包_{cfg.display_name()}_{cfg.date_yyyymmdd()}.zip"
            zip_path = output / name
            zip_output(output, zip_path)
            logs.append(f"已生成压缩包 {name}")
            report = output / "00_归档报告.md"
            with report.open("a", encoding="utf-8") as f:
                f.write(f"\n- 压缩包：`{zip_path}`\n")
    else:
        logs.append("网页预览：未写盘、未复制")

    return RunResult(
        output=output,
        records=records,
        missing=missing,
        pending=pending,
        duplicates=duplicates,
        copied=copied,
        logs=logs,
    )


def result_payload(result: RunResult, cfg: ProjectConfig) -> dict:
    """给网页的 JSON。"""
    archived = [r for r in result.records if r.status == "已归档"]

    def rec_dict(r: ArchiveRecord) -> dict:
        folder = "/".join(p for p in (r.main, r.sub, r.extra_sub) if p)
        return {
            "id": r.rel or r.original_name,
            "rel": r.rel,
            "original_name": r.original_name,
            "new_name": r.new_name,
            "actual_name": r.actual_name,
            "main": r.main,
            "sub": r.sub,
            "extra_sub": r.extra_sub,
            "folder": folder,
            "owner": r.owner,
            "status": r.status,
            "confidence": r.confidence,
            "reason": r.remark_text(),
            "sensitive": r.sensitive,
            "duplicate": r.status == "重复",
            "source_path": r.source_path,
            "archive_path": r.archive_path,
            "sha256": r.sha256,
            "naming_rule": r.naming_rule,
        }

    return {
        "output": str(result.output),
        "copied": result.copied,
        "stats": {
            "total": len(result.records),
            "classified": len(archived),
            "pending": len(result.pending),
            "duplicate": len(result.duplicates),
            "sensitive": sum(1 for r in result.records if r.sensitive),
            "missing": sum(1 for m in result.missing if m.status == "缺失"),
            "maybe_required": sum(1 for m in result.missing if m.status == "待确认"),
        },
        "files": [rec_dict(r) for r in result.records],
        "missing": [rec_dict(m) if m.rel or m.original_name else {
            "id": f"{m.main}/{m.sub}",
            "original_name": "",
            "new_name": "",
            "main": m.main,
            "sub": m.sub,
            "extra_sub": m.extra_sub,
            "folder": "/".join(p for p in (m.main, m.sub) if p),
            "owner": m.owner,
            "status": m.status,
            "confidence": 0,
            "reason": m.remark_text(),
            "sensitive": False,
            "template_required": m.template_required,
            "board": m.board,
            "variant": m.variant,
        } for m in result.missing],
        "logs": result.logs,
        "project": {
            "project_name": cfg.project_name,
            "project_code": cfg.project_code,
            "model": cfg.model,
        },
    }
