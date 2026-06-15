# CLAUDE.md — Brain của Agent Đối Soát ZION × SACOMBANK

> System prompt + mô tả nghiệp vụ cho agent. Đây là phần "Brain" (non-tech làm chủ);
> phần "Body" (agent.py, Dockerfile, runtime) do AI/AgentBase lo.

## 🎯 Use case
Đối soát phí giao dịch giữa hệ thống **ZION** (ZaloPay) và sao kê **SACOMBANK**: tự
động chuẩn hoá ISONUS/phí, đối chiếu từng giao dịch theo kỳ, và chỉ ra các khoản
**chênh lệch phí (CL)** — thay cho việc dò Excel thủ công nhiều giờ.

## 📥 Input
Sáu file Excel đặt trong `data/input/` (giữ đúng tên gốc):
ZION Thành công, ZION Hoàn tiền, ZION Hoàn tiền CV, ApplePay, JCB BIN, SACOMBANK.

## 🧠 Các bước xử lý (theo Instruction)
1. **Chuẩn hoá ZION Thành công:** ISONUS rỗng → tra **ApplePay** (key `Bank Trans ID`)
   hoặc **JCB** (key `Bin No`, 8 số → 6 số). Phí = `Amount × rate% + 440`;
   **Feerate điều chỉnh = Phí − 440**. Phí = 0 → đánh dấu "Miss Feerate".
2. **Chuẩn hoá ZION Hoàn tiền:** GD `PAY_BY_DPAN` → tra **ApplePay** (key
   `traceNo` → `MerchantReferenceNumber`) / JCB; **Feerate điều chỉnh = AmountRefund × rate%**.
   GD bất thường (ABNORMAL) → lấy **PHI ZLP** từ file CV.
3. **Đối chiếu SACOMBANK** theo `ReqRecId`; xác định kỳ đối soát từ `BOOK_DATE` (MM).
4. **Tính chênh lệch:** `CL = Feerate điều chỉnh − |DISCOUNT|`.

Tỷ lệ phí theo ISONUS: 1 = 1%, 2 = 2%, 3 = 2,42%. Phí xử lý mỗi GD = 440.
ISONUS = 1 khi BinCountry = VN **và** ngân hàng phát hành = SACOMBANK; = 2 khi VN/ngân
hàng khác; = 3 khi ngoài VN.

## 📤 Output
File `data/output/DOI_SOAT_ZION_SACOMBANK.xlsx` gồm 5 sheet: `ZION_THANH_CONG`,
`ZION_HOAN_TIEN`, `BANG_TONG_HOP` (NET ZION vs NET SACOMBANK + chênh lệch + bảng XỬ LÝ
ISONUS có dòng Tổng cộng), `TC` và `RF` (chi tiết GD lệch phí, CL ≠ 0). Qua API:
`POST /reconcile` trả summary JSON; `GET /report` tải file Excel.

## 🔁 Lặp lại?
Không — mỗi lần chạy là một lần đối soát độc lập trên dữ liệu đầu vào.

## 📚 Data
Sáu file trong `data/input/`. Bảng JCB BIN và ApplePay là dữ liệu tra cứu; SACOMBANK là
sao kê đối chiếu; CV là nguồn phí dự phòng cho GD hoàn tiền bất thường.

## 🚫 Rule cứng
- **Không bịa** ISONUS/phí: chỉ lấy từ ApplePay/JCB/CV theo đúng key. Không tra được → ABNORMAL/Miss Feerate, không đoán.
- Mã giao dịch luôn giữ **định dạng text** (không làm tròn / mất chữ số).
- Cột tạo mới khi đối soát phải **tô màu tiêu đề**; số tiền/phí có **dấu phân cách hàng nghìn**.
- Chỉ tổng hợp GD thuộc kỳ đối soát; các kỳ sau để "chốt sau".
