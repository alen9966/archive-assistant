"""标准归档目录与模板项。主文件夹序号和名称必须与模板/需求原文一致。"""

from __future__ import annotations

from dataclasses import dataclass, field


UNKNOWN_FOLDER = "99_待确认与其他"

MEDIA_STAGES = ("电装完", "三防前", "三防后", "发货前", "包装箱")

# 成组资料子目录：整夹（如坐标文件夹、Gerber）丢进来后保持在对应子文件夹下
ASSEMBLY_EXTRAS = ("装配清单", "阻容表", "装配图", "坐标文件", "钢网")
PCB_EXTRAS = ("Gerber", "库", "检查报告", "工程输出存档", "导出表格")
SCH_EXTRAS = ("库", "检查报告")

# 板号-装配变量-套数矩阵必查 12 类（暂定默认，可改）
REQUIRED_MATRIX_KEYS = (
    "原理图",
    "采购清单",
    "PCB",
    "结构图纸",
    "装配文件",
    "整机接线图",
    "领料单",
    "三防图",
    "单板测试记录",
    "调试记录",
    "整机装配记录",
    "三防多媒体记录",
)


@dataclass(frozen=True)
class FolderSpec:
    main: str
    sub: str
    required_files: str
    owners_roles: str
    naming_rule: str
    remarks: str = ""
    matrix_key: str = ""  # 对应 12 类必查；空表示非矩阵必交
    matrix_scope: str = ""  # board / board_variant / project
    confirm_required: str = ""


