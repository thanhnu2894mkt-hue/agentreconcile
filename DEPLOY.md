# DEPLOY.md — Hướng dẫn Push GitHub & Deploy AgentBase (Claw-a-thon 2026)

> Các bước dưới đây **bạn tự chạy trên máy mình** vì chúng cần tài khoản GitHub và
> IAM credential GreenNode của bạn (Claude không nhập mật khẩu/token thay bạn được).
> Bạn chỉ cần copy/paste đúng lệnh. Đặt folder trong **Documents**, không để trong Downloads.

## 0. Chuẩn bị (1 lần)
Cài theo Sổ tay: **GitHub account → Git CLI → Docker Desktop**. Kiểm tra:
```bash
git --version        # ra "git version 2.xx"
docker --version     # Docker đang chạy (icon cá voi "Engine running")
```

## 1. Đưa folder vào Documents
Giải nén `my-agent.zip` rồi chuyển folder `my-agent` vào `Documents`.
```bash
cd ~/Documents/my-agent       # (Windows: cd %USERPROFILE%\Documents\my-agent)
```

## 2. (Tuỳ chọn) Test nhanh trên máy
```bash
pip install -r requirements.txt
python run.py                 # xuất data/output/DOI_SOAT_ZION_SACOMBANK.xlsx
# hoặc chạy dạng agent có endpoint:
python agent.py               # mở http://localhost:8000  (POST /reconcile, GET /report)
```

## 3. Test bằng Docker (giống môi trường AgentBase)
```bash
docker build -t zion-recon-agent:latest .
docker run --rm -p 8000:8000 -v "$PWD/data/output:/app/data/output" zion-recon-agent:latest
# mở http://localhost:8000/health  -> {"status":"ok"}
# POST http://localhost:8000/reconcile
```

## 4. Push code lên GitHub

### Cách A — GitHub Desktop (không gõ lệnh)
1. Mở **GitHub Desktop** → File → **Add Local Repository** → chọn folder `my-agent`.
2. Nó báo chưa phải repo → bấm **Create a repository** → Create.
3. Bấm **Publish repository** → đặt tên (vd `clawathon-zion-recon`).
   - ⚠️ **Bỏ tick "Keep this code private"** chỉ khi bạn chấp nhận công khai. Vì repo
     chứa **dữ liệu giao dịch thật** (mã GD, số thẻ), **NÊN để Private**.
4. Sau này sửa gì → tab Changes → viết mô tả → **Commit to main** → **Push origin**.

### Cách B — Git CLI
```bash
cd ~/Documents/my-agent
git init
git add .
git commit -m "Agent doi soat ZION-SACOMBANK - first deploy"
# Tạo repo trống trên github.com trước (NÊN chọn Private), rồi:
git branch -M main
git remote add origin https://github.com/<username>/<ten-repo>.git
git push -u origin main
```
> Lần push đầu GitHub hỏi đăng nhập → dùng **Personal Access Token** thay mật khẩu
> (GitHub → Settings → Developer settings → Tokens). Bạn tự nhập, đừng đưa token cho ai.

**Link repo này chính là thứ nộp bài.**

## 5. Deploy lên AgentBase (GreenNode)
Theo Sổ tay (Phần 3B, con đường Claude Code CLI):
```bash
cd ~/Documents/my-agent
git clone https://github.com/vngcloud/greennode-agentbase-skills .agentbase
claude        # mở Claude Code CLI trong folder này
```
Trong Claude Code, gõ:
```
Deploy agent trong folder hien tai len AgentBase. Dockerfile da co san, agent chay
o cong 8000, endpoint POST /reconcile va GET /report.
```
Claude Code sẽ hỏi config — chọn **Recommended**:
- Registry? → Recommended
- Network? → **PUBLIC** (để có link public; chỉ làm vậy nếu chấp nhận công khai endpoint)
- CPU? → **2CPU/4GB** (Recommended)
- Nhập **IAM credential** khi được hỏi (bạn tự nhập, lấy ở GreenNode Portal → IAM → Credentials).

Xong (~15–20 phút) bạn nhận **link endpoint public**. Nếu còn `localhost` → gõ:
"Chuyển endpoint sang public mode".

## 6. Nộp bài
- Link **GitHub repo** (bước 4)
- Link **endpoint AgentBase** (bước 5)
- Deadline **17/06 12:00** (Fail thì sửa đến 18/06).

---
### ⚠️ Lưu ý dữ liệu nhạy cảm
Repo này chứa dữ liệu thật trong `data/input/`. Nếu để **Network PUBLIC** + repo public,
endpoint và dữ liệu sẽ công khai. Khuyến nghị: repo **Private**; nếu cần demo công khai,
xoá `data/input/*` và chạy `python run.py --sample` (dữ liệu giả lập).
