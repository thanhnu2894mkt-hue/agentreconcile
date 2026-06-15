"""BODY cua agent — HTTP endpoint cho AgentBase runtime.

Dung thu vien chuan (khong them dependency). Mo cong 8000.

Endpoints:
  GET  /            -> thong tin agent
  GET  /health      -> {"status": "ok"}
  POST /reconcile   -> chay doi soat tren du lieu trong INPUT_DIR, tra ve summary JSON
  GET  /report      -> tai file Excel ket qua moi nhat

Chay:  python agent.py     (hoac qua Docker: CMD mac dinh)
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config as C
from src.recon import run_recon
from src.report import build_report

PORT = int(os.environ.get("PORT", "8000"))
INFO = {
    "agent": "ZION x SACOMBANK Reconciliation Agent",
    "version": "1.0",
    "description": "Doi soat phi giao dich ZION voi SACOMBANK, xuat bao cao Excel.",
    "endpoints": {
        "GET /health": "kiem tra song",
        "POST /reconcile": "chay doi soat -> tra ve summary JSON",
        "GET /report": "tai file Excel ket qua moi nhat",
    },
}


def _do_reconcile():
    tc, rf, summ = run_recon()
    out = os.path.join(C.OUTPUT_DIR, C.OUTPUT_XLSX)
    build_report(tc, rf, summ, C.RECON_PERIOD, out)
    return {"recon_period": C.RECON_PERIOD, "report_path": out, "summary": summ}


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, default=float).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/"):
            return self._json(200, INFO)
        if self.path == "/health":
            return self._json(200, {"status": "ok"})
        if self.path == "/report":
            out = os.path.join(C.OUTPUT_DIR, C.OUTPUT_XLSX)
            if not os.path.exists(out):
                return self._json(404, {"error": "Chua co bao cao. Goi POST /reconcile truoc."})
            data = open(out, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{C.OUTPUT_XLSX}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") == "/reconcile":
            try:
                return self._json(200, _do_reconcile())
            except Exception as e:  # noqa
                return self._json(500, {"error": str(e)})
        return self._json(404, {"error": "not found"})

    def log_message(self, *a):  # gon log
        pass


def main():
    print(f"Agent dang chay tai 0.0.0.0:{PORT}  (POST /reconcile de doi soat)")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
