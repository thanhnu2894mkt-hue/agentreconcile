"""Entrypoint agent doi soat ZION <-> SACOMBANK.

Vi du:
  python run.py                 # doc data tu data/input, xuat ra data/output
  python run.py --sample        # sinh data gia lap truoc roi chay
  RECON_PERIOD=06 python run.py # doi ky doi soat
"""
import argparse
import os
import sys

import config as C
from src.recon import run_recon
from src.report import build_report


def main():
    ap = argparse.ArgumentParser(description="Agent doi soat ZION <-> SACOMBANK")
    ap.add_argument("--sample", action="store_true", help="Sinh du lieu gia lap truoc khi chay")
    args = ap.parse_args()

    if args.sample:
        from src.generate_sample_data import main as gen
        gen()

    missing = [k for k in C.FILES if not os.path.exists(C.input_path(k))]
    if missing:
        print("THIEU file dau vao trong %s:" % C.INPUT_DIR, file=sys.stderr)
        for k in missing:
            print("  - [%s] %s" % (k, C.FILES[k]), file=sys.stderr)
        print("Goi y: chay 'python run.py --sample' de sinh du lieu gia lap.", file=sys.stderr)
        sys.exit(1)

    print("Doc du lieu tu:", C.INPUT_DIR)
    tc, rf, summ = run_recon()
    out = os.path.join(C.OUTPUT_DIR, C.OUTPUT_XLSX)
    build_report(tc, rf, summ, C.RECON_PERIOD, out)

    print("=== KET QUA (ky %s) ===" % C.RECON_PERIOD)
    print("  ZION  TC: %d GD | phi %s" % (summ["tc_cnt"], f"{summ['tc_fee']:,.0f}"))
    print("  ZION  RF: %d GD | phi %s" % (summ["rf_cnt"], f"{summ['rf_fee']:,.0f}"))
    print("  NET ZION:     %s" % f"{summ['net_zion']:,.0f}")
    print("  NET SACOMBANK:%s" % f"{summ['net_sacom']:,.0f}")
    print("  CHENH LECH:   %s" % f"{summ['chenh_lech']:,.2f}")
    print("  Phi xu ly GD: %s" % f"{summ['phi_xu_ly']:,.0f}")
    print("Da xuat:", out)


if __name__ == "__main__":
    main()
