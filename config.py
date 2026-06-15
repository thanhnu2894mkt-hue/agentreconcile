"""Cau hinh tap trung cho agent doi soat ZION <-> SACOMBANK.

Tat ca duong dan / hang so co the override bang bien moi truong (env)
=> thuan tien khi chay tren CI, Docker, Greenode.
"""
import os

# --- Thu muc ---
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR  = os.environ.get("INPUT_DIR",  os.path.join(BASE_DIR, "data", "input"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "data", "output"))
OUTPUT_XLSX = os.environ.get("OUTPUT_XLSX", "DOI_SOAT_ZION_SACOMBANK.xlsx")

# --- Ten file dau vao (giu nguyen ten goc; co the doi qua env) ---
FILES = {
    "TC":  os.environ.get("FILE_TC",  "1DATAZION_THÀNH_CÔNG.xlsx"),   # ZION Thanh cong
    "RF":  os.environ.get("FILE_RF",  "1DATA_ZION_HOÀN_TIỀN.xlsx"),   # ZION Hoan tien
    "CV":  os.environ.get("FILE_CV",  "1DATAZIONHOANTIENCV.xlsx"),    # ZION Hoan tien CV (PHI ZLP)
    "AP":  os.environ.get("FILE_AP",  "1APPLEPAY.xlsx"),              # ApplePay
    "JCB": os.environ.get("FILE_JCB", "1JCB.xlsx"),                   # JCB BIN
    "SB":  os.environ.get("FILE_SB",  "1DATA_SACOMBANK.xlsx"),        # SACOMBANK
}

# --- Hang so nghiep vu ---
SACOM_NAME    = "SAIGON THUONG TIN COMMERCIAL JOINT STOCK BANK"
RECON_PERIOD  = os.environ.get("RECON_PERIOD", "05")  # ky doi soat dang chot (MM); cac thang sau chot ky sau
PROCESS_FEE   = 440                                   # phi xu ly moi GD
RATE_MAP      = {1: 0.01, 2: 0.02, 3: 0.0242}         # Isonus -> ty le phi

# Nguong loc sheet chi tiet: chi xuat GD co |CL| lam tron != 0
CL_ROUND_TOL  = 0  # so chu so thap phan khi lam tron CL de loc

def input_path(key: str) -> str:
    return os.path.join(INPUT_DIR, FILES[key])
