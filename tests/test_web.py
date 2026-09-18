from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from archive_assistant.web import Handler


class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.host, cls.port = cls.httpd.server_address
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _conn(self) -> HTTPConnection:
        return HTTPConnection("127.0.0.1", self.port, timeout=30)

    def _json(self, method: str, path: str, body: dict | None = None, code: int = 200) -> dict:
        conn = self._conn()
        raw = json.dumps(body or {}).encode("utf-8") if body is not None and method != "GET" else b""
        headers = {}
        if method != "GET":
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(raw))
        conn.request(method, path, body=raw if method != "GET" else None, headers=headers)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()
        self.assertEqual(resp.status, code, data)
        return data

    def test_bootstrap_and_demo_preview_apply(self) -> None:
        conn = self._conn()
        conn.request("GET", "/api/bootstrap")
        resp = conn.getresponse()
        boot = json.loads(resp.read().decode("utf-8"))
        conn.close()
        self.assertEqual(resp.status, 200)
        self.assertTrue(boot["folders"])
        labels = [x["label"] for x in boot["folders"]]
        self.assertIn("99_待确认与其他", labels)
        self.assertIn("03_硬件&结构设计/01_原理图", labels)

        conn = self._conn()
        conn.request("GET", "/")
        html_resp = conn.getresponse()
        html = html_resp.read().decode("utf-8")
        conn.close()
        self.assertEqual(html_resp.status, 200)
        self.assertIn("生成分类文件夹", html)
        self.assertIn("选择本机文件夹", html)

        sess = self._json("POST", "/api/session", {})
        sid = sess["session_id"]
        demo = self._json(
            "POST",
            "/api/demo",
            {
                "session_id": sid,
                "project": {
                    "project_name": "演示项目",
                    "project_code": "ZCJY260101",
                    "model": "DEMO-1",
                    "boards": "ZC7.820.0001-V6.1",
                    "variants_text": "授时守时板卡,ZCJY260101",
                    "quantity": "2套",
                    "archive_date": "20260917",
                },
                "output": str(Path(self.httpd.server_address[0])),  # unused in preview
            },
        )
        self.assertGreaterEqual(demo["stats"]["total"], 8)
        self.assertGreaterEqual(demo["copied"], 0)
        names = {f["original_name"]: f for f in demo["files"]}
        self.assertIn("ZC7.820.0001-V6.1.SchDoc", names)
        self.assertEqual(names["ZC7.820.0001-V6.1.SchDoc"]["sub"], "01_原理图")
        self.assertEqual(names["无法识别的杂项.dat"]["main"], "99_待确认与其他")
        dat = names["无法识别的杂项.dat"]
        tmp_out = Path(__file__).resolve().parents[1] / "_web_test_out"
        if tmp_out.exists():
            import shutil

            shutil.rmtree(tmp_out, ignore_errors=True)
        applied = self._json(
            "POST",
            "/api/apply",
            {
                "session_id": sid,
                "project": {
                    "project_name": "演示项目",
                    "project_code": "ZCJY260101",
                    "model": "DEMO-1",
                    "boards": "ZC7.820.0001-V6.1",
                    "variants_text": "授时守时板卡,ZCJY260101",
                    "quantity": "2套",
                    "archive_date": "20260917",
                },
                "output": str(tmp_out),
                "overrides": [
                    {
                        "id": dat["id"],
                        "rel": dat["rel"],
                        "main": "00_需求确认",
                        "sub": "技术要求",
                        "folder": "00_需求确认/技术要求",
                        "new_name": "网页改分类.dat",
                    }
                ],
            },
        )
        self.assertTrue(applied["applied"])
        self.assertGreater(applied["copied"], 0)
        self.assertTrue((tmp_out / "00_归档报告.md").is_file())
        self.assertTrue((tmp_out / "00_归档索引.csv").is_file())
        moved = tmp_out / "00_需求确认" / "技术要求" / "网页改分类.dat"
        self.assertTrue(moved.is_file())
        # 上传/演示暂存不算删除源：演示文件仍在 session 目录逻辑上由 apply 复制
        import shutil

        shutil.rmtree(tmp_out, ignore_errors=True)

    def test_multipart_upload(self) -> None:
        sess = self._json("POST", "/api/session", {})
        sid = sess["session_id"]
        boundary = "----WebTestBoundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="技术要求.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "req-demo\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        conn = self._conn()
        conn.request(
            "POST",
            f"/api/upload?session_id={sid}",
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()
        self.assertEqual(resp.status, 200, data)
        self.assertEqual(data["uploaded"], 1)
        prev = self._json(
            "POST",
            "/api/preview",
            {
                "session_id": sid,
                "project": {"project_name": "演示项目", "archive_date": "20260917"},
            },
        )
        self.assertEqual(prev["stats"]["total"], 1)
        self.assertEqual(prev["files"][0]["sub"], "技术要求")
        self.assertEqual(prev["copied"], 0)


if __name__ == "__main__":
    unittest.main()
