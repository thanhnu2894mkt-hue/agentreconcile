"""Sinh du lieu GIA LAP (synthetic) cho 6 file dau vao.

Muc dich: cho phep build & test agent tren GitHub/CI/Docker ma KHONG can du lieu that.
Du lieu sinh ra nhat quan noi bo (ID khop giua cac file) va co du cac nhanh:
SKIP, APPLEPAY_Y, JCB_Y/JCB_N, ABNORMAL, chenh lech CL...

Chay:  python -m src.generate_sample_data   (hoac)  python src/generate_sample_data.py
"""
import os
import random
import numpy as np
import pandas as pd

import config as C

SEED = int(os.environ.get("SAMPLE_SEED", "42"))
N_TC = int(os.environ.get("SAMPLE_N_TC", "60"))
N_RF = int(os.environ.get("SAMPLE_N_RF", "30"))
rng = random.Random(SEED)
np.random.seed(SEED)

SACOM = C.SACOM_NAME
OTHER_BANKS = ["VIETCOMBANK", "TECHCOMBANK", "BIDV", "ACB", "MB BANK"]
RATE = C.RATE_MAP


def tid():
    return str(rng.randint(7 * 10**21, 8 * 10**21 - 1))


def trace():
    return "ZP" + "".join(rng.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(10))


def book_date():
    mm = rng.choice(["05", "05", "05", "06"])           # nghieng ve ky 05
    dd = f"{rng.randint(1,28):02d}"
    return int(f"2026{mm}{dd}")


def isonus_rate(iso):
    return RATE[iso]


