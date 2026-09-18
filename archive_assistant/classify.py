"""按文件夹名、关键词与扩展名分类。低置信度入 99，不硬塞。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from archive_assistant.catalog import MEDIA_STAGES, UNKNOWN_FOLDER, spec_by_path
from archive_assistant.scan import SourceFile

MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".heic", ".mp4", ".mov", ".avi", ".mkv", ".wmv"}
PCB_EXTS = {
    ".pcbdoc",
    ".pcb",
    ".prjpcb",
    ".pcbdwf",
    ".dwf",
    ".gbr",
    ".gerber",
    ".gtl",
    ".gbl",
    ".gto",
    ".gts",
    ".gbs",
    ".gbo",
    ".gm1",
    ".gd1",
    ".gg1",
    ".drl",
    ".art",
}
SCH_EXTS = {".schdoc", ".sch", ".schdot"}
LIB_SCH_EXTS = {".schlib", ".intlib"}
LIB_PCB_EXTS = {".pcblib"}
ARCHIVE_EXTS = {".rar", ".zip", ".7z"}
TABLE_EXTS = {".xlsx", ".xls", ".csv"}
COAT_EXTS = {".pdf", ".dwg", ".dxf", ".png", ".jpg", ".jpeg"}
BOARD_STEM_RE = re.compile(r"^Z?C\d+[._]\d+[._]\d+(?:[-_]V[\d.]+)?$", re.I)
FW_EXTS = {".bin", ".hex", ".axf", ".elf", ".out"}

# 需求第五节关键词表 + 硬件常见资料别名。单独 PDF 不作为原理图依据。
RULES: list[tuple[str, str, str, tuple[str, ...], int]] = [
    # main, sub, extra_sub, keywords, weight
    ("09_售后", "维修单", "", ("维修单",), 90),
    ("09_售后", "维修后测试记录", "", ("维修后测试记录", "维修后测试"), 90),
    ("09_售后", "产品配置参数记录", "", ("配置参数记录", "配置参数"), 80),
    ("08_项目总结", "项目总结会议纪要", "", ("会议纪要", "项目总结"), 85),
    ("07_出厂资料", "发货记录", "", ("发货单", "发货记录", "checklist"), 80),
    ("07_出厂资料", "测试相关协议", "", ("相关协议", "测试协议"), 75),
    ("07_出厂资料", "测试大纲", "", ("测试大纲",), 85),
    ("07_出厂资料", "检验报告", "", ("检验报告",), 80),
    ("07_出厂资料", "产品说明书", "", ("产品说明书", "产品手册"), 80),
    ("07_出厂资料", "设备及板卡类说明书相关图片存档", "", ("实物图", "web图", "界面图"), 80),
    ("07_出厂资料", "多媒体记录", "", ("多媒体记录", "电装完", "三防前", "三防后", "发货前"), 70),
    ("06_成品检验", "试验报告", "", ("高低温工作试验报告", "高低温", "环境试验报告", "环境试验"), 85),
    ("06_成品检验", "测试记录", "", ("常规测试记录表", "常规测试", "成品测试记录"), 80),
    ("05_生产调试", "08_调试&自测记录", "", ("调试记录表", "调试记录", "自测记录"), 85),
    ("05_生产调试", "07_整机装配&检验", "", ("整机装配记录表", "整机装配记录"), 90),
    ("05_生产调试", "05_印制板装配外协&检验", "", ("单板测试记录表", "单板测试记录", "单板测试", "电装检验"), 88),
    ("05_生产调试", "01_元器件采购&检验", "", ("关重件", "元器件检验", "元器件采购"), 80),
    ("05_生产调试", "00_质量跟踪卡", "", ("质量跟踪卡", "履历表"), 90),
    ("05_生产调试", "03_结构外协&检验", "", ("结构件入厂", "质量问题反馈单", "结构外协"), 80),
    ("05_生产调试", "04_物料齐套缺件表", "", ("缺件表", "齐套"), 80),
    ("05_生产调试", "02_印制板外协&检验", "", ("印制板外协", "丝印"), 70),
    ("05_生产调试", "06_三防外协&检验", "", ("三防外协",), 80),
    ("03_硬件&结构设计", "07_领料单", "", ("领料单",), 95),
    ("03_硬件&结构设计", "02_采购清单", "", ("采购清单", "bom表", "物料清单", "bom"), 92),
    ("03_硬件&结构设计", "08_三防图", "", ("三防图", "三防图纸"), 95),
    ("03_硬件&结构设计", "06_整机接线图", "", ("整机接线图", "接线图", "接线表"), 85),
    ("03_硬件&结构设计", "05_装配文件", "阻容表", ("外协阻容备料", "外协阻容清单", "阻容备料清单", "阻容备料", "阻容清单", "阻容表"), 94),
    ("03_硬件&结构设计", "05_装配文件", "装配清单", ("装配清单",), 92),
    ("03_硬件&结构设计", "05_装配文件", "装配图", ("装配图",), 92),
    ("03_硬件&结构设计", "05_装配文件", "坐标文件", ("坐标文件夹", "坐标文件", "pickup", "centroid"), 92),
    ("03_硬件&结构设计", "05_装配文件", "钢网", ("钢网",), 90),
    ("03_硬件&结构设计", "04_结构图纸", "", ("结构图纸", "结构图", "三维", "二维", "结构清单"), 75),
    ("03_硬件&结构设计", "01_原理图", "", ("原理图", "schdoc", "schematic prints", "schematic"), 90),
    ("03_硬件&结构设计", "03_PCB", "Gerber", ("gerber", "光绘"), 90),
    ("03_硬件&结构设计", "03_PCB", "", ("pcbdoc",), 85),
    ("04_软件设计", "软件程序", "", ("固件", "boot_", "软件程序", "下载程序", "网络升级"), 80),
    ("02_方案设计", "硬件方案", "", ("硬件方案", "方案设计"), 80),
    ("01_任务书", "生产开发计划", "", ("生产开发计划", "任务书"), 85),
    ("00_需求确认", "设计相关资料", "", ("规格书", "铷钟"), 70),
    ("00_需求确认", "技术要求", "", ("技术要求", "需求规格"), 75),
]

# 源目录里的文件夹名（由内向外匹配）。整夹丢进来时靠这个识别。
FOLDER_HINTS: list[tuple[tuple[str, ...], str, str, str, str, int]] = [
    (("外协阻容备料", "外协阻容清单", "阻容备料", "阻容清单", "阻容表", "阻容"), "03_硬件&结构设计", "05_装配文件", "阻容表", "阻容表", 94),
    (("lib", "library"), "03_硬件&结构设计", "01_原理图", "库", "库", 93),
    (("坐标文件夹", "坐标文件", "坐标", "pickup", "centroid", "xy"), "03_硬件&结构设计", "05_装配文件", "坐标文件", "坐标文件", 93),
    (("装配清单",), "03_硬件&结构设计", "05_装配文件", "装配清单", "装配清单", 93),
    (("装配图",), "03_硬件&结构设计", "05_装配文件", "装配图", "装配图", 93),
    (("钢网", "钢网文件"), "03_硬件&结构设计", "05_装配文件", "钢网", "钢网文件", 92),
    (("gerber", "gerbers", "光绘"), "03_硬件&结构设计", "03_PCB", "Gerber", "Gerber", 93),
    (("原理图", "schematic", "schematic prints", "sch"), "03_硬件&结构设计", "01_原理图", "", "原理图", 93),
    (("采购清单", "bom表", "物料清单", "bom"), "03_硬件&结构设计", "02_采购清单", "", "采购清单", 94),
    (("单板测试记录表", "单板测试记录", "单板测试"), "05_生产调试", "05_印制板装配外协&检验", "", "单板测试记录表", 93),
    (("三防图", "三防图纸"), "03_硬件&结构设计", "08_三防图", "", "三防图", 95),
    (("pcb", "pcb图", "印制板"), "03_硬件&结构设计", "03_PCB", "", "PCB", 90),
]


@dataclass
class ClassifyResult:
    main: str
    sub: str
    extra_sub: str
    confidence: int
    reason: str
    file_type: str
    pending: bool


def _norm(text: str) -> str:
    return (text or "").replace("\\", "/").lower()


def _haystack(item: SourceFile) -> str:
    return _norm(item.rel + " " + item.name)


def _match_kw(hay: str, kw: str) -> bool:
    k = kw.lower()
    if k.endswith("_") or k.startswith("."):
        return k in hay
    return k in hay


def _folder_parts(rel: str) -> list[str]:
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if len(parts) <= 1:
        return []
    return parts[:-1]


def detect_media_stage(name: str) -> str:
    for stage in ("电装完", "三防前", "三防后", "发货前", "包装箱"):
        if stage in name:
            return stage
    return ""


def detect_file_type(name: str, main: str, sub: str, extra: str = "") -> str:
    mapping = [
        ("外协阻容备料", "阻容表"),
        ("阻容备料", "阻容表"),
        ("外协阻容清单", "阻容表"),
        ("阻容清单", "阻容表"),
        ("领料单", "领料单"),
        ("采购清单", "采购清单"),
        ("物料清单", "采购清单"),
        ("bom", "采购清单"),
        ("阻容表", "阻容表"),
        ("装配清单", "装配清单"),
        ("装配图", "装配图"),
        ("坐标文件夹", "坐标文件"),
        ("坐标文件", "坐标文件"),
        ("坐标", "坐标文件"),
        ("钢网", "钢网文件"),
        ("接线表", "接线表"),
        ("接线图", "接线图"),
        ("design rule check", "检查报告"),
        ("电气规则检查", "检查报告"),
        ("intlib", "库"),
        ("schlib", "库"),
        ("pcblib", "库"),
        ("导出表格", "导出表格"),
        ("project outputs", "工程输出存档"),
        ("三防图", "三防图"),
        ("三防.pdf", "三防图"),
        ("原理图", "原理图"),
        ("gerber", "Gerber"),
        ("光绘", "Gerber"),
        ("单板测试记录", "单板测试记录表"),
        ("单板测试", "单板测试记录表"),
        ("调试记录", "调试记录表"),
        ("整机装配记录", "整机装配记录表"),
        ("常规测试", "常规测试记录表"),
        ("高低温", "高低温工作试验报告"),
        ("检验报告", "检验报告"),
        ("产品手册", "产品手册"),
        ("产品说明书", "产品手册"),
        ("测试大纲", "测试大纲"),
        ("相关协议", "相关协议"),
        ("会议纪要", "会议纪要"),
        ("配置参数", "配置参数记录"),
        ("维修单", "维修单"),
        ("发货", "发货记录"),
        ("checklist", "checklist"),
        ("实物图", "实物图"),
        ("web图", "web图"),
        ("界面图", "界面图"),
        ("履历表", "履历表"),
        ("质量跟踪卡", "质量跟踪卡"),
        ("关重件", "关重件检验记录"),
        ("生产开发计划", "生产开发计划"),
        ("硬件方案", "硬件方案"),
        ("技术要求", "技术要求"),
    ]
    lower = name.lower()
    for kw, typ in mapping:
        if kw.lower() in lower or kw in name:
            return typ
    if extra:
        return extra
    if sub:
        return sub
    return "资料"


def _looks_like_bom(text: str) -> bool:
    hay = _norm(text)
    if any(m in hay for m in ("采购清单", "bom表", "物料清单")):
        return True
    return bool(re.search(r"(^|[/_\s.-])bom($|[/_\s.-]|表)", hay))


def _from_folder(item: SourceFile) -> ClassifyResult | None:
    """整夹丢入时，优先看路径里的文件夹名（由内向外）。"""
    best: ClassifyResult | None = None
    best_depth = -1
    folders = _folder_parts(item.rel)
    for depth, raw in enumerate(folders):
        part = _norm(raw)
        for aliases, main, sub, extra, ftype, conf in FOLDER_HINTS:
            hit = ""
            for alias in sorted(aliases, key=len, reverse=True):
                a = alias.lower()
                if len(a) <= 3 and a.isascii():
                    matched = part == a or part == a + "s"
                else:
                    matched = part == a or a in part
                if not matched:
                    continue
                if a == "pcb" and _looks_like_bom(raw):
                    continue
                hit = alias
                break
            if not hit:
                continue
            cand = ClassifyResult(
                main,
                sub,
                extra,
                conf,
                f"源文件夹「{raw}」",
                ftype,
                False,
            )
            if depth >= best_depth and (best is None or cand.confidence >= best.confidence):
                best = cand
                best_depth = depth
    return best


def _in_sch_path(rel: str) -> bool:
    p = _norm(rel)
    return "原理图" in p or "/sch/" in f"/{p}/" or p.startswith("sch/") or "/schlib/" in f"/{p}/"


def _in_pcb_path(rel: str) -> bool:
    p = _norm(rel)
    return "/pcb/" in f"/{p}/" or p.startswith("pcb/") or "pcb图" in p or "印制板" in p


def _from_special(item: SourceFile) -> ClassifyResult | None:
    """硬件工程常见别名：库、DRC、工程输出存档、PCBDwf、导出表、三防.pdf。"""
    ext = item.path.suffix.lower()
    name = item.name
    stem = Path(name).stem
    hay = _haystack(item)
    rel = item.rel

    if ext in LIB_SCH_EXTS:
        reason = ".IntLib 为原理图与PCB共用集成库" if ext == ".intlib" else "原理图库 SchLib"
        return ClassifyResult("03_硬件&结构设计", "01_原理图", "库", 95, reason, "库", False)
    if ext in LIB_PCB_EXTS:
        return ClassifyResult("03_硬件&结构设计", "03_PCB", "库", 95, "PCB 封装库 PcbLib", "库", False)

    if ext == ".pcbdwf":
        return ClassifyResult("03_硬件&结构设计", "03_PCB", "", 94, "PCBDwf 为 PCB 文件", "PCB", False)

    if ext in ARCHIVE_EXTS and "project outputs" in hay:
        return ClassifyResult(
            "03_硬件&结构设计",
            "03_PCB",
            "工程输出存档",
            94,
            "Project Outputs 压缩包为工程输出存档",
            "工程输出存档",
            False,
        )

    if "design rule check" in hay or "设计规则检查" in name:
        if _in_sch_path(rel) or "electrical" in hay:
            return ClassifyResult("03_硬件&结构设计", "01_原理图", "检查报告", 93, "原理图规则检查", "检查报告", False)
        return ClassifyResult("03_硬件&结构设计", "03_PCB", "检查报告", 93, "PCB Design Rule Check", "检查报告", False)
    if "electrical rule" in hay or "电气规则检查" in name:
        return ClassifyResult("03_硬件&结构设计", "01_原理图", "检查报告", 93, "原理图电气规则检查", "检查报告", False)

    if ext in COAT_EXTS and not any(x in name for x in ("三防前", "三防后", "三防外协")):
        if stem in {"三防", "三防图"} or stem.endswith("_三防") or stem.endswith("-三防") or stem.endswith("三防图"):
            return ClassifyResult("03_硬件&结构设计", "08_三防图", "", 96, "三防图", "三防图", False)

    if ext in TABLE_EXTS and BOARD_STEM_RE.match(stem or ""):
        return ClassifyResult(
            "03_硬件&结构设计",
            "03_PCB",
            "导出表格",
            88,
            "板号同名导出表格",
            "导出表格",
            False,
        )
    return None


def _from_ext(item: SourceFile) -> ClassifyResult | None:
    ext = item.path.suffix.lower()
    name = item.name
    hay = _haystack(item)
    if ext in SCH_EXTS or "原理图" in name:
        return ClassifyResult("03_硬件&结构设计", "01_原理图", "", 92, "原理图/原理图扩展名", "原理图", False)
    if _looks_like_bom(name):
        return None
    if ext in PCB_EXTS:
        extra = "Gerber" if ext not in {".pcbdoc", ".pcb", ".prjpcb", ".pcbdwf"} else ""
        ftype = "Gerber" if extra else "PCB"
        return ClassifyResult("03_硬件&结构设计", "03_PCB", extra, 90, f"PCB/Gerber 扩展名 {ext}", ftype, False)
    if re.search(r"(^|[/_\s.-])pcb($|[/_\s.-])", hay) and "采购" not in name and not _looks_like_bom(hay):
        return ClassifyResult("03_硬件&结构设计", "03_PCB", "", 86, "路径或文件名含 PCB", "PCB", False)
    if ext in FW_EXTS or name.upper().startswith("BOOT_") or "固件" in name:
        return ClassifyResult("04_软件设计", "软件程序", "", 88, "固件/BOOT/bin", "软件程序", False)
    return None


def _from_keywords(item: SourceFile) -> ClassifyResult | None:
    hay = _haystack(item)
    name = item.name
    best: ClassifyResult | None = None
    for main, sub, extra, kws, weight in RULES:
        for kw in kws:
            if _match_kw(hay, kw):
                pending = weight < 60
                ftype = detect_file_type(name, main, sub, extra)
                cand = ClassifyResult(main, sub, extra, weight, f"关键词「{kw}」", ftype, pending)
                if best is None or cand.confidence > best.confidence:
                    best = cand
                break
    return best


def classify_override(item: SourceFile, main: str, sub: str, extra_sub: str = "") -> ClassifyResult:
    """网页用户指定分类；非法目录回退自动分类。"""
    if main == UNKNOWN_FOLDER or not main:
        return ClassifyResult(
            UNKNOWN_FOLDER,
            "",
            "",
            100,
            "用户指定：无法分类/待确认",
            detect_file_type(item.name, "", ""),
            True,
        )
    spec = spec_by_path(main, sub)
    if spec is None:
        auto = classify_file(item)
        return ClassifyResult(
            auto.main,
            auto.sub,
            auto.extra_sub,
            auto.confidence,
            auto.reason + "；网页改分类无效已回退自动识别",
            auto.file_type,
            auto.pending,
        )
    extra = extra_sub
    if spec.sub == "多媒体记录" and extra not in (*MEDIA_STAGES, "待确认", ""):
        extra = extra or "待确认"
    pending = spec.sub == "多媒体记录" and extra in ("", "待确认")
    ftype = detect_file_type(item.name, main, sub, extra)
    return ClassifyResult(main, sub, extra, 100, "用户在网页中指定分类", ftype, pending)


def classify_file(item: SourceFile) -> ClassifyResult:
    special = _from_special(item)
    folder = _from_folder(item)
    named = _from_keywords(item)
    exted = _from_ext(item)

    best: ClassifyResult | None = None
    for cand in (special, folder, named, exted):
        if cand is None:
            continue
        if best is None or cand.confidence > best.confidence:
            best = cand
        elif cand.confidence == best.confidence and named is cand and folder is not None:
            # 同置信度时，文件名关键词比父文件夹更具体（如 PCB/采购清单.xlsx）
            best = cand

    # 多媒体：图片视频 + 阶段词，或落在多媒体分类后补阶段
    hay = _haystack(item)
    name = item.name
    ext = item.path.suffix.lower()
    stage = detect_media_stage(name + hay)
    if stage and ext in MEDIA_EXTS:
        extra = stage
        best = ClassifyResult(
            "07_出厂资料",
            "多媒体记录",
            extra,
            max(best.confidence if best else 0, 80),
            f"多媒体阶段「{stage}」",
            f"多媒体记录_{stage}",
            False,
        )
    elif best and best.sub == "多媒体记录":
        extra = stage or "待确认"
        best = ClassifyResult(best.main, best.sub, extra, best.confidence, best.reason, best.file_type, extra == "待确认")
    elif ext in MEDIA_EXTS and (best is None or best.confidence < 70):
        extra = stage or "待确认"
        best = ClassifyResult(
            "07_出厂资料",
            "多媒体记录",
            extra,
            45,
            "图片/视频扩展名，阶段未识别",
            "多媒体记录",
            True,
        )

    if best is None or best.confidence < 55:
        reason = "无法可靠分类" if best is None else f"置信度低（{best.confidence}）：{best.reason}"
        guessed_type = detect_file_type(name, "", "")
        return ClassifyResult(UNKNOWN_FOLDER, "", "", best.confidence if best else 0, reason, guessed_type or "待确认", True)

    spec = spec_by_path(best.main, best.sub)
    if spec is None and best.main != UNKNOWN_FOLDER:
        return ClassifyResult(UNKNOWN_FOLDER, "", "", 0, "分类结果不在标准目录", best.file_type, True)

    if "结构图纸" in name and best.sub == "多媒体记录":
        best = ClassifyResult("03_硬件&结构设计", "04_结构图纸", "", 80, "文件名含结构图纸", "结构图纸", False)

    return best
