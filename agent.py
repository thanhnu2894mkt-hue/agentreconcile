"""Agent HTTP server — UI + API cho AgentBase runtime.

Endpoints:
  GET  /           -> giao dien web upload file
  GET  /health     -> {"status": "ok"}
  POST /reconcile  -> nhan 6 file upload, chay doi soat, tra ve Excel
"""
import cgi
import io
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config as C
from src.recon import run_recon
from src.report import build_report

PORT = int(os.environ.get("PORT", "8080"))

HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bank Reconcile Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', sans-serif;
    min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 24px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  }
  .card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4);
    padding: 40px 48px;
    max-width: 660px; width: 100%;
    position: relative; z-index: 1;
  }
  body::before {
    content: '';
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial Black,Arial' font-weight='900' font-size='60' fill='rgba(255,255,255,0.04)'%3E%24%3C/text%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 120px 120px;
    pointer-events: none; user-select: none;
    z-index: 0;
  }
  .header { display: flex; align-items: center; gap: 14px; margin-bottom: 6px; }
  .logo { flex-shrink: 0; filter: drop-shadow(0 2px 8px rgba(0,106,245,0.4)); }
  h1 { font-size: 22px; font-weight: 700; color: #fff; }
  .subtitle { font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 28px; text-align: center; margin-top: 10px; }
  .divider { height: 1px; background: rgba(255,255,255,0.08); margin-bottom: 24px; }

  .file-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
  .file-item label {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.55);
    margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.8px;
  }
  .badge {
    font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
    color: #fff; letter-spacing: 0.3px;
  }
  .badge-zion  { background: linear-gradient(90deg,#16a34a,#22c55e); }
  .badge-apple { background: linear-gradient(90deg,#555,#111); }
  .badge-jcb   { background: linear-gradient(90deg,#cc0000,#ff2222); }
  .badge-sacom { background: linear-gradient(90deg,#1d4ed8,#3b82f6); }

  .file-item input[type=file] { display: none; }
  .file-btn {
    display: flex; align-items: center; gap: 10px;
    padding: 11px 14px;
    border: 1.5px dashed rgba(255,255,255,0.2);
    border-radius: 10px; cursor: pointer;
    font-size: 13px; color: rgba(255,255,255,0.4);
    transition: all 0.2s;
    background: rgba(255,255,255,0.04);
    width: 100%;
  }
  .file-btn:hover {
    border-color: #e94560; color: #ff6b81;
    background: rgba(233,69,96,0.08);
    transform: translateY(-1px);
  }
  .file-btn.selected {
    border-color: #00d2a0; color: #00d2a0;
    background: rgba(0,210,160,0.08); border-style: solid;
  }
  .file-btn .icon { font-size: 15px; flex-shrink: 0; }
  .file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 90px; }
  .clear-btn {
    margin-left: auto; flex-shrink: 0;
    font-size: 14px; color: rgba(255,255,255,0.25);
    cursor: pointer; padding: 0 2px; line-height: 1;
    transition: color 0.15s;
  }
  .clear-btn:hover { color: #fc8181; }
  .file-btn:not(.selected) .clear-btn { display: none; }

  .bottom-row { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
  .period-wrap { display: flex; align-items: center; gap: 10px; }
  .period-wrap label { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.6); white-space: nowrap; }
  .period-wrap select {
    padding: 8px 12px; width: 120px;
    background: rgba(255,255,255,0.07); border: 1.5px solid rgba(255,255,255,0.15);
    border-radius: 8px; color: #fff; font-size: 14px; font-weight: 600;
    cursor: pointer;
  }
  .period-wrap select:focus { outline: none; border-color: #e94560; }
  .period-wrap select option { background: #16213e; color: #fff; }

  .progress-bar-wrap { flex: 1; }
  .progress-label { font-size: 11px; color: rgba(255,255,255,0.4); margin-bottom: 5px; }
  .progress-track { position: relative; height: 10px; background: rgba(255,255,255,0.1); border-radius: 99px; overflow: visible; }
  .progress-fill {
    height: 100%; border-radius: 99px; transition: width 0.4s cubic-bezier(.34,1.56,.64,1);
    background: linear-gradient(90deg, #7928ca, #e94560, #ff8c00);
    width: 0%;
  }
  .progress-rabbit {
    position: absolute; top: 50%; font-size: 18px;
    transform: translate(-50%, -60%);
    transition: left 0.4s cubic-bezier(.34,1.56,.64,1);
    left: 0%; pointer-events: none; line-height: 1;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
  }

  .btn {
    width: 100%; padding: 15px;
    background: linear-gradient(135deg, #e94560 0%, #c62a47 100%);
    color: white; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 20px rgba(233,69,96,0.35);
    letter-spacing: 0.3px;
  }
  .btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(233,69,96,0.5);
  }
  .btn:disabled {
    background: rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.3); cursor: not-allowed;
    box-shadow: none; transform: none;
  }
  .status {
    margin-top: 16px; padding: 13px 16px; border-radius: 10px;
    font-size: 14px; display: none; font-weight: 500;
  }
  .status.running { background: rgba(66,153,225,0.15); color: #90cdf4; border: 1px solid rgba(66,153,225,0.3); display: block; }
  .status.error   { background: rgba(233,69,96,0.15);  color: #fc8181; border: 1px solid rgba(233,69,96,0.3);  display: block; }
  .status.success { background: rgba(0,210,160,0.12);  color: #00d2a0; border: 1px solid rgba(0,210,160,0.3);  display: block; }
  .tpl-link {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; color: rgba(255,255,255,0.35);
    text-decoration: none; margin-top: 5px;
    transition: color 0.15s;
  }
  .tpl-link:hover { color: #00d2a0; }
  .drop-zone {
    border: 2px dashed rgba(255,255,255,0.2); border-radius: 14px;
    padding: 28px 20px; text-align: center; cursor: pointer;
    transition: all 0.2s; background: rgba(255,255,255,0.03);
    margin-bottom: 4px;
  }
  .drop-zone:hover, .drop-zone.dragover {
    border-color: #22c55e; background: rgba(34,197,94,0.08);
    transform: scale(1.01);
  }
  .drop-icon { font-size: 32px; margin-bottom: 8px; }
  .drop-text { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.7); margin-bottom: 4px; }
  .drop-sub  { font-size: 12px; color: rgba(255,255,255,0.35); }
  .spinner {
    display: inline-block; width: 13px; height: 13px;
    border: 2px solid rgba(144,205,244,0.3); border-top-color: #90cdf4;
    border-radius: 50%; animation: spin 0.7s linear infinite;
    margin-right: 8px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .loading-bar-wrap { display: none; margin-top: 14px; }
  .loading-bar-wrap.show { display: block; }
  .loading-track {
    position: relative; height: 10px;
    background: rgba(255,255,255,0.08); border-radius: 99px; overflow: visible;
  }
  .loading-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #7928ca, #e94560, #ff8c00);
    animation: loading-slide 2s ease-in-out infinite alternate;
  }
  .loading-animal {
    position: absolute; top: 50%; font-size: 22px;
    transform: translateY(-55%);
    animation: animal-run 2s ease-in-out infinite alternate;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));
    pointer-events: none; line-height: 1;
  }
  @keyframes loading-slide {
    0%   { width: 15%; margin-left: 0; }
    100% { width: 35%; margin-left: 58%; }
  }
  @keyframes animal-run {
    0%   { left: 5%; }
    100% { left: 85%; }
  }
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <svg class="logo" viewBox="0 0 148 36" xmlns="http://www.w3.org/2000/svg" style="width:148px;height:36px">
      <text x="0" y="28" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="30" fill="#006AF5">Zalo</text>
      <text x="74" y="28" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="30" fill="#00C259">pay</text>
    </svg>
    <div>
      <h1>Bank Reconcile Agent</h1>
    </div>
  </div>
  <p class="subtitle">Upload 6 file Excel để chạy đối soát tự động</p>
  <div class="divider"></div>

  <div class="drop-zone" id="drop-zone" onclick="document.getElementById('f-all').click()" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
    <div class="drop-icon">📂</div>
    <div class="drop-text">Kéo thả hoặc click để chọn tất cả 6 file cùng lúc</div>
    <div class="drop-sub">Hệ thống tự nhận dạng file theo tên</div>
    <input type="file" id="f-all" accept=".xlsx" multiple onchange="autoDetect(this.files)" style="display:none">
  </div>
  <div class="divider" style="margin-top:20px"></div>

  <div class="file-grid">
    <div class="file-item">
      <label><span class="badge badge-zion">ZION</span> Thành công</label>
      <div class="file-btn" id="btn-TC" onclick="document.getElementById('f-TC').click()">
        <span class="icon">📄</span><span class="file-name" id="name-TC">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'TC')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-TC" accept=".xlsx" onchange="setFile('TC',this)">
      <a class="tpl-link" href="/template/TC" download="template_ZION_thanh_cong.xlsx">📥 Tải file mẫu</a>
    </div>
    <div class="file-item">
      <label><span class="badge badge-zion">ZION</span> Hoàn tiền</label>
      <div class="file-btn" id="btn-RF" onclick="document.getElementById('f-RF').click()">
        <span class="icon">📄</span><span class="file-name" id="name-RF">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'RF')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-RF" accept=".xlsx" onchange="setFile('RF',this)">
      <a class="tpl-link" href="/template/RF" download="template_ZION_hoan_tien.xlsx">📥 Tải file mẫu</a>
    </div>
    <div class="file-item">
      <label><span class="badge badge-zion">ZION</span> Hoàn tiền CV</label>
      <div class="file-btn" id="btn-CV" onclick="document.getElementById('f-CV').click()">
        <span class="icon">📄</span><span class="file-name" id="name-CV">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'CV')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-CV" accept=".xlsx" onchange="setFile('CV',this)">
      <a class="tpl-link" href="/template/CV" download="template_ZION_hoan_tien_CV.xlsx">📥 Tải file mẫu</a>
    </div>
    <div class="file-item">
      <label><span class="badge badge-apple">🍎</span> Apple Pay</label>
      <div class="file-btn" id="btn-AP" onclick="document.getElementById('f-AP').click()">
        <span class="icon">📄</span><span class="file-name" id="name-AP">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'AP')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-AP" accept=".xlsx" onchange="setFile('AP',this)">
      <a class="tpl-link" href="/template/AP" download="template_APPLEPAY.xlsx">📥 Tải file mẫu</a>
    </div>
    <div class="file-item">
      <label><span class="badge badge-jcb">JCB</span> BIN Lookup</label>
      <div class="file-btn" id="btn-JCB" onclick="document.getElementById('f-JCB').click()">
        <span class="icon">📄</span><span class="file-name" id="name-JCB">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'JCB')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-JCB" accept=".xlsx" onchange="setFile('JCB',this)">
      <a class="tpl-link" href="/template/JCB" download="template_JCB.xlsx">📥 Tải file mẫu</a>
    </div>
    <div class="file-item">
      <label><span class="badge badge-sacom">SACOMBANK</span></label>
      <div class="file-btn" id="btn-SB" onclick="document.getElementById('f-SB').click()">
        <span class="icon">📄</span><span class="file-name" id="name-SB">Chọn file...</span>
        <span class="clear-btn" onclick="clearFile(event,'SB')" title="Xóa file">✕</span>
      </div>
      <input type="file" id="f-SB" accept=".xlsx" onchange="setFile('SB',this)">
      <a class="tpl-link" href="/template/SB" download="template_SACOMBANK.xlsx">📥 Tải file mẫu</a>
    </div>
  </div>

  <div class="bottom-row">
    <div class="period-wrap">
      <label>Kỳ:</label>
      <select id="period">
        <option value="">--</option>
      </select>
    </div>
    <div class="progress-bar-wrap">
      <div class="progress-label" id="progress-label">0 / 6 file đã chọn</div>
      <div class="progress-track">
        <div class="progress-fill" id="progress-fill"></div>
        <span class="progress-rabbit" id="progress-rabbit">🐇</span>
      </div>
    </div>
  </div>

  <button class="btn" id="run-btn" onclick="runRecon()" disabled>⚡ Chạy đối soát</button>
  <div class="loading-bar-wrap" id="loading-bar">
    <div class="loading-track">
      <div class="loading-fill"></div>
      <span class="loading-animal" id="animal">🐇</span>
    </div>
  </div>
  <div class="status" id="status"></div>
</div>

<script>
const keys = ['TC','RF','CV','AP','JCB','SB'];
const files = {};

// Bảng nhận dạng file theo tên — dùng chuỗi normalize để xử lý tiếng Việt
function normalize(s) {
  return s.normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/gi,'d').toLowerCase();
}

const PATTERNS = {
  CV:  s => /hoantiencv|hoantien.*cv|cv.*hoantien/i.test(s),
  TC:  s => /datazion/.test(s) && /thanh.*cong|cong.*thanh/.test(s),
  RF:  s => /(datazion|zion)/.test(s) && /hoan.*tien|tien.*hoan/.test(s) && !/cv/.test(s),
  AP:  s => /applepay|apple.?pay/.test(s),
  JCB: s => /jcb/.test(s),
  SB:  s => /sacombank|sacom/.test(s),
};

function detectKey(filename) {
  const n = normalize(filename);
  // CV phải check trước RF vì cùng có "hoan tien"
  for (const key of ['CV','TC','RF','AP','JCB','SB']) {
    if (PATTERNS[key](n)) return key;
  }
  return null;
}

async function applyFile(key, file) {
  // 1. Kiểm tra đuôi file
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    showError(`❌ File "${file.name}" không đúng định dạng — chỉ chấp nhận .xlsx`);
    return;
  }
  // 2. Kiểm tra cấu trúc cột trên server
  const form = new FormData();
  form.append('file', file);
  form.append('key', key);
  try {
    const res = await fetch('/validate-file', { method: 'POST', body: form });
    const data = await res.json();
    if (!data.ok) {
      showError(`❌ ${data.error}`);
      return;
    }
  } catch(e) { /* bỏ qua nếu network lỗi */ }

  files[key] = file;
  document.getElementById('name-' + key).textContent = file.name;
  const btn = document.getElementById('btn-' + key);
  btn.classList.add('selected');
  btn.querySelector('.icon').textContent = '✅';
  if (key === 'SB') detectPeriods(file);
  checkReady();
}

function showError(msg) {
  const s = document.getElementById('status');
  s.className = 'status error';
  s.style.display = 'block';
  s.innerHTML = msg;
  setTimeout(() => { if (s.innerHTML === msg) s.style.display = 'none'; }, 5000);
}

async function detectPeriods(file) {
  const sel = document.getElementById('period');
  sel.innerHTML = '<option value="">Đang đọc kỳ...</option>';
  try {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch('/detect-periods', { method: 'POST', body: form });
    const data = await res.json();
    if (data.periods && data.periods.length > 0) {
      sel.innerHTML = data.periods.map(p =>
        `<option value="${p}">Tháng ${p}</option>`
      ).join('');
    } else {
      sel.innerHTML = '<option value="">Không tìm thấy kỳ</option>';
    }
  } catch(e) {
    sel.innerHTML = '<option value="">Lỗi đọc file</option>';
  }
}

async function autoDetect(fileList) {
  const unmatched = [];
  const promises = Array.from(fileList).map(async f => {
    const key = detectKey(f.name);
    if (key) await applyFile(key, f);
    else unmatched.push(f.name);
  });
  await Promise.all(promises);
  if (unmatched.length) {
    const s = document.getElementById('status');
    s.className = 'status error';
    s.style.display = 'block';
    s.innerHTML = '⚠️ Không nhận dạng được tên file: ' + unmatched.map(n => `<b>${n}</b>`).join(', ') + '<br><small>Đổi tên file theo quy ước hoặc kéo thả vào đúng ô bên dưới</small>';
    setTimeout(() => { if (s.classList.contains('error')) s.style.display='none'; }, 6000);
  }
  checkReady();
}

function onDragOver(e) { e.preventDefault(); document.getElementById('drop-zone').classList.add('dragover'); }
function onDragLeave(e) { document.getElementById('drop-zone').classList.remove('dragover'); }
function onDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('dragover');
  autoDetect(e.dataTransfer.files);
}

function setFile(key, input) {
  if (!input.files[0]) return;
  applyFile(key, input.files[0]);
}

function clearFile(e, key) {
  e.stopPropagation();
  delete files[key];
  document.getElementById('name-' + key).textContent = 'Chọn file...';
  const btn = document.getElementById('btn-' + key);
  btn.classList.remove('selected');
  btn.querySelector('.icon').textContent = '📄';
  document.getElementById('f-' + key).value = '';
  checkReady();
}

function checkReady() {
  const count = keys.filter(k => files[k]).length;
  const ready = count === keys.length;
  document.getElementById('run-btn').disabled = !ready;
  const pct = count / 6 * 100;
  document.getElementById('progress-label').textContent = count + ' / 6 file đã chọn';
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-rabbit').style.left = Math.min(pct, 93) + '%';
  document.getElementById('progress-rabbit').textContent = count === 6 ? '🐇' : '🐢';
}

async function runRecon() {
  const status = document.getElementById('status');
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  document.getElementById('loading-bar').classList.add('show');
  status.className = 'status running';
  status.innerHTML = '🐇 Đang xử lý đối soát, vui lòng chờ...';

  const form = new FormData();
  keys.forEach(k => form.append(k, files[k]));
  form.append('period', document.getElementById('period').value || '05');

  try {
    const res = await fetch('/reconcile', { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Lỗi không xác định' }));
      throw new Error(err.error || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'DOI_SOAT_ZION_SACOMBANK.xlsx';
    a.click();
    URL.revokeObjectURL(url);
    status.className = 'status success';
    status.innerHTML = '✅ Đối soát hoàn tất! File Excel đã được tải xuống.';
  } catch (e) {
    status.className = 'status error';
    status.innerHTML = '❌ Lỗi: ' + e.message;
  } finally {
    btn.disabled = false;
    document.getElementById('loading-bar').classList.remove('show');
  }
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, content_type, body):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, payload):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(payload, ensure_ascii=False, default=float))

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/"):
            self._send(200, "text/html; charset=utf-8", HTML)
        elif self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path.startswith("/template/"):
            key = self.path.split("/template/")[-1].upper().rstrip("/")
            self._serve_template(key)
        else:
            self._json(404, {"error": "not found"})

    def _serve_template(self, key):
        import io as _io, openpyxl as _xl
        # Full column lists from actual input files
        TEMPLATES = {
            "TC": [
                ["Bank Trans ID", "Trace No", "Sub Trans Type", "Amount", "Trans Time",
                 "Card Type", "BankMID", "Is On Us", "Fee Rate", "Bin No", "L4 Card No"],
            ],
            "RF": [
                ["traceNo", "Refund Bank Trans ID", "Amount", "Refund Amount",
                 "Refund Trans Time", "Is On Us", "Bank Account", "Fee Rate",
                 "Sub Trans Type", "Card Scheme", "F6 Card No", "L4 Card No"],
            ],
            "CV": [
                ["traceNo", "Refund Bank Trans ID", "Amount", "Refund Amount",
                 "Refund Trans Time", "Is On Us", "Bank Account", "Fee Rate",
                 "Sub Trans Type", "Refund Sub Trans Type", "Card Scheme",
                 "F6 Card No", "L4 Card No", "BINCOUNTRY", "BINISSER",
                 "BOOK_DATE (BANK)", "DISCOUNT (BANK)", "PHI +440", "PHI XLGD",
                 "PHI ZLP", "TỶ LÊ", "Chốt VAT"],
            ],
            "AP": [
                # row 0: metadata (giữ nguyên như file gốc)
                ["zalopay_acct", "Apple pay", "PaymentBatchDetail", "1.00", ""],
                # row 1: header thật
                ["RequestDate", "RequestID", "MerchantReferenceNumber", "BinCountry",
                 "BinIssuer", "Amount", "Status", "MerchantID", "BatchID", "BatchDate",
                 "LocalizedRequestDate", "BinScheme", "RCode", "BinNumber",
                 "ApplicationName", "RMsg"],
            ],
            "JCB": [
                ["BIN 8 SỐ", "6 SỐ ĐẦU", "Ngân hàng", "Viet tat", "Ghi chú loại thẻ", "Notes"],
            ],
            "SB": [
                ["MM_DBA_NAME", "CARDNO", "TRANS_AMOUNT", "BILLING_AMOUNT", "DISCOUNT",
                 "PROC_DATE", "BOOK_DATE", "CrdType", "ReqRecId"],
            ],
        }
        if key not in TEMPLATES:
            self._json(404, {"error": "template not found"}); return
        wb = _xl.Workbook()
        ws = wb.active
        for row in TEMPLATES[key]:
            ws.append(row)
        buf = _io.BytesIO()
        wb.save(buf)
        data = buf.getvalue()
        fname = f"template_{key}.xlsx"
        self.send_response(200)
        self.send_header("Content-Type",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.rstrip("/") == "/validate-file":
            try:
                ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
                pdict["boundary"] = pdict["boundary"].encode()
                pdict["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", 0))
                fields = cgi.parse_multipart(self.rfile, pdict)
                data = fields.get("file", [None])[0]
                key  = (fields.get("key", [b""])[0] or b"").decode() if isinstance(fields.get("key", [b""])[0], bytes) else fields.get("key", [""])[0]
                if data is None: self._json(400, {"ok": False, "error": "Thiếu file"}); return
                if isinstance(data, str): data = data.encode()
                import io as _io, pandas as _pd
                REQUIRED = {
                    "TC":  ["Bank Trans ID", "Is On Us", "Fee Rate", "Amount"],
                    "RF":  ["Refund Bank Trans ID"],
                    "CV":  ["Refund Bank Trans ID", "PHI ZLP"],
                    "AP":  ["RequestID", "BinCountry", "BinIssuer"],
                    "JCB": ["BIN 8 SỐ"],
                    "SB":  ["BOOK_DATE", "ReqRecId", "DISCOUNT"],
                }
                # AP file has 1 metadata row before the real header
                SKIPROWS = {"AP": 1}
                try:
                    df = _pd.read_excel(_io.BytesIO(data), nrows=2,
                                        skiprows=SKIPROWS.get(key, 0))
                except Exception:
                    self._json(200, {"ok": False, "error": "File không đọc được, vui lòng kiểm tra lại định dạng .xlsx"}); return
                cols = list(df.columns)
                expected = REQUIRED.get(key, [])
                missing = [c for c in expected if c not in cols]
                if missing:
                    self._json(200, {"ok": False, "error": f"File không đúng cấu trúc. Thiếu cột: {', '.join(missing)}"}); return
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path.rstrip("/") == "/detect-periods":
            try:
                ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
                pdict["boundary"] = pdict["boundary"].encode()
                pdict["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", 0))
                fields = cgi.parse_multipart(self.rfile, pdict)
                data = fields.get("file", [None])[0]
                if data is None:
                    self._json(400, {"error": "Thiếu file"}); return
                if isinstance(data, str): data = data.encode()
                import io as _io
                import pandas as _pd
                df = _pd.read_excel(_io.BytesIO(data)).dropna(axis=1, how="all")
                periods = []
                if "BOOK_DATE" in df.columns:
                    raw = df["BOOK_DATE"].dropna().astype("Int64").astype(str)
                    periods = sorted(set(r[4:6] for r in raw if len(r) == 8))
                self._json(200, {"periods": periods})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path.rstrip("/") != "/reconcile":
            self._json(404, {"error": "not found"})
            return
        try:
            ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
            if ctype != "multipart/form-data":
                self._json(400, {"error": "Yeu cau multipart/form-data"})
                return
            pdict["boundary"] = pdict["boundary"].encode()
            pdict["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", 0))
            fields = cgi.parse_multipart(self.rfile, pdict)

            required = ["TC", "RF", "CV", "AP", "JCB", "SB"]
            missing = [k for k in required if k not in fields or not fields[k]]
            if missing:
                self._json(400, {"error": f"Thieu file: {missing}"})
                return

            period = (fields.get("period") or ["05"])[0]
            if isinstance(period, bytes):
                period = period.decode()

            with tempfile.TemporaryDirectory() as tmpdir:
                outdir = os.path.join(tmpdir, "output")
                os.makedirs(outdir)

                file_map = {}
                for key in required:
                    data = fields[key][0]
                    if isinstance(data, str):
                        data = data.encode()
                    fpath = os.path.join(tmpdir, f"{key}.xlsx")
                    with open(fpath, "wb") as f:
                        f.write(data)
                    file_map[key] = fpath

                old_env = {}
                env_updates = {
                    "INPUT_DIR": tmpdir,
                    "OUTPUT_DIR": outdir,
                    "RECON_PERIOD": period,
                    "FILE_TC": f"{key}.xlsx",
                }
                for k in required:
                    env_updates[f"FILE_{k}"] = f"{k}.xlsx"
                for k, v in env_updates.items():
                    old_env[k] = os.environ.get(k)
                    os.environ[k] = v

                import importlib
                importlib.reload(C)
                tc, rf, summ = run_recon()
                out_path = os.path.join(outdir, "DOI_SOAT_ZION_SACOMBANK.xlsx")
                build_report(tc, rf, summ, period, out_path)

                for k, v in old_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
                importlib.reload(C)

                with open(out_path, "rb") as f:
                    xlsx_data = f.read()

            fname = "DOI_SOAT_ZION_SACOMBANK.xlsx"
            self.send_response(200)
            self.send_header("Content-Type",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(xlsx_data)))
            self.end_headers()
            self.wfile.write(xlsx_data)

        except Exception as e:
            self._json(500, {"error": str(e)})

    def log_message(self, *a):
        pass


def main():
    print(f"Agent dang chay tai 0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
