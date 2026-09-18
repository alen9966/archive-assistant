"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from archive_assistant.config import load_config
from archive_assistant.pipeline import run_archive


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archive_assistant",
        description="项目资料归档助手：网页可视化，或 plan/apply 命令行。默认不移动、不删除、不覆盖。",
    )
    parser.add_argument(
        "command",
        choices=["web", "plan", "apply"],
        help="web=本地网页；plan=预览方案；apply=复制归档",
    )
    parser.add_argument("--source", default="", help="待归档资料目录（plan/apply）")
    parser.add_argument("--output", default="", help="归档根目录（plan/apply）")
    parser.add_argument("--config", default="", help="项目配置 YAML/JSON，见 project.example.yaml")
    parser.add_argument("--zip", dest="make_zip", action="store_true", help="apply 后打包 zip（默认不打）")
    parser.add_argument(
        "--confirm-move",
        action="store_true",
        help="二次确认允许移动；仍需配置 allow_move=true。默认关闭。",
    )
    parser.add_argument("--host", default="127.0.0.1", help="网页绑定地址")
    parser.add_argument("--port", type=int, default=8765, help="网页端口")
    parser.add_argument("--no-browser", action="store_true", help="启动网页时不自动打开浏览器")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "web":
        from archive_assistant.web import serve

        serve(host=args.host, port=args.port, open_browser=not args.no_browser)
        return 0
    source = Path(args.source)
    output = Path(args.output)
    if not args.source or not source.exists():
        print("plan/apply 需要有效 --source 目录。可视化请用: py -3 -m archive_assistant web", file=sys.stderr)
        return 2
    if not args.output:
        print("plan/apply 需要 --output 归档根目录。", file=sys.stderr)
        return 2
    cfg = load_config(args.config or None)
    apply = args.command == "apply"
    if args.make_zip and not apply:
        print("提示：--zip 仅在 apply 时打包，plan 已忽略。")
    result = run_archive(
        source=source,
        output=output,
        cfg=cfg,
        apply=apply,
        make_zip=bool(args.make_zip and apply),
        confirm_move=bool(args.confirm_move),
    )
    print(f"完成 {args.command}：输出 {result.output}")
    print(f"文件 {len(result.records)}，复制 {result.copied}，待确认 {len(result.pending)}，重复 {len(result.duplicates)}，缺失项 {len(result.missing)}")
    print("请查看 00_归档报告.md 与四份清单。")
    return 0
