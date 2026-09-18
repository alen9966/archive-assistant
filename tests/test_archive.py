from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from archive_assistant.catalog import iter_directory_relpaths
from archive_assistant.config import load_config, parse_simple_yaml
from archive_assistant.pipeline import run_archive


ROOT = Path(__file__).resolve().parents[1]


def write_file(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)


class YamlConfigTests(unittest.TestCase):
    def test_parse_example_yaml(self) -> None:
        cfg = load_config(ROOT / "project.example.yaml")
        self.assertEqual(cfg.project_name, "")
        self.assertFalse(cfg.allow_move)
        self.assertEqual(cfg.boards, [])

    def test_parse_filled_yaml(self) -> None:
        text = """
project_name: 演示项目
project_code: ZCJY260101
model: DEMO-1
boards:
  - ZC7.820.0001-V6.1
assembly_variants:
  - name: 授时守时板卡
    code: ZCJY260101
quantity: 2套
allow_move: false
owners:
  hardware: 张三
"""
        data = parse_simple_yaml(text)
        self.assertEqual(data["project_name"], "演示项目")
        self.assertEqual(data["boards"], ["ZC7.820.0001-V6.1"])
        self.assertEqual(data["assembly_variants"][0]["name"], "授时守时板卡")
        self.assertEqual(data["owners"]["hardware"], "张三")


class ArchiveFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="archive_asst_"))
        self.source = self.tmp / "src"
        self.output = self.tmp / "out"
        self.source.mkdir()
        write_file(self.source / "ZC7.820.0001-V6.1.SchDoc", b"sch")
        write_file(self.source / "授时守时板卡_采购清单.xlsx", b"bom")
        write_file(self.source / "生产开发计划.docx", b"plan")
        write_file(self.source / "BOOT_1U_VER6906_251127_v1.01.bin", b"fw" * 20)
        write_file(self.source / "电装完_现场.jpg", b"\xff\xd8\xff")
        write_file(self.source / "无法识别的杂项.dat", b"unknown-bytes")
        write_file(self.source / "售后维修单.docx", b"repair-form")
        write_file(self.source / "客户机密_说明.txt", "这是内部说明，不是真实密钥\n")
        write_file(self.source / "dup_a.txt", "same-hash-payload")
        write_file(self.source / "dup_b.txt", "same-hash-payload")
        write_file(self.source / "sub" / "密码口令备忘.txt", "fake password list\n")
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
archive_date: "20260917"
allow_move: false
confirm_move: false
owners:
  hardware: ""
  quality: ""