STANDARD_FOLDERS: tuple[FolderSpec, ...] = (
    FolderSpec("00_需求确认", "技术要求", "技术要求", "硬件/质量", "", ""),
    FolderSpec(
        "00_需求确认",
        "设计相关资料",
        "设计相关资料",
        "硬件",
        "",
        "例：铷钟、电源等相关规格书",
    ),
    FolderSpec(
        "01_任务书",
        "生产开发计划",
        "生产开发计划",
        "硬件",
        "项目名称生产开发计划",
        "例：授时守时终端生产开发计划",
    ),
    FolderSpec("02_方案设计", "硬件方案", "硬件方案", "硬件", "", ""),
    FolderSpec(
        "03_硬件&结构设计",
        "01_原理图",
        "原理图",
        "硬件",
        "板号",
        "归档时需和对应负责人确认原理图+调试记录完整无问题",
        matrix_key="原理图",
        matrix_scope="board",
        confirm_required="需与硬件确认原理图+调试记录完整无问题",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "02_采购清单",
        "采购清单",
        "硬件",
        "板号_装配变量名称（工号_装配变量）_采购清单_套数_日期",
        "例：ZC7.820.0002-V1_ZCJY260101_授时守时板卡_采购清单_2套_20260405",
        matrix_key="采购清单",
        matrix_scope="board_variant",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "03_PCB",
        "PCB",
        "硬件",
        "板号",
        "例：ZC7_820_0001-V6.1.PCBDOC",
        matrix_key="PCB",
        matrix_scope="board",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "04_结构图纸",
        "结构图纸（包含二维、三维、结构清单及包装箱）",
        "王杰",
        "工号_型号/产品名称_日期",
        "例：ZCJY260101_B3T/0-10北三时统结构图纸_260403",
        matrix_key="结构图纸",
        matrix_scope="project",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "05_装配文件",
        "装配清单、阻容表、装配图、坐标文件、钢网文件",
        "硬件",
        "板号_装配变量名称（工号_装配变量）_装配清单_（套数）_日期；单板阻容表/设备阻容表/板号装配图/板号坐标文件/板号钢网文件",
        "",
        matrix_key="装配文件",
        matrix_scope="board_variant",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "06_整机接线图",
        "接线图、接线表",
        "硬件",
        "项目名称整机接线图 / 项目名称整机接线表",
        "",
        matrix_key="整机接线图",
        matrix_scope="project",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "07_领料单",
        "领料单",
        "硬件",
        "板号_装配变量名称（工号_装配变量）_领料单_套数_日期",
        "",
        matrix_key="领料单",
        matrix_scope="board_variant",
    ),
    FolderSpec(
        "03_硬件&结构设计",
        "08_三防图",
        "三防图",
        "硬件",
        "板号_三防图",
        "例：ZC7.820.0164-V2_三防图",
        matrix_key="三防图",
        matrix_scope="board",
    ),
    FolderSpec(
        "04_软件设计",
        "软件程序",
        "软件程序",
        "测试（归档）/软件（确认）",
        "固件文件夹：工号_文件类型_归档日期；下载程序：BOOT_（用户）_产品/名称_（功能）_日期.bin",
        "",
    ),
    FolderSpec(
        "05_生产调试",
        "00_质量跟踪卡",
        "履历表",
        "质量",
        "",
        "下载在线文档进行存档",
    ),
    FolderSpec(
        "05_生产调试",
        "01_元器件采购&检验",
        "关重件检验记录",
        "质量/测试",
        "项目工号_项目名称_元器件类型_数量",
        "",
    ),
    FolderSpec(
        "05_生产调试",
        "02_印制板外协&检验",
        "/",
        "质量",
        "",
        "目前主要是检查外观及丝印",
    ),
    FolderSpec(
        "05_生产调试",
        "03_结构外协&检验",
        "结构件入厂检验记录表、质量问题反馈单",
        "质量",
        "项目工号_项目名称",
        "",
    ),
    FolderSpec(
        "05_生产调试",
        "04_物料齐套缺件表",
        "/",
        "采购",
        "",
        "",
    ),
    FolderSpec(
        "05_生产调试",
        "05_印制板装配外协&检验",
        "电装检验记录",
        "硬件",
        "板号_单板测试记录表",
        "例如：ZC7.820.0164-V2_单板测试记录表",
        matrix_key="单板测试记录",
        matrix_scope="board",
    ),
    FolderSpec(
        "05_生产调试",
        "06_三防外协&检验",
        "见多媒体记录",
        "质量",
        "",
        "见 07_出厂资料/多媒体记录",
        matrix_key="三防多媒体记录",
        matrix_scope="project",
    ),
    FolderSpec(
        "05_生产调试",
        "07_整机装配&检验",
        "整机装配记录表",
        "硬件（输出）/生产（填写）/质量（扫描归档）",
        "项目工号_项目名称_整机装配记录表",
        "",
        matrix_key="整机装配记录",
        matrix_scope="project",
    ),
    FolderSpec(
        "05_生产调试",
        "08_调试&自测记录",
        "调试记录表",
        "硬件（填写）/质量（确认）",
        "项目工号_项目名称_调试记录表",
        "",
        matrix_key="调试记录",
        matrix_scope="project",
        confirm_required="需与硬件确认原理图+调试记录完整无问题",
    ),
    FolderSpec(
        "06_成品检验",
        "测试记录",
        "测试记录表",
        "测试",
        "型号_项目名称_常规测试记录表",
        "",
    ),
    FolderSpec(
        "06_成品检验",
        "试验报告",
        "环境试验报告",
        "测试/质量",
        "项目名称_高低温工作试验报告",
        "",
    ),
    FolderSpec(
        "07_出厂资料",
        "检验报告",
        "检验报告",
        "测试",
        "项目名称_检验报告",
        "",
    ),
    FolderSpec(
        "07_出厂资料",
        "产品说明书",
        "产品说明书",
        "测试",
        "项目名称_产品手册（看客户要求）",
        "无产品说明书要求需归档相应图片",
        confirm_required="无产品说明书要求时需归档相应图片",
    ),
    FolderSpec(
        "07_出厂资料",
        "设备及板卡类说明书相关图片存档",
        "实物图/web图/界面图",
        "测试/质量",
        "项目名称_实物图/web图/界面图",
        "最好是 word 形式",
    ),
    FolderSpec(
        "07_出厂资料",
        "测试大纲",
        "测试大纲",
        "测试",
        "项目名称_测试大纲",
        "",
    ),
    FolderSpec(
        "07_出厂资料",
        "测试相关协议",
        "相关协议",
        "测试",
        "项目名称_相关协议",
        "",
    ),
    FolderSpec(
        "07_出厂资料",
        "发货记录",
        "发货单、checklist",
        "质量",
        "项目工号_项目名称_文件类型_日期",
        "模板命名为 /，已用默认命名（暂定默认，可改）",
    ),
    FolderSpec(
        "07_出厂资料",
        "多媒体记录",
        "电装完/三防前/三防后/发货前；涉及包装箱的项目需包含包装箱所有图片",
        "质量",
        "项目工号_项目名称_文件类型_日期",
        "模板命名为 /，已用默认命名（暂定默认，可改）",
        confirm_required="涉及包装箱的项目需包含包装箱所有图片",
    ),
    FolderSpec(
        "08_项目总结",
        "项目总结会议纪要",
        "会议纪要",
        "质量",
        "项目名称_会议纪要",
        "会议需确认待补充文件及相应完成时间",
        confirm_required="会议需确认待补充文件及相应完成时间",
    ),
    FolderSpec(
        "09_售后",
        "产品配置参数记录",
        "产品配置参数记录",
        "质量/测试",
        "项目名称_配置参数记录",
        "",
    ),
    FolderSpec(
        "09_售后",
        "维修单",
        "维修单",
        "质量",
        "工号_项目名称_维修单",
        "模板原文为「工号_项目名称维修单」无下划线，已按可读性补下划线，可改回",
    ),
    FolderSpec(
        "09_售后",
        "维修后测试记录",
        "维修后测试记录",
        "测试",
        "型号_项目名称_常规测试记录表",
        "",
    ),
)


