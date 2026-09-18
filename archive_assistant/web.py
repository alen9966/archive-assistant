"""本地网页服务：拖拽识别，确认后才复制。复用 pipeline 分类规则。"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from archive_assistant.catalog import folder_options
from archive_assistant.config import ProjectConfig, config_from_mapping, load_config
from archive_assistant.pipeline import result_payload, run_archive

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
SESSION_ROOT = Path(tempfile.gettempdir()) / "archive_assistant_sessions"
MAX_UPLOAD = 512 * 1024 * 1024  # 单次上传 512MB；更大请填本机目录

_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def _json_bytes(data: object, code: int = 200) -> tuple[int, bytes, str]:
    raw = json.dumps(data, ensure_ascii=False, indent=None).encode("utf-8")
    return code, raw, "application/json; charset=utf-8"


def safe_rel(name: str) -> str:
    name = unquote(name or "").replace("\\", "/").replace("\x00", "")
    parts = []
    for p in name.split("/"):
        p = p.strip()
        if not p or p in (".", ".."):
            continue
        p = re.sub(r'[<>:"|?*]', "_", p)
        parts.append(p)
    return "/".join(parts) or "unnamed"


def default_project() -> tuple[ProjectConfig, str]:
    for cand in (ROOT / "project.yaml", ROOT / "project.example.yaml"):
        if cand.is_file():
            try:
                return load_config(cand), str(cand)
            except Exception:
                continue
    return ProjectConfig(), ""


def cfg_to_form(cfg: ProjectConfig) -> dict:
    variants = [{"name": v.name, "code": v.code} for v in cfg.assembly_variants]
    return {
        "project_name": cfg.project_name,
        "project_code": cfg.project_code,
        "model": cfg.model,
        "boards": "\n".join(cfg.boards),
        "assembly_variants": variants,
        "variants_text": "\n".join(
            f"{v.name},{v.code}".strip(",") if v.code else v.name for v in cfg.assembly_variants
        ),
        "quantity": cfg.quantity,
        "archive_date": cfg.archive_date,
        "owners": cfg.owners,
        "confirmers": cfg.confirmers,
        "allow_move": False,
    }


def form_to_cfg(data: dict) -> ProjectConfig:
    boards_raw = data.get("boards", "")
    if isinstance(boards_raw, list):
        boards = boards_raw
    else:
        boards = [x.strip() for x in str(boards_raw).replace(",", "\n").splitlines() if x.strip()]
    variants = data.get("assembly_variants") or []
    if not variants and data.get("variants_text"):
        variants = []
        for line in str(data.get("variants_text")).splitlines():
            line = line.strip()
            if not line:
                continue
            if "," in line:
                name, code = line.split(",", 1)
                variants.append({"name": name.strip(), "code": code.strip()})
            else:
                variants.append({"name": line, "code": ""})
    owners = data.get("owners") if isinstance(data.get("owners"), dict) else {}
    mapping = {
        "project_name": data.get("project_name", ""),
        "project_code": data.get("project_code", ""),
        "model": data.get("model", ""),
        "boards": boards,
        "assembly_variants": variants,
        "quantity": data.get("quantity", ""),
        "archive_date": data.get("archive_date", ""),
        "owners": owners,
        "confirmers": data.get("confirmers") or {},
        "allow_move": False,
        "confirm_move": False,
    }
    return config_from_mapping(mapping)


def session_dir(sid: str) -> Path:
    return SESSION_ROOT / sid / "files"


def get_or_create_session(sid: str | None) -> str:
    with _lock:
        if sid and sid in _sessions:
            return sid
        new_id = uuid.uuid4().hex
        path = session_dir(new_id)
        path.mkdir(parents=True, exist_ok=True)
        _sessions[new_id] = {"id": new_id, "files": path, "local_source": ""}
        return new_id


def write_demo_files(dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    samples = {
        "原理图/ZC7.820.0001-V6.1.SchDoc": b"sch-demo",
        "PCB/ZC7.820.0001-V6.1.PcbDoc": b"pcb-demo",
        "BOM表/授时守时板卡_采购清单.xlsx": b"bom-demo",
        "单板测试记录表/ZC7.820.0001-V6.1_单板测试记录表.xlsx": b"test-demo",
        "三防图/ZC7.820.0001-V6.1_三防图.pdf": b"3f-demo",
        "装配图/ZC7.820.0001-V6.1装配图.pdf": b"assy-demo",
        "外协阻容清单/外协阻容清单.xlsx": b"rc-demo",
        "装配清单/装配清单.xlsx": b"kitting-demo",
        "坐标文件夹/top.csv": b"xy,1,2\n",
        "坐标文件夹/bot.csv": b"xy,3,4\n",
        "生产开发计划.docx": b"plan-demo",
        "BOOT_1U_VER6906_251127_v1.01.bin": b"fw" * 16,
        "电装完_现场.jpg": b"\xff\xd8\xff\xd9",
        "无法识别的杂项.dat": b"unknown-bytes",
        "客户机密_说明.txt": "这是内部说明，不是真实密钥\n".encode("utf-8"),
        "售后维修单.docx": b"repair-form",
        "dup_a.txt": b"same-hash-payload",
        "dup_b.txt": b"same-hash-payload",
    }
    n = 0
    for name, data in samples.items():
        p = dest / Path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        n += 1
    return n


def parse_overrides(items: list) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        key = str(it.get("id") or it.get("rel") or "").replace("\\", "/")
        if not key:
            continue
        out[key] = {
            "main": it.get("main", ""),
            "sub": it.get("sub", ""),
            "extra_sub": it.get("extra_sub", ""),
            "label": it.get("folder") or it.get("label") or "",
            "new_name": it.get("new_name", ""),
        }
    return out


def resolve_source(sess: dict, local_source: str) -> Path:
    local_source = (local_source or sess.get("local_source") or "").strip()
    if local_source:
        p = Path(local_source)
        if not p.exists():
            raise FileNotFoundError(f"本机目录不存在: {p}")
        sess["local_source"] = str(p)
        return p.resolve()
    return Path(sess["files"]).resolve()


def intended_output(raw: str, cfg: ProjectConfig) -> Path:
    text = (raw or "").strip()
    if text:
        return Path(text)
    name = cfg.display_name()
    return ROOT / "归档输出" / name


def run_preview_or_apply(
    *,
    sess: dict,
    data: dict,
    apply: bool,
) -> dict:
    cfg = form_to_cfg(data.get("project") or data)
    source = resolve_source(sess, str(data.get("local_source") or ""))
    output = intended_output(str(data.get("output") or ""), cfg)
    overrides = parse_overrides(data.get("overrides") or data.get("files") or [])
    if apply and not list(source.rglob("*")):
        raise ValueError("没有可归档文件。请先拖入/上传，或填写本机目录。")
    result = run_archive(
        source=source,
        output=output,
        cfg=cfg,
        apply=apply,
        make_zip=bool(data.get("zip")),
        write_outputs=apply,
        overrides=overrides or None,
    )
    payload = result_payload(result, cfg)
    payload["session_id"] = sess["id"]
    payload["source"] = str(source)
    payload["applied"] = apply
    if apply:
        report = output / "00_归档报告.md"
        payload["report_excerpt"] = report.read_text(encoding="utf-8")[:4000] if report.is_file() else ""
        payload["artifacts"] = [
            "00_归档索引.xlsx",
            "00_归档索引.csv",
            "00_缺失资料清单.xlsx",
            "00_待确认清单.xlsx",
            "00_重复文件清单.xlsx",
            "00_归档报告.md",
        ]
    return payload


def _discard_body(handler: BaseHTTPRequestHandler) -> None:
    try:
        length = int(handler.headers.get("Content-Length") or "0")
    except ValueError:
        length = 0
    remain = max(0, length)
    # 超大包只丢掉一小段，避免卡死；随后 Connection: close
    cap = min(remain, 1024 * 1024)
    while cap > 0:
        chunk = handler.rfile.read(min(65536, cap))
        if not chunk:
            break
        cap -= len(chunk)


_browse_lock = threading.Lock()


def pick_directory() -> str:
    """弹出系统文件夹对话框，返回本机绝对路径。失败返回空串。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return ""
    with _browse_lock:
        root = tk.Tk()
        root.withdraw()
        try:
            root.wm_attributes("-topmost", True)
        except Exception:
            pass
        path = filedialog.askdirectory(title="选择待归档资料文件夹")
        root.destroy()
        return path or ""


