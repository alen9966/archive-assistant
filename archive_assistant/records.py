"""归档记录与缺失检查。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from archive_assistant.catalog import REQUIRED_MATRIX_KEYS, STANDARD_FOLDERS, spec_by_matrix_key
from archive_assistant.config import ProjectConfig, format_owners


@dataclass
class ArchiveRecord:
    seq: int = 0
    main: str = ""
    sub: str = ""
    extra_sub: str = ""
    template_required: str = ""
    actual_name: str = ""
    new_name: str = ""
    original_name: str = ""
    owner: str = ""
    naming_rule: str = ""
    project_code: str = ""
    project_name: str = ""
    model: str = ""
    board: str = ""
    variant: str = ""
    quantity: str = ""
    version: str = ""
    date: str = ""
    source_path: str = ""
    archive_path: str = ""
    sha256: str = ""
    status: str = ""
    remarks: list[str] = field(default_factory=list)
    sensitive: bool = False
    confidence: int = 0
    rel: str = ""

    def remark_text(self) -> str:
        return "；".join(x for x in self.remarks if x)

    def to_row(self) -> dict[str, str]:
        return {
            "序号": str(self.seq),
            "主文件夹": self.main,
            "子文件夹": "/".join(p for p in (self.sub, self.extra_sub) if p),
            "模板要求文件": self.template_required,
            "实际文件名": self.actual_name,
            "新文件名": self.new_name,
            "原文件名": self.original_name,
            "负责人": self.owner,
            "模板命名规范": self.naming_rule,
            "项目工号": self.project_code,
            "项目名称": self.project_name,
            "型号": self.model,
            "板号": self.board,
            "装配变量": self.variant,
            "套数": self.quantity,
            "版本": self.version,
            "日期": self.date,
            "来源路径": self.source_path,
            "归档路径": self.archive_path,
            "文件哈希": self.sha256,
            "状态": self.status,
            "备注": self.remark_text(),
        }


def _matrix_units(cfg: ProjectConfig) -> list[tuple[str, str, str]]:
    """(board, variant, qty) 组合。不编造缺失的维度，用待确认占位。"""
    boards = cfg.boards or ["待确认"]
    variants = cfg.assembly_variants or []
    variant_labels = [v.name or v.code or "待确认" for v in variants] or ["待确认"]
    qty = cfg.quantity or "待确认"
    units = []
    for b in boards:
        for v in variant_labels:
            units.append((b, v, qty))
    return units


def _has_file(records: list[ArchiveRecord], *, main: str, sub: str, board: str = "", variant: str = "") -> bool:
    for r in records:
        if r.status in ("缺失",):
            continue
        if r.main != main or r.sub != sub:
            continue
        if r.status == "待确认" and not r.source_path:
            continue
        if not r.source_path and r.status != "已归档":
            continue
        if board and board != "待确认" and r.board and r.board != board:
            continue
        if variant and variant != "待确认" and r.variant and r.variant != variant:
            continue
        if r.source_path:
            return True
    return False


def build_missing(cfg: ProjectConfig, file_records: list[ArchiveRecord]) -> list[ArchiveRecord]:
    missing: list[ArchiveRecord] = []
    na = set(cfg.not_applicable)
    units = _matrix_units(cfg)

    # 12 类矩阵
    for key in REQUIRED_MATRIX_KEYS:
        spec = spec_by_matrix_key(key)
        if spec is None:
            continue
        label = f"{spec.main}/{spec.sub}"
        if label in na or spec.sub in na or key in na:
            missing.append(
                ArchiveRecord(
                    main=spec.main,
                    sub=spec.sub,
                    template_required=spec.required_files,
                    owner=format_owners(spec.owners_roles, cfg),
                    naming_rule=spec.naming_rule,
                    project_code=cfg.project_code,
                    project_name=cfg.project_name,
                    model=cfg.model,
                    quantity=cfg.quantity,
                    date=cfg.date_yyyymmdd(),
                    status="不适用",
                    remarks=["配置标记为不适用"],
                )
            )
            continue
        scope = spec.matrix_scope
        if scope == "board_variant":
            checks = units
        elif scope == "board":
            seen = []
            checks = []
            for b, v, q in units:
                if b not in seen:
                    seen.append(b)
                    checks.append((b, "", q))
        else:
            checks = [("", "", cfg.quantity or "待确认")]

        for board, variant, qty in checks:
            found = _has_file(file_records, main=spec.main, sub=spec.sub, board=board, variant=variant)
            # 三防多媒体：看 07 多媒体里是否有三防前/后
            if key == "三防多媒体记录":
                found = any(
                    r.source_path
                    and r.sub == "多媒体记录"
                    and (r.extra_sub in ("三防前", "三防后") or "三防" in (r.original_name + r.new_name))
                    for r in file_records
                ) or found
            if found:
                continue
            remarks = [f"矩阵必查项缺失：{key}"]
            if board == "待确认" and not cfg.boards:
                remarks.append("配置未提供板号，未编造")
            missing.append(
                ArchiveRecord(
                    main=spec.main,
                    sub=spec.sub,
                    template_required=spec.required_files,
                    owner=format_owners(spec.owners_roles, cfg),
                    naming_rule=spec.naming_rule,
                    project_code=cfg.project_code,
                    project_name=cfg.project_name,
                    model=cfg.model,
                    board=board,
                    variant=variant,
                    quantity=qty,
                    date=cfg.date_yyyymmdd(),
                    status="缺失",
                    remarks=remarks,
                )
            )

    covered = {(m.main, m.sub) for m in missing}
    covered |= {(r.main, r.sub) for r in file_records if r.source_path}
    for spec in STANDARD_FOLDERS:
        if spec.matrix_key:
            continue
        if (spec.main, spec.sub) in covered:
            continue
        label = f"{spec.main}/{spec.sub}"
        if label in na or spec.sub in na:
            status = "不适用"
            remarks = ["配置标记为不适用"]
        else:
            status = "待确认"
            remarks = ["待确认是否必交"]
            if spec.required_files.strip() in ("", "/"):
                remarks.append("模板包含文件为空白或 /，不视为必交")
        missing.append(
            ArchiveRecord(
                main=spec.main,
                sub=spec.sub,
                template_required=spec.required_files,
                owner=format_owners(spec.owners_roles, cfg),
                naming_rule=spec.naming_rule,
                project_code=cfg.project_code,
                project_name=cfg.project_name,
                model=cfg.model,
                quantity=cfg.quantity,
                date=cfg.date_yyyymmdd(),
                status=status,
                remarks=remarks,
            )
        )
    return missing


def number_records(records: list[ArchiveRecord]) -> None:
    for i, r in enumerate(records, 1):
        r.seq = i