def main_folder_names() -> list[str]:
    names: list[str] = []
    for spec in STANDARD_FOLDERS:
        if spec.main not in names:
            names.append(spec.main)
    names.append(UNKNOWN_FOLDER)
    return names


def iter_directory_relpaths() -> list[str]:
    """创建目录用的相对路径（含子目录与多媒体阶段）。"""
    paths: list[str] = []
    seen: set[str] = set()

    def add(rel: str) -> None:
        rel = rel.replace("\\", "/").strip("/")
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)

    for spec in STANDARD_FOLDERS:
        add(spec.main)
        add(f"{spec.main}/{spec.sub}")
        if spec.sub == "多媒体记录":
            for stage in MEDIA_STAGES:
                add(f"{spec.main}/{spec.sub}/{stage}")
            add(f"{spec.main}/{spec.sub}/待确认")
        if spec.sub == "05_装配文件":
            for extra in ASSEMBLY_EXTRAS:
                add(f"{spec.main}/{spec.sub}/{extra}")
        if spec.sub == "03_PCB":
            for extra in PCB_EXTRAS:
                add(f"{spec.main}/{spec.sub}/{extra}")
        if spec.sub == "01_原理图":
            for extra in SCH_EXTRAS:
                add(f"{spec.main}/{spec.sub}/{extra}")
    add(UNKNOWN_FOLDER)
    return paths


def spec_by_path(main: str, sub: str) -> FolderSpec | None:
    for spec in STANDARD_FOLDERS:
        if spec.main == main and spec.sub == sub:
            return spec
    return None


def spec_by_matrix_key(key: str) -> FolderSpec | None:
    for spec in STANDARD_FOLDERS:
        if spec.matrix_key == key:
            return spec
    return None


def folder_options() -> list[dict[str, str]]:
    """网页下拉框：标准目录 + 多媒体阶段 + 99。"""
    opts: list[dict[str, str]] = []
    for spec in STANDARD_FOLDERS:
        path = f"{spec.main}/{spec.sub}"
        opts.append(
            {
                "main": spec.main,
                "sub": spec.sub,
                "extra_sub": "",
                "label": path,
                "owners": spec.owners_roles,
            }
        )
        extras: tuple[str, ...] = ()
        if spec.sub == "多媒体记录":
            extras = (*MEDIA_STAGES, "待确认")
        elif spec.sub == "05_装配文件":
            extras = ASSEMBLY_EXTRAS
        elif spec.sub == "03_PCB":
            extras = PCB_EXTRAS
        elif spec.sub == "01_原理图":
            extras = SCH_EXTRAS
        for extra in extras:
            opts.append(
                {
                    "main": spec.main,
                    "sub": spec.sub,
                    "extra_sub": extra,
                    "label": f"{path}/{extra}",
                    "owners": spec.owners_roles,
                }
            )
    opts.append(
        {
            "main": UNKNOWN_FOLDER,
            "sub": "",
            "extra_sub": "",
            "label": UNKNOWN_FOLDER,
            "owners": "",
        }
    )
    return opts


def parse_folder_label(label: str) -> tuple[str, str, str]:
    """把 '主/子/阶段' 解析为 (main, sub, extra_sub)。无法识别则进 99。"""
    text = (label or "").replace("\\", "/").strip().strip("/")
    if not text or text == UNKNOWN_FOLDER:
        return UNKNOWN_FOLDER, "", ""
    for opt in folder_options():
        if opt["label"] == text:
            return opt["main"], opt["sub"], opt["extra_sub"]
    parts = [p for p in text.split("/") if p]
    if not parts:
        return UNKNOWN_FOLDER, "", ""
    main = parts[0]
    sub = parts[1] if len(parts) > 1 else ""
    extra = "/".join(parts[2:]) if len(parts) > 2 else ""
    if main == UNKNOWN_FOLDER:
        return UNKNOWN_FOLDER, "", ""
    if spec_by_path(main, sub) is None:
        return UNKNOWN_FOLDER, "", ""
    return main, sub, extra
