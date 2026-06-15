"""Buoc 1-3: chuan hoa du lieu, dien ISONUS/FEERATE, doi soat voi SACOMBANK.

run_recon() tra ve (tc_df, rf_df, summary_dict).
Logic bam theo Instruction.docx (muc 1.1, 1.2, Buoc 2, Buoc 3).
"""
import numpy as np
import pandas as pd

import config as C


def _jcb_lookups(jcb):
    jcb = jcb.copy()
    jcb["bin8"] = jcb["BIN 8 SỐ"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    jcb["bin6"] = jcb["6 SỐ ĐẦU"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().str[:6]
    j8 = jcb.dropna(subset=["Ngân hàng"]).set_index("bin8")["Ngân hàng"].to_dict()
    j6 = jcb.dropna(subset=["Ngân hàng"]).groupby("bin6")["Ngân hàng"].first().to_dict()
    return j8, j6


def _make_jcb_bank(j8, j6):
    def jcb_bank(binno):
        s = str(binno).replace(".0", "").strip()
        if s in ("nan", ""):
            return None
        if s[:8] in j8:
            return j8[s[:8]]
        if s[:6] in j6:
            return j6[s[:6]]
        return None
    return jcb_bank


def _isonus_from_country_issuer(bc, bi):
    if bc is None or (isinstance(bc, float) and np.isnan(bc)):
        return None
    bcu = str(bc).strip().upper()
    biu = str(bi).strip().upper()
    if bcu == "VN":
        return 1 if biu == C.SACOM_NAME.upper() else 2
    return 3


def run_recon():
    SACOM = C.SACOM_NAME
    RATE = C.RATE_MAP
    PERIOD = C.RECON_PERIOD
    CARDS_AP = {"VISA", "MASTER", "MASTERCARD", "AMEX"}

    # ---------- load ----------
    tc = pd.read_excel(C.input_path("TC"))
    rf = pd.read_excel(C.input_path("RF")).dropna(axis=1, how="all")
    sb = pd.read_excel(C.input_path("SB")).dropna(axis=1, how="all")
    ap = pd.read_excel(C.input_path("AP"), header=1)
    jcb = pd.read_excel(C.input_path("JCB"))
    cv = pd.read_excel(C.input_path("CV"))

    # ---------- SACOMBANK lookups (key = ReqRecId) ----------
    sb["req"] = sb["ReqRecId"].astype(str).str.strip()
    sb["MM"] = sb["BOOK_DATE"].astype("Int64").astype(str).str[4:6]
    sb_disc = sb.set_index("req")["DISCOUNT"].to_dict()
    sb_mm = sb.set_index("req")["MM"].to_dict()
    sb_book = sb.set_index("req")["BOOK_DATE"].astype("Int64").to_dict()

    # ---------- ApplePay lookups ----------
    ap["rid"] = ap["RequestID"].astype(str).str.strip()                    # TC key = Bank Trans ID
    ap["mref"] = ap["MerchantReferenceNumber"].astype(str).str.strip()     # RF key = BC TRACE NO
    ap_bc = ap.set_index("rid")["BinCountry"].to_dict()
    ap_bi = ap.set_index("rid")["BinIssuer"].to_dict()
    ap_bc_m = ap.dropna(subset=["mref"]).groupby("mref")["BinCountry"].first().to_dict()
    ap_bi_m = ap.dropna(subset=["mref"]).groupby("mref")["BinIssuer"].first().to_dict()

    # ---------- JCB lookups ----------
    j8, j6 = _jcb_lookups(jcb)
    jcb_bank = _make_jcb_bank(j8, j6)

    # ---------- CV (HOANCV) PHI ZLP by Refund Bank Trans ID ----------
    cv["rbtid"] = cv["Refund Bank Trans ID"].astype(str).str.strip()
    cv_zlp = cv.set_index("rbtid")["PHI ZLP"].to_dict()

    # =====================================================================
    # 1.1 + Buoc 2 : ZION THANH CONG
    # =====================================================================
    tc["btid"] = tc["Bank Trans ID"].astype(str).str.strip()
    tc["ISONUS"] = tc["Is On Us"]
    tc["FEERATE"] = tc["Fee Rate"].astype(float)
    for col in ("CHECKISONUS", "BinCountry", "BinIssuer", "Ten ngan hang", "MARK"):
        tc[col] = ""
    tc["RATE"] = np.nan

    for i, r in tc.iterrows():
        iso = r["Is On Us"]
        amt = float(r["Amount"])
        if pd.notna(iso) and int(iso) in (1, 2, 3):                  # TH1: SKIP
            tc.at[i, "CHECKISONUS"] = "SKIP"; tc.at[i, "ISONUS"] = int(iso); continue
        stt = str(r["Sub Trans Type"]).strip()
        ct = str(r["Card Type"]).strip().upper()
        if stt == "PAY_BY_DPAN" and ct in CARDS_AP:                  # 1.1.1.1 ApplePay (key Bank Trans ID)
            bc = ap_bc.get(r["btid"]); bi = ap_bi.get(r["btid"])
            new_iso = _isonus_from_country_issuer(bc, bi)
            if new_iso is not None:
                tc.at[i, "ISONUS"] = new_iso; tc.at[i, "BinCountry"] = bc; tc.at[i, "BinIssuer"] = bi
                tc.at[i, "CHECKISONUS"] = "APPLEPAY_Y"; tc.at[i, "MARK"] = "AP"
                tc.at[i, "RATE"] = RATE[new_iso]; tc.at[i, "FEERATE"] = amt * RATE[new_iso] + C.PROCESS_FEE
            else:
                tc.at[i, "CHECKISONUS"] = "APPLEPAY_N"
        elif stt == "PAY_BY_DPAN" and ct == "JCB":                  # 1.1.1.2 JCB (key Bin No)
            bank = jcb_bank(r["Bin No"])
            if bank is not None:
                new_iso = 1 if str(bank).strip().upper() == SACOM.upper() else 2
                tc.at[i, "Ten ngan hang"] = bank; tc.at[i, "CHECKISONUS"] = "JCB_Y"
            else:
                new_iso = 3; tc.at[i, "CHECKISONUS"] = "JCB_N"
            tc.at[i, "MARK"] = "JCB"; tc.at[i, "ISONUS"] = new_iso
            tc.at[i, "RATE"] = RATE[new_iso]; tc.at[i, "FEERATE"] = amt * RATE[new_iso] + C.PROCESS_FEE

    mask_abn = (tc["CHECKISONUS"].isin(["", "APPLEPAY_N"])) & (~tc["ISONUS"].isin([1, 2, 3]))
    tc.loc[mask_abn, "CHECKISONUS"] = "ABNORMAL"                     # 1.1.1.3

    tc["FEERATE_DC"] = np.where(tc["FEERATE"] > 0, tc["FEERATE"] - C.PROCESS_FEE, 0.0)  # Buoc 2
    tc["Ghi chu"] = np.where(tc["FEERATE"] <= 0, "Miss Feerate", "")
    tc["DISCOUNT"] = tc["btid"].map(sb_disc)
    tc["DISCOUNT_ABS"] = tc["DISCOUNT"].abs()
    tc["KY_CHOT"] = tc["btid"].map(sb_book)
    tc["MM"] = tc["btid"].map(sb_mm)
    tc["CL"] = tc["FEERATE_DC"] - tc["DISCOUNT_ABS"]
    tc["TYLE"] = np.where(tc["Amount"] > 0, tc["FEERATE_DC"] / tc["Amount"], np.nan)

    # =====================================================================
    # 1.2 + Buoc 2 : ZION HOAN TIEN
    # =====================================================================
    rf["rbtid"] = rf["Refund Bank Trans ID"].astype(str).str.strip()
    rf["trace"] = rf["traceNo"].astype(str).str.strip()
    rf["ISONUS"] = rf["Is On Us"]
    rf["FEERATE"] = rf["Fee Rate"].astype(float)
    for col in ("CHECKISONUS", "BinCountry", "BinIssuer", "Ten ngan hang", "MARK"):
        rf[col] = ""
    rf["RATE"] = np.nan

    for i, r in rf.iterrows():
        iso = r["Is On Us"]
        stt = str(r["Sub Trans Type"]).strip()
        amtr = float(r["Refund Amount"])
        cs = str(r["Card Scheme"]).strip().upper()

        if stt != "PAY_BY_DPAN":                                    # TH1 & TH2
            if pd.notna(iso) and int(iso) in (1, 2, 3):
                rf.at[i, "CHECKISONUS"] = "SKIP"; rf.at[i, "ISONUS"] = int(iso)
            else:
                rf.at[i, "CHECKISONUS"] = "ABNORMAL"; rf.at[i, "MARK"] = "GREEN"
            continue

        # TH3: PAY_BY_DPAN -> kiem tra lai, Feerate dieu chinh = AmountRefund * rate%
        if cs in CARDS_AP:                                          # 1.2.1.1 ApplePay (key BC TRACE NO)
            bc = ap_bc_m.get(r["trace"]); bi = ap_bi_m.get(r["trace"])
            new_iso = _isonus_from_country_issuer(bc, bi)
            if new_iso is not None:
                rf.at[i, "ISONUS"] = new_iso; rf.at[i, "BinCountry"] = bc; rf.at[i, "BinIssuer"] = bi
                rf.at[i, "CHECKISONUS"] = "APPLEPAY_Y"; rf.at[i, "MARK"] = "AP"
                rf.at[i, "RATE"] = RATE[new_iso]; rf.at[i, "FEERATE"] = amtr * RATE[new_iso]
            elif pd.notna(iso) and int(iso) in (1, 2, 3):
                rf.at[i, "CHECKISONUS"] = "APPLEPAY_N"; rf.at[i, "ISONUS"] = int(iso)
                rf.at[i, "RATE"] = RATE[int(iso)]; rf.at[i, "FEERATE"] = amtr * RATE[int(iso)]
            else:
                rf.at[i, "CHECKISONUS"] = "ABNORMAL"; rf.at[i, "MARK"] = "GREEN"
        elif cs == "JCB":                                           # 1.2.1.2 JCB
            bank = jcb_bank(r.get("F6 Card No"))
            if bank is not None:
                new_iso = 1 if str(bank).strip().upper() == SACOM.upper() else 2
                rf.at[i, "Ten ngan hang"] = bank; rf.at[i, "CHECKISONUS"] = "JCB_Y"
            else:
                new_iso = 3; rf.at[i, "CHECKISONUS"] = "JCB_N"
            rf.at[i, "MARK"] = "JCB"; rf.at[i, "ISONUS"] = new_iso
            rf.at[i, "RATE"] = RATE[new_iso]; rf.at[i, "FEERATE"] = amtr * RATE[new_iso]
        else:                                                       # DPAN thieu scheme -> 1.2.1.3
            if pd.notna(iso) and int(iso) in (1, 2, 3):
                rf.at[i, "CHECKISONUS"] = "APPLEPAY_N"; rf.at[i, "ISONUS"] = int(iso)
                rf.at[i, "RATE"] = RATE[int(iso)]; rf.at[i, "FEERATE"] = amtr * RATE[int(iso)]
            else:
                rf.at[i, "CHECKISONUS"] = "ABNORMAL"; rf.at[i, "MARK"] = "GREEN"

    # ABNORMAL -> Feerate = PHI ZLP tu HOANCV
    for i in rf[rf["CHECKISONUS"] == "ABNORMAL"].index:
        z = cv_zlp.get(rf.at[i, "rbtid"])
        if z is not None and pd.notna(z):
            rf.at[i, "FEERATE"] = float(z)

    rf["FEERATE_DC"] = rf["FEERATE"]                                # Buoc 2: giu nguyen
    rf["DISCOUNT"] = rf["rbtid"].map(sb_disc)
    rf["DISCOUNT_ABS"] = rf["DISCOUNT"].abs()
    rf["KY_CHOT"] = rf["rbtid"].map(sb_book)
    rf["MM"] = rf["rbtid"].map(sb_mm)
    rf["CL"] = rf["FEERATE_DC"] - rf["DISCOUNT_ABS"]
    rf["TYLE"] = np.where(rf["Refund Amount"] > 0, rf["FEERATE_DC"] / rf["Refund Amount"], np.nan)

    # =====================================================================
    # Buoc 3 : Summary cho ky doi soat
    # =====================================================================
    tcP = tc[tc["MM"] == PERIOD]
    rfP = rf[rf["MM"] == PERIOD]
    summary = {
        "tc_cnt": int(len(tcP)), "tc_amt": float(tcP["Amount"].sum()), "tc_fee": float(tcP["FEERATE_DC"].sum()),
        "rf_cnt": int(len(rfP)), "rf_amt": float(rfP["Refund Amount"].sum()), "rf_fee": float(rfP["FEERATE_DC"].sum()),
        "sb_tc_fee": float(tcP["DISCOUNT_ABS"].sum()), "sb_rf_fee": float(rfP["DISCOUNT_ABS"].sum()),
    }
    summary["net_zion"] = summary["tc_fee"] - summary["rf_fee"]
    summary["net_sacom"] = summary["sb_tc_fee"] - summary["sb_rf_fee"]
    summary["chenh_lech"] = summary["net_zion"] - summary["net_sacom"]
    summary["phi_xu_ly"] = (summary["tc_cnt"] + summary["rf_cnt"]) * C.PROCESS_FEE

    return tc, rf, summary
