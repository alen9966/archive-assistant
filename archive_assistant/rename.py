"""按模板命名规范生成新文件名。缺字段用「待确认」，不编造。"""

from __future__ import annotations

from pathlib import Path

from archive_assistant.catalog import UNKNOWN_FOLDER, spec_by_path
from archive_assistant.classify import ClassifyResult
from archive_assistant.config import ProjectConfig
from archive_assistant.names import (
    extract_board,
    extract_code,
    extract_date,
    extract_qty,
    extract_variant,
    extract_version,
    join_parts,
    parse_boot,
    placeholder,
    sanitize_filename,
)
from archive_assistant.scan import SourceFile


def _ext(name: str) -> str:
    return Path(name).suffix


def generate_name(
    item: SourceFile,
    cls: ClassifyResult,
    cfg: ProjectConfig,
) -> tuple[str, str, dict[str, str], list[str]]:
    """
    返回 (new_filename, archive_relpath_parent, fields, remarks)
    archive_relpath_parent 不含文件名。
    """
    remarks: list[str] = []
    text = item.rel + " " + item.name
    board = extract_board(text, cfg)
    code = extract_code(text, cfg) or cfg.project_code
    date_s, date_note = extract_date(text, cfg, fallback_archive=True)
    if date_note:
        remarks.append(date_note)
    qty = extract_qty(text, cfg)
    variant_name, variant_code = extract_variant(text, cfg)
    version = extract_version(item.name)
    model = cfg.model
    project = cfg.project_name
    ext = _ext(item.name)
    spec = spec_by_path(cls.main, cls.sub)
    naming = spec.naming_rule if spec else "项目工号_项目名称_文件类型_日期"

    fields = {
        "board": board,
        "code": code,
        "date": date_s,
        "qty": qty,
        "variant": variant_name,
        "variant_code": variant_code,
        "version": version,
        "model": model,
        "project": project,
        "file_type": cls.file_type,
    }

    def need(val: str, label: str) -> str:
        if val:
            return val
        remarks.append(f"{label}未提供，已填待确认")
        return "待确认"

    parent = f"{cls.main}/{cls.sub}" if cls.sub else cls.main
    if cls.extra_sub:
        parent = f"{parent}/{cls.extra_sub}"

    sub = cls.sub
    file_type = cls.file_type
    new_name = ""

    # 坐标文件夹 / Gerber 等成组资料：整夹放入对应子目录，保留原文件名，避免批量撞名。
    keep_original_extras = {"坐标文件", "Gerber", "钢网", "库", "工程输出存档", "导出表格", "检查报告"}
    if cls.extra_sub in keep_original_extras:
        new_name = sanitize_filename(item.name)
        remarks.append(f"成组资料「{cls.extra_sub}」保留原文件名，放入 {parent}")
        return new_name, parent.replace("\\", "/"), fields, remarks

    if cls.main == UNKNOWN_FOLDER:
        new_name = sanitize_filename(item.name)
        remarks.append("无法分类，保留原文件名（已清洗禁止字符）")
        return new_name, UNKNOWN_FOLDER, fields, remarks

    if sub == "01_原理图" or sub == "03_PCB":
        stem = need(board, "板号")
        new_name = sanitize_filename(stem + ext)
    elif sub in ("02_采购清单", "07_领料单") or file_type in ("采购清单", "领料单"):
        kind = "采购清单" if "采购" in (file_type + sub) else "领料单"
        new_name = join_parts(
            need(board, "板号"),
            need(variant_code or code, "工号/装配变量"),
            need(variant_name, "装配变量名称"),
            kind,
            need(qty, "套数"),
            date_s,
            ext=ext,
        )
    elif sub == "04_结构图纸":
        model_or_name = model or project
        if model:
            remarks.append("结构图纸优先使用型号（暂定默认，可改）")
        elif project:
            remarks.append("无型号，结构图纸使用项目名称（暂定默认，可改）")
        new_name = join_parts(
            need(code, "工号"),
            need(model_or_name, "型号或产品名称"),
            date_s,
            ext=ext,
        )
    elif sub == "05_装配文件":
        if file_type == "阻容表" and ("设备" in item.name or not board):
            new_name = join_parts(need(project, "设备名称"), "阻容表", need(qty, "套数"), date_s, ext=ext)
        elif file_type == "阻容表":
            new_name = join_parts(
                need(board, "板号"),
                need(variant_code or code, "工号/装配变量"),
                need(variant_name, "装配变量名称"),
                "阻容表",
                need(qty, "套数"),
                date_s,
                ext=ext,
            )
        elif file_type == "装配图":
            new_name = sanitize_filename(need(board, "板号") + "装配图" + ext)
        elif file_type == "坐标文件":
            new_name = sanitize_filename(need(board, "板号") + "坐标文件" + ext)
        elif file_type == "钢网文件":
            new_name = sanitize_filename(need(board, "板号") + "钢网文件" + ext)
        else:
            new_name = join_parts(
                need(board, "板号"),
                need(variant_code or code, "工号/装配变量"),
                need(variant_name, "装配变量名称"),
                "装配清单",
                qty,  # 套数可空，示例中装配清单可无套数
                date_s,
                ext=ext,
            )
    elif sub == "06_整机接线图":
        kind = "整机接线表" if "表" in file_type or "接线表" in item.name else "整机接线图"
        new_name = sanitize_filename(need(project, "项目名称") + kind + ext)
    elif sub == "08_三防图":
        new_name = join_parts(need(board, "板号"), "三防图", ext=ext)
    elif sub == "软件程序":
        boot = parse_boot(Path(item.name).stem) if item.name.upper().startswith("BOOT") or item.path.suffix.lower() == ".bin" else None
        fw_type = "固件"
        if "显示" in item.name:
            fw_type = "显示屏程序"
        elif boot:
            fw_type = "网络升级程序"
        folder = join_parts(need(code, "工号"), fw_type, cfg.date_yyyymmdd())
        parent = f"{cls.main}/{cls.sub}/{Path(folder).stem}"
        if item.name.upper().startswith("BOOT") or (boot and boot.get("user")):
            info = parse_boot(Path(item.name).stem)
            if info.get("note"):
                remarks.append(info["note"])
            user = info["user"] or "待确认"
            product = info["product"] or (model or project or "待确认")
            func = info["function"] or "待确认"
            bdate = info["date"] or date_s
            if user == "待确认" or func == "待确认":
                remarks.append("BOOT 用户/功能提取不到则待确认，不编造")
            new_name = join_parts("BOOT", user, product, func, bdate, ext=ext or ".bin")
        else:
            new_name = join_parts(need(code, "工号"), need(project, "项目名称"), fw_type, date_s, ext=ext)
    elif sub == "生产开发计划":
        new_name = sanitize_filename(need(project, "项目名称") + "生产开发计划" + ext)
    elif sub == "01_元器件采购&检验":
        # 元器件类型、数量从文件名尽量提取，否则待确认
        mtype = "元器件"
        for cand in ("电阻", "电容", "电感", "芯片", "晶振", "连接器", "关重件"):
            if cand in item.name:
                mtype = cand
                break
        else:
            remarks.append("元器件类型未从文件名提取到，已填待确认")
            mtype = "待确认"
        new_name = join_parts(need(code, "项目工号"), need(project, "项目名称"), mtype, need(qty, "数量"), ext=ext)
    elif sub == "03_结构外协&检验":
        new_name = join_parts(need(code, "项目工号"), need(project, "项目名称"), file_type or "结构外协", ext=ext)
    elif sub == "05_印制板装配外协&检验":
        new_name = join_parts(need(board, "板号"), "单板测试记录表", ext=ext)
    elif sub == "07_整机装配&检验":
        new_name = join_parts(need(code, "项目工号"), need(project, "项目名称"), "整机装配记录表", ext=ext)
    elif sub == "08_调试&自测记录":
        new_name = join_parts(need(code, "项目工号"), need(project, "项目名称"), "调试记录表", ext=ext)
    elif sub == "测试记录" or sub == "维修后测试记录":
        new_name = join_parts(need(model, "型号"), need(project, "项目名称"), "常规测试记录表", ext=ext)
    elif sub == "试验报告":
        new_name = join_parts(need(project, "项目名称"), "高低温工作试验报告", ext=ext)
    elif sub == "检验报告":
        new_name = join_parts(need(project, "项目名称"), "检验报告", ext=ext)
    elif sub == "产品说明书":
        new_name = join_parts(need(project, "项目名称"), "产品手册", ext=ext)
        remarks.append("产品手册是否按客户要求，待确认")
    elif sub == "设备及板卡类说明书相关图片存档":
        kind = file_type if file_type in ("实物图", "web图", "界面图") else "说明书图片"
        new_name = join_parts(need(project, "项目名称"), kind, ext=ext)
    elif sub == "测试大纲":
        new_name = join_parts(need(project, "项目名称"), "测试大纲", ext=ext)
    elif sub == "测试相关协议":
        new_name = join_parts(need(project, "项目名称"), "相关协议", ext=ext)
    elif sub == "项目总结会议纪要":
        new_name = join_parts(need(project, "项目名称"), "会议纪要", ext=ext)
        remarks.append("会议需确认待补充文件及相应完成时间")
    elif sub == "产品配置参数记录":
        new_name = join_parts(need(project, "项目名称"), "配置参数记录", ext=ext)
    elif sub == "维修单":
        new_name = join_parts(need(code, "工号"), need(project, "项目名称"), "维修单", ext=ext)
        remarks.append("模板原文无下划线，已按可读性补下划线，可改回")
    elif sub == "发货记录" or sub == "多媒体记录":
        kind = file_type or sub
        if cls.extra_sub and cls.extra_sub != "待确认":
            kind = f"{sub}_{cls.extra_sub}"
        new_name = join_parts(need(code, "项目工号"), need(project, "项目名称"), kind, date_s, ext=ext)
        remarks.append("模板无专名，已用默认命名（暂定默认，可改）")
    else:
        # 模板无规范
        new_name = join_parts(
            need(code, "项目工号"),
            need(project, "项目名称"),
            file_type or sub or "资料",
            date_s,
            ext=ext,
        )
        if not naming:
            remarks.append("模板无命名规范，已用 项目工号_项目名称_文件类型_日期（暂定默认，可改）")

    fields["board"] = board
    fields["code"] = code
    fields["date"] = date_s
    fields["qty"] = qty
    fields["variant"] = variant_name
    fields["version"] = version
    if new_name and "待确认" in Path(new_name).stem:
        new_name = sanitize_filename(item.name)
        remarks.append("缺少命名所需项目信息，已保留原文件名（不编造）")
    return sanitize_filename(new_name), parent.replace("\\", "/"), fields, remarks
