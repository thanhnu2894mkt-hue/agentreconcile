# Agent Đối Soát ZION ↔ SACOMBANK

Agent tự động đối soát phí giao dịch giữa **ZION** và **SACOMBANK**: chuẩn hóa
ISONUS/FEERATE (ApplePay, JCB, HOANCV), tính chênh lệch **CL** theo kỳ đối soát,
và xuất báo cáo Excel nhiều sheet. Đóng gói sẵn để build trên **GitHub + Docker**
(ví dụ Greenode), kèm **bộ sinh dữ liệu giả lập** để chạy/test mà không cần dữ liệu thật.

## Cấu trúc

```
zion-recon/
├── config.py                   # Cấu hình (đường dẫn, tên file, hằng số nghiệp vụ) — override bằng env
├── run.py                      # Entrypoint
├── src/
│   ├── recon.py                # Bước 1–3: chuẩn hóa + đối soát
│   ├── report.py               # Bước 3–4: dựng workbook (5 sheet, format, màu)
│   └── generate_sample_data.py # Sinh 6 file dữ liệu giả lập, nhất quán nội bộ
├── data/
│   ├── input/                  # ĐẶT 6 file dữ liệu thật vào đây (đã .gitignore)
│   └── output/                 # Báo cáo xuất ra
├── Dockerfile / docker-compose.yml
├── requirements.txt / Makefile
└── .github/workflows/ci.yml    # CI: sinh data giả lập → chạy → upload báo cáo
```

## Dữ liệu đầu vào (6 file, đặt trong `data/input/`)

| Khóa | File mặc định | Vai trò |
|------|---------------|---------|
| TC  | `1DATAZION_THÀNH_CÔNG.xlsx` | ZION Thành công |
| RF  | `1DATA_ZION_HOÀN_TIỀN.xlsx` | ZION Hoàn tiền |
| CV  | `1DATAZIONHOANTIENCV.xlsx`  | ZION Hoàn tiền CV (PHI ZLP) |
| AP  | `1APPLEPAY.xlsx`            | ApplePay (BinCountry/BinIssuer) |
| JCB | `1JCB.xlsx`                 | Bảng BIN JCB |
| SB  | `1DATA_SACOMBANK.xlsx`      | SACOMBANK |

Đổi tên file qua env `FILE_TC`, `FILE_RF`, … nếu cần.

## Chạy nhanh (local)

> Nhanh nhất: chạy `./setup.sh` — tự cài deps, build/chạy và smoke-test endpoint.
> Dùng `./setup.sh --docker`, `./setup.sh --sample`, hoặc `./setup.sh --batch` tuỳ nhu cầu.


```bash
pip install -r requirements.txt

# Chạy trên 6 file THẬT (đã có sẵn trong data/input/):
python run.py

# Hoặc test bằng dữ liệu GIẢ LẬP (ghi đè data/input):
python run.py --sample
```

Báo cáo: `data/output/DOI_SOAT_ZION_SACOMBANK.xlsx` (5 sheet: ZION_THANH_CONG,
ZION_HOAN_TIEN, BANG_TONG_HOP, TC, RF).

## Docker

> Image này **đã nhúng sẵn 6 file dữ liệu thật** trong `data/input/`, nên `docker run`
> sẽ chạy ngay trên dữ liệu thật. File kết quả nằm trong container ở `/app/data/output`;
> mount thư mục để lấy ra ngoài.

```bash
# Build
docker build -t zion-recon:latest .

# Chạy trên data thật, lấy báo cáo ra ./data/output trên máy host
docker run --rm -v "$PWD/data/output:/app/data/output" zion-recon:latest

# (tuỳ chọn) test bằng data giả lập
docker run --rm -v "$PWD/data/output:/app/data/output" zion-recon:latest --sample
```

Hoặc dùng docker-compose:

```bash
docker compose run --rm recon
```

## Cấu hình qua biến môi trường

| Env | Mặc định | Ý nghĩa |
|-----|----------|---------|
| `INPUT_DIR` / `OUTPUT_DIR` | `data/input` / `data/output` | Thư mục vào/ra |
| `RECON_PERIOD` | `05` | Kỳ đối soát (MM); các kỳ sau chốt sau |
| `OUTPUT_XLSX` | `DOI_SOAT_ZION_SACOMBANK.xlsx` | Tên file kết quả |
| `SAMPLE_SEED` / `SAMPLE_N_TC` / `SAMPLE_N_RF` | `42 / 60 / 30` | Tham số sinh data giả lập |

## Logic nghiệp vụ (tóm tắt theo Instruction)

- **TC (Thành công):** ISONUS rỗng → tra ApplePay (key `Bank Trans ID`) hoặc JCB (key `Bin No`,
  8 số → 6 số). FEERATE = `Amount × rate% + 440`; **Feerate điều chỉnh = FEERATE − 440**.
  FEERATE = 0 → "Miss Feerate" (tô đỏ).
- **RF (Hoàn tiền):** PAY_BY_DPAN → tra ApplePay (key **`traceNo` → MerchantReferenceNumber**) /
  JCB; **Feerate điều chỉnh = AmountRefund × rate%**. ABNORMAL → lấy **PHI ZLP** từ file CV.
- **CL = Feerate điều chỉnh − |DISCOUNT|** (đối chiếu SACOMBANK theo `ReqRecId`).
- Báo cáo chỉ tổng hợp GD trong kỳ đối soát; bảng XỬ LÝ ISONUS có dòng **Tổng cộng**.
- Cột tạo mới khi đối soát: **tô màu cam** ở tiêu đề; số tiền/phí có **dấu phân cách hàng nghìn**;
  mã giao dịch giữ **định dạng text**.

> Công thức trong file Excel được đặt `fullCalcOnLoad`: tự tính lại khi mở bằng Excel/LibreOffice,
> nên image Docker **không cần** cài LibreOffice.

## Lưu ý bảo mật dữ liệu

Bản này **có sẵn 6 file dữ liệu thật** trong `data/input/` (theo yêu cầu để build/chạy trực tiếp).
Vì đây là dữ liệu giao dịch thật (mã GD, số thẻ F6/L4, số tiền, chiết khấu SACOMBANK),
**nên dùng repo PRIVATE** khi đẩy lên GitHub. Nếu cần demo công khai, hãy xoá data trong
`data/input/` và dùng `python run.py --sample` (bộ sinh dữ liệu giả lập).