def main():
    os.makedirs(C.INPUT_DIR, exist_ok=True)

    # JCB BIN table (gom SACOM + ngan hang khac)
    jcb_rows = []
    jcb_bins = []
    for k in range(10):
        b8 = 35670000 + k * 137
        bank = SACOM if k % 4 == 0 else rng.choice(OTHER_BANKS)
        jcb_rows.append({"BIN 8 SỐ": b8, "6 SỐ ĐẦU": str(b8)[:6], "Ngân hàng": bank,
                         "Viet tat": "ABC", "Ghi chú loại thẻ": "Credit"})
        jcb_bins.append((str(b8), bank))
    pd.DataFrame(jcb_rows).to_excel(os.path.join(C.INPUT_DIR, C.FILES["JCB"]), index=False)

    tc, sb, ap = [], [], []

    for n in range(N_TC):
        bid = tid(); tr = trace(); amt = rng.choice([60000, 100000, 140000, 250000, 690000, 980000])
        branch = rng.choices(["skip", "dpan_visa", "dpan_jcb"], weights=[6, 3, 1])[0]
        if branch == "skip":
            iso = rng.choice([1, 2, 2, 3]); ct = rng.choice(["VISA", "MASTER", "AMEX"])
            stt = rng.choice(["PAY", "PAY_BY_TOKEN"]); fee = round(amt * isonus_rate(iso) + C.PROCESS_FEE, 2)
            binno = str(rng.randint(400000, 499999))
        elif branch == "dpan_visa":
            iso = None; ct = rng.choice(["VISA", "MASTER", "AMEX"]); stt = "PAY_BY_DPAN"; fee = 0
            binno = str(rng.randint(400000, 499999))
        else:  # dpan_jcb
            iso = None; ct = "JCB"; stt = "PAY_BY_DPAN"; fee = 0
            binno = rng.choice(jcb_bins)[0] + str(rng.randint(10, 99))  # 8 so + duoi
        tc.append({"Bank Trans ID": bid, "Trace No": tr, "Sub Trans Type": stt, "Amount": amt,
                   "Trans Time": "28/04/2026 19:06:15", "Card Type": ct, "BankMID": "vngcorp",
                   "Is On Us": iso, "Fee Rate": fee, "Bin No": binno, "L4 Card No": str(rng.randint(1000, 9999))})
        # ApplePay cho dpan_visa (key RequestID = Bank Trans ID)
        if branch == "dpan_visa":
            country = rng.choices(["VN", "US", "AE"], weights=[5, 3, 2])[0]
            issuer = SACOM if (country == "VN" and rng.random() < 0.4) else rng.choice(OTHER_BANKS)
            iso_eff = 1 if (country == "VN" and issuer == SACOM) else (2 if country == "VN" else 3)
            ap.append({"RequestID": bid, "MerchantReferenceNumber": tr, "BinCountry": country,
                       "BinIssuer": issuer, "Amount": amt, "Status": "BATCHED", "MerchantID": "vngcorp",
                       "BinScheme": "VISA CREDIT", "BinNumber": binno})
            disc = round(amt * isonus_rate(iso_eff))
        else:
            iso_eff = iso if iso else 2
            if branch == "dpan_jcb":
                bank = dict(jcb_bins).get(binno[:8])
                iso_eff = 1 if bank == SACOM else (2 if bank else 3)
            disc = round(amt * isonus_rate(iso_eff))
        # tao chenh lech ngau nhien ~15%
        if rng.random() < 0.15:
            disc += rng.choice([-500, -200, 300, 800])
        sb.append({"MM_DBA_NAME": "ZION", "CARDNO": str(rng.randint(10**11, 10**12)),
                   "TRANS_AMOUNT": amt, "BILLING_AMOUNT": amt, "DISCOUNT": disc,
                   "PROC_DATE": 20260429, "BOOK_DATE": book_date(),
                   "CrdType": "VS-LOCAL", "ReqRecId": bid})

    rf, cv = [], []
    for n in range(N_RF):
        rbid = tid(); tr = trace(); amtr = rng.choice([240000, 360000, 2647000, 4366000, 7117180])
        branch = rng.choices(["nondpan_skip", "nondpan_empty", "dpan_visa"], weights=[4, 3, 4])[0]
        if branch == "nondpan_skip":
            iso = rng.choice([1, 2, 3]); cs = rng.choice(["VISA", "MASTER"]); stt = rng.choice(["PAY", "PAY_BY_TOKEN"])
            fee = round(amtr * isonus_rate(iso), 2)
        elif branch == "nondpan_empty":
            iso = None; cs = None; stt = rng.choice(["PAY", "PAY_BY_TOKEN"]); fee = 0
        else:
            iso = None; cs = rng.choice(["VISA", "MASTER"]); stt = "PAY_BY_DPAN"; fee = 0
        rf.append({"traceNo": tr, "Refund Bank Trans ID": rbid, "Amount": amtr, "Refund Amount": amtr,
                   "Refund Trans Time": "30/04/2026 01:30:00", "Is On Us": iso, "Bank Account": "vngcorp",
                   "Fee Rate": fee, "Sub Trans Type": stt, "Card Scheme": cs,
                   "F6 Card No": str(rng.randint(100000, 999999)), "L4 Card No": str(rng.randint(1000, 9999))})
        if branch == "dpan_visa":
            country = rng.choices(["VN", "US"], weights=[6, 4])[0]
            issuer = SACOM if (country == "VN" and rng.random() < 0.4) else rng.choice(OTHER_BANKS)
            iso_eff = 1 if (country == "VN" and issuer == SACOM) else (2 if country == "VN" else 3)
            ap.append({"RequestID": tid(), "MerchantReferenceNumber": tr, "BinCountry": country,
                       "BinIssuer": issuer, "Amount": amtr, "Status": "BATCHED", "MerchantID": "vngcorp",
                       "BinScheme": "VISA CREDIT", "BinNumber": "470000"})
            fee_eff = round(amtr * isonus_rate(iso_eff))
        elif branch == "nondpan_empty":
            fee_eff = round(amtr * 0.02)  # PHI ZLP tu CV
            cv.append({"traceNo": tr, "Refund Bank Trans ID": rbid, "Amount": amtr, "Refund Amount": amtr,
                       "Refund Trans Time": "30/04/2026", "Bank Account": "vngcorp", "Fee Rate": 0,
                       "Sub Trans Type": stt, "Refund Sub Trans Type": "REFUND",
                       "F6 Card No": "356505", "L4 Card No": "7676", "BINCOUNTRY": None, "BINISSER": None,
                       "BOOK_DATE (BANK)": book_date(), "DISCOUNT (BANK)": -fee_eff, "PHI +440": fee_eff + 440,
                       "PHI XLGD": 440, "PHI ZLP": fee_eff, "TỶ LÊ": 0.02, "Chốt VAT": "05"})
        else:
            fee_eff = round(amtr * isonus_rate(iso))
        disc = -fee_eff
        if rng.random() < 0.15:
            disc += rng.choice([-300, 200, 500])
        sb.append({"MM_DBA_NAME": "ZION", "CARDNO": str(rng.randint(10**11, 10**12)),
                   "TRANS_AMOUNT": amtr, "BILLING_AMOUNT": amtr, "DISCOUNT": disc,
                   "PROC_DATE": 20260429, "BOOK_DATE": book_date(),
                   "CrdType": "VS-LOCAL", "ReqRecId": rbid})

    pd.DataFrame(tc).to_excel(os.path.join(C.INPUT_DIR, C.FILES["TC"]), index=False)
    pd.DataFrame(rf).to_excel(os.path.join(C.INPUT_DIR, C.FILES["RF"]), index=False)
    pd.DataFrame(cv).to_excel(os.path.join(C.INPUT_DIR, C.FILES["CV"]), index=False)
    pd.DataFrame(sb).to_excel(os.path.join(C.INPUT_DIR, C.FILES["SB"]), index=False)

    # ApplePay: banner o dong 1, header o dong 2 (doc bang header=1)
    ap_df = pd.DataFrame(ap)
    with pd.ExcelWriter(os.path.join(C.INPUT_DIR, C.FILES["AP"]), engine="openpyxl") as w:
        ap_df.to_excel(w, index=False, startrow=1, sheet_name="APPLE PAY")
        w.sheets["APPLE PAY"]["A1"] = "zalopay_acct | Apple pay | PaymentBatchDetail (SYNTHETIC)"

    print(f"Sinh du lieu gia lap xong tai {C.INPUT_DIR}")
    print(f"  TC={len(tc)}  RF={len(rf)}  SB={len(sb)}  AP={len(ap)}  CV={len(cv)}  JCB={len(jcb_rows)}")


if __name__ == "__main__":
    main()
