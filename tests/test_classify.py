from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from archive_assistant.classify import classify_file
from archive_assistant.config import load_config
from archive_assistant.pipeline import run_archive
from archive_assistant.scan import SourceFile


def touch(path: Path, data: bytes | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if data is not None else path.as_posix().encode("utf-8"))


def fake_item(rel: str) -> SourceFile:
    return SourceFile(
        path=Path(rel),
        rel=rel.replace("\\", "/"),
        name=Path(rel).name,
        sha256="0",
        size=1,
        sensitive=False,
    )


class FolderDropClassifyTests(unittest.TestCase):
    def test_folder_names_map_to_template(self) -> None:
        cases = {
            "原理图/ZC7.820.0001-V6.1.SchDoc": ("03_硬件&结构设计", "01_原理图", ""),
            "PCB/board.PcbDoc": ("03_硬件&结构设计", "03_PCB", ""),
            "BOM表/清单.xlsx": ("03_硬件&结构设计", "02_采购清单", ""),
            "采购清单/xxx.xlsx": ("03_硬件&结构设计", "02_采购清单", ""),
            "单板测试记录表/记录.xlsx": ("05_生产调试", "05_印制板装配外协&检验", ""),
            "三防图/coat.pdf": ("03_硬件&结构设计", "08_三防图", ""),
            "装配图/assy.pdf": ("03_硬件&结构设计", "05_装配文件", "装配图"),
            "外协阻容清单/rc.xlsx": ("03_硬件&结构设计", "05_装配文件", "阻容表"),
            "装配清单/kit.xlsx": ("03_硬件&结构设计", "05_装配文件", "装配清单"),
            "坐标文件夹/top.csv": ("03_硬件&结构设计", "05_装配文件", "坐标文件"),
            "随便叫啥/无法识别的杂项.dat": ("99_待确认与其他", "", ""),
            "lib/power.IntLib": ("03_硬件&结构设计", "01_原理图", "库"),
            "Pcb/Design Rule Check.html": ("03_硬件&结构设计", "03_PCB", "检查报告"),
            "Sch/Electrical Rules Check.html": ("03_硬件&结构设计", "01_原理图", "检查报告"),
            "Project Outputs for ZC7.820.0155-V3.rar": ("03_硬件&结构设计", "03_PCB", "工程输出存档"),
            "ZC7.820.0155-V3_1.PCBDwf": ("03_硬件&结构设计", "03_PCB", ""),
            "ZC7.820.0155-V3.xlsx": ("03_硬件&结构设计", "03_PCB", "导出表格"),
            "C7.820.0155-V3_外协阻容备料清单.xlsx": ("03_硬件&结构设计", "05_装配文件", "阻容表"),
            "三防.pdf": ("03_硬件&结构设计", "08_三防图", ""),
        }
        for rel, expected in cases.items():
            got = classify_file(fake_item(rel))
            self.assertEqual((got.main, got.sub, got.extra_sub), expected, rel)

    def test_filename_beats_pcb_folder_for_bom(self) -> None:
        got = classify_file(fake_item("PCB/授时守时板卡_采购清单.xlsx"))
        self.assertEqual(got.sub, "02_采购清单")

    def test_mixed_folder_apply(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="archive_mix_"))
        source = tmp / "src"
        output = tmp / "out"
        try:
            touch(source / "原理图" / "ZC7.820.0001-V6.1.SchDoc")
            touch(source / "PCB" / "ZC7.820.0001-V6.1.PcbDoc")
            touch(source / "BOM表" / "采购清单.xlsx")
            touch(source / "单板测试记录表" / "单板测试记录表.xlsx")
            touch(source / "三防图" / "三防图.pdf")
            touch(source / "装配图" / "装配图.pdf")
            touch(source / "外协阻容清单" / "外协阻容清单.xlsx")
            touch(source / "装配清单" / "装配清单.xlsx")
            touch(source / "坐标文件夹" / "top.csv")
            touch(source / "坐标文件夹" / "bot.csv")
            touch(source / "不知道放哪" / "杂项说明.dat", b"unknown-bytes")
            touch(source / "History" / "old.PcbDoc", b"altium-history-should-skip")
            cfg_text = """
project_name: 演示项目
project_code: ZCJY260101
model: DEMO-1
boards:
  - ZC7.820.0001-V6.1
assembly_variants:
  - name: 授时守时板卡
    code: ZCJY260101
quantity: 2套
archive_date: "20260918"
allow_move: false
"""
            cfg_path = tmp / "project.yaml"
            cfg_path.write_text(cfg_text, encoding="utf-8")
            cfg = load_config(cfg_path)
            result = run_archive(source=source, output=output, cfg=cfg, apply=True)
            self.assertGreaterEqual(result.copied, 11)
            self.assertTrue(list((output / "03_硬件&结构设计" / "01_原理图").glob("*.SchDoc")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "03_PCB").glob("*.PcbDoc")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "02_采购清单").glob("*")))
            self.assertTrue(list((output / "05_生产调试" / "05_印制板装配外协&检验").glob("*")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "08_三防图").glob("*")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "05_装配文件" / "装配图").glob("*")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "05_装配文件" / "阻容表").glob("*")))
            self.assertTrue(list((output / "03_硬件&结构设计" / "05_装配文件" / "装配清单").glob("*")))
            xy = output / "03_硬件&结构设计" / "05_装配文件" / "坐标文件"
            self.assertTrue((xy / "top.csv").is_file())
            self.assertTrue((xy / "bot.csv").is_file())
            self.assertTrue(list((output / "99_待确认与其他").glob("*杂项*")) or list((output / "99_待确认与其他").glob("*.dat")))
            self.assertTrue((source / "坐标文件夹" / "top.csv").is_file())
            self.assertFalse(list(output.rglob("old.PcbDoc")), "Altium History 不应归档")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