def _parse_disposition(disp: str) -> tuple[str, str]:
    name, filename = "", ""
    for part in disp.split(";"):
        part = part.strip()
        if part.lower().startswith("name="):
            name = part.split("=", 1)[1].strip().strip('"')
        elif part.lower().startswith("filename*="):
            val = part.split("=", 1)[1].strip()
            if "''" in val:
                val = val.split("''", 1)[1]
            filename = unquote(val.strip().strip('"'))
        elif part.lower().startswith("filename="):
            filename = part.split("=", 1)[1].strip().strip('"')
    return name, filename


def save_multipart_upload(handler: BaseHTTPRequestHandler, dest: Path) -> tuple[int, dict[str, str]]:
    """流式保存 multipart 文件到 dest。返回 (文件数, 文本字段)。"""
    ctype = handler.headers.get("Content-Type", "")
    m = re.search(r"boundary=([^;]+)", ctype, re.I)
    if not m:
        raise ValueError("不是 multipart 上传")
    boundary = m.group(1).strip().strip('"').encode("utf-8")
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        raise ValueError("空上传")
    if length > MAX_UPLOAD:
        _discard_body(handler)
        raise ValueError(
            f"这个文件夹约 {length / 1024 / 1024:.0f}MB，浏览器传不上去。"
            "请点「选择本机文件夹」，或把路径填到左侧「本机资料目录」后再识别。"
        )
    raw = handler.rfile.read(length)
    marker = b"--" + boundary
    parts = raw.split(marker)
    fields: dict[str, str] = {}
    count = 0
    dest.mkdir(parents=True, exist_ok=True)
    for part in parts:
        if not part or part in (b"--", b"--\r\n", b"--\n"):
            continue
        if part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        elif part.startswith(b"\n"):
            part = part[1:]
        sep = b"\r\n\r\n"
        idx = part.find(sep)
        if idx < 0:
            sep = b"\n\n"
            idx = part.find(sep)
        if idx < 0:
            continue
        head, body = part[:idx].decode("utf-8", "replace"), part[idx + len(sep) :]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        elif body.endswith(b"\n"):
            body = body[:-1]
        disp = ""
        for line in head.splitlines():
            if line.lower().startswith("content-disposition:"):
                disp = line.split(":", 1)[1].strip()
        name, filename = _parse_disposition(disp)
        if filename:
            rel = safe_rel(filename)
            path = dest / Path(*rel.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            count += 1
        elif name:
            fields[name] = body.decode("utf-8", "replace")
    return count, fields


class Handler(BaseHTTPRequestHandler):
    server_version = "ArchiveAssistantWeb/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("[web] " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, ctype: str, close: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if close or code >= 400:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: object, code: int = 200) -> None:
        code, raw, ctype = _json_bytes(data, code)
        self._send(code, raw, ctype)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or "0")
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON 须为对象")
        return data

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            html = (STATIC / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/api/bootstrap":
            cfg, cfg_path = default_project()
            self._send_json(
                {
                    "folders": folder_options(),
                    "project": cfg_to_form(cfg),
                    "config_path": cfg_path,
                    "default_output": str(ROOT / "归档输出"),
                    "policy": "暂定默认：只复制、不删除、不覆盖；识别预览不写盘。",
                }
            )
            return
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        self._send_json({"error": "未找到"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        try:
            if path == "/api/session":
                sid = get_or_create_session(None)
                self._send_json({"session_id": sid})
                return
            if path == "/api/upload":
                sid = qs.get("session_id", [""])[0] or None
                sid = get_or_create_session(sid)
                dest = session_dir(sid)
                count, fields = save_multipart_upload(self, dest)
                with _lock:
                    _sessions[sid]["local_source"] = ""
                self._send_json({"session_id": sid, "uploaded": count, "fields": fields})
                return
            data = self._read_json()
            sid = get_or_create_session(data.get("session_id"))
            with _lock:
                sess = _sessions[sid]
            if path == "/api/browse":
                chosen = pick_directory()
                self._send_json({"session_id": sid, "path": chosen, "ok": bool(chosen)})
                return
            if path == "/api/demo":
                n = write_demo_files(session_dir(sid))
                sess["local_source"] = ""
                data.setdefault("project", cfg_to_form(default_project()[0]))
                payload = run_preview_or_apply(sess=sess, data=data, apply=False)
                payload["demo_files"] = n
                self._send_json(payload)
                return
            if path == "/api/preview":
                payload = run_preview_or_apply(sess=sess, data=data, apply=False)
                self._send_json(payload)
                return
            if path == "/api/apply":
                payload = run_preview_or_apply(sess=sess, data=data, apply=True)
                self._send_json(payload)
                return
            if path == "/api/open":
                target = Path(str(data.get("path") or ""))
                if not target.exists():
                    raise FileNotFoundError(f"路径不存在: {target}")
                if os.name == "nt":
                    os.startfile(str(target))  # noqa: S606
                else:
                    os.system(f'xdg-open "{target}"')  # noqa: S605
                self._send_json({"ok": True, "path": str(target)})
                return
            self._send_json({"error": "未找到接口"}, 404)
        except Exception as exc:  # noqa: BLE001
            if parsed.path == "/api/upload":
                try:
                    _discard_body(self)
                except Exception:
                    pass
            self._send_json({"error": str(exc)}, 400)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"归档助手网页：{url}", flush=True)
    print("先识别预览，点「生成分类文件夹」后才复制。默认不删除、不覆盖。认不出的进 99_待确认与其他。", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止网页服务")
    finally:
        httpd.server_close()