"""
        self.cfg_path = self.tmp / "project.yaml"
        self.cfg_path.write_text(cfg_text, encoding="utf-8")
        self.cfg = load_config(self.cfg_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _source_names(self) -> set[str]:
        return {p.name for p in self.source.rglob("*") if p.is_file()}

    def test_plan_creates_tree_and_reports_without_copy(self) -> None:
        before = {p.relative_to(self.source).as_posix(): p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        result = run_archive(source=self.source, output=self.output, cfg=self.cfg, apply=False)
        self.assertEqual(result.copied, 0)
        for rel in iter_directory_relpaths():
            self.assertTrue((self.output / Path(*rel.split("/"))).is_dir(), rel)
        for name in (
            "00_归档索引.xlsx",
            "00_归档索引.csv",
            "00_缺失资料清单.xlsx",
            "00_缺失资料清单.csv",
            "00_待确认清单.xlsx",
            "00_待确认清单.csv",
            "00_重复文件清单.xlsx",
            "00_重复文件清单.csv",
            "00_归档报告.md",
        ):
            self.assertTrue((self.output / name).is_file(), name)
        # 源文件仍在且内容未变
        after = {p.relative_to(self.source).as_posix(): p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        # plan 不把资料复制进分类目录
        copied_samples = list(self.output.rglob("*.SchDoc")) + list(self.output.rglob("无法识别的杂项.dat"))
        self.assertEqual(copied_samples, [])
        report = (self.output / "00_归档报告.md").read_text(encoding="utf-8")
        self.assertIn("暂定默认", report)
        self.assertIn("演示项目", report)

    def test_apply_copies_keeps_source_no_overwrite(self) -> None:
        before_src = self._source_names()
        plan = run_archive(source=self.source, output=self.output, cfg=self.cfg, apply=False)
        self.assertGreaterEqual(len(plan.records), 8)
        result = run_archive(source=self.source, output=self.output, cfg=self.cfg, apply=True)
        self.assertGreater(result.copied, 0)
        self.assertEqual(self._source_names(), before_src)
        # 原理图按板号归档
        sch_dir = self.output / "03_硬件&结构设计" / "01_原理图"
        schs = list(sch_dir.glob("*"))
        self.assertTrue(any(p.is_file() for p in schs), "原理图应被复制")
        # 无法分类进 99
        unknown = list((self.output / "99_待确认与其他").glob("*无法识别*")) + list(
            (self.output / "99_待确认与其他").glob("*.dat")
        )
        self.assertTrue(unknown, "无法分类应进入 99")
        # 多媒体阶段
        media = list((self.output / "07_出厂资料" / "多媒体记录" / "电装完").glob("*"))
        self.assertTrue(any(p.is_file() for p in media))
        # 重复哈希
        self.assertGreaterEqual(len(result.duplicates), 1)
        # 敏感标记
        self.assertTrue(any(r.sensitive for r in result.records))
        # 同名不覆盖：再 apply 一次，源仍在，已有文件不被替换成空
        sch_files = [p for p in sch_dir.iterdir() if p.is_file()]
        sizes = {p.name: p.stat().st_size for p in sch_files}
        run_archive(source=self.source, output=self.output, cfg=self.cfg, apply=True)
        for p in sch_files:
            self.assertTrue(p.exists())
            self.assertEqual(p.stat().st_size, sizes[p.name])
        self.assertEqual(self._source_names(), before_src)
        # 索引含原文件名
        csv_text = (self.output / "00_归档索引.csv").read_text(encoding="utf-8-sig")
        self.assertIn("原文件名", csv_text)
        self.assertIn("ZC7.820.0001-V6.1.SchDoc", csv_text)
        self.assertIn("ZCJY260101_演示项目_维修单.docx", csv_text)
        self.assertIn("模板原文无下划线", csv_text)
        self.assertIn("已归档", csv_text)
        self.assertIn("待确认是否必交", csv_text)

    def test_move_disabled_by_default(self) -> None:
        run_archive(
            source=self.source,
            output=self.output,
            cfg=self.cfg,
            apply=True,
            confirm_move=True,
        )
        self.assertTrue((self.source / "ZC7.820.0001-V6.1.SchDoc").exists())

    def test_preview_no_write_and_override(self) -> None:
        ghost = self.tmp / "ghost_out"
        result = run_archive(
            source=self.source,
            output=ghost,
            cfg=self.cfg,
            apply=False,
            write_outputs=False,
        )
        self.assertFalse(ghost.exists())
        self.assertEqual(result.copied, 0)
        dat = next(r for r in result.records if r.original_name.endswith(".dat"))
        self.assertEqual(dat.main, "99_待确认与其他")
        ov = {
            dat.rel: {
                "main": "00_需求确认",
                "sub": "技术要求",
                "extra_sub": "",
                "new_name": "手动指定技术要求.dat",
            }
        }
        result2 = run_archive(
            source=self.source,
            output=ghost,
            cfg=self.cfg,
            apply=False,
            write_outputs=False,
            overrides=ov,
        )
        again = next(r for r in result2.records if r.original_name.endswith(".dat"))
        self.assertEqual(again.main, "00_需求确认")
        self.assertEqual(again.sub, "技术要求")
        self.assertEqual(again.new_name, "手动指定技术要求.dat")
        self.assertIn("用户在网页中指定分类", again.remark_text())
        self.assertFalse(ghost.exists())


if __name__ == "__main__":
    unittest.main()
