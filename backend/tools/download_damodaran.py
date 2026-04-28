"""Download all 244 Damodaran Excel files from NYU Stern website.

Usage:
    python backend/tools/download_damodaran.py [--force]

Downloads to knowledge_base/damodaran/, skipping files that already exist
unless --force is passed.
"""
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEST_DIR = BASE_DIR / "knowledge_base" / "damodaran"

# All 244 URLs extracted from https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html
URLS = [
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capex.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/capexRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/countrystats.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/countrytaxrates.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctrypremJuly25.xlsx",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctrypremJune13.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfund.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/dbtfundRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetails.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/debtdetailsRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfe.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfcfeRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfund.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/divfundRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/Dollaremerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/DollarUS.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/Employee.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/Employeeemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EmployeeRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVA.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVAJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/EVARest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflows.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/finflowsRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEB.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/fundgrEBRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histretSP.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/inshold.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/insholdRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffect.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/leaseeffectRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/macro.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/margin.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/marginRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCap.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/mktcapmult.xlsx",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/MktCapRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/mktcaprisk.xlsx",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvar.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvaremerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/optvarRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvdata.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pbvRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/pedata.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/peRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psdata.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/psRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&D.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&Demerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/R&DRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roe.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/roeRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrate.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrateRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbeta.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/totalbetaRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitda.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/vebitdaRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wacc.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/waccRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdata.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataChina.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataemerg.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataEurope.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataGlobal.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataIndia.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataJapan.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/datasets/wcdataRest.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/macrodur.xls",
    "https://pages.stern.nyu.edu/~adamodar/pc/ratings.xls",
]


def download_all(force: bool = False) -> None:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    total = len(URLS)
    downloaded = 0
    skipped = 0
    failed = 0

    for i, url in enumerate(URLS, 1):
        filename = url.split("/")[-1]
        dest_path = DEST_DIR / filename

        if dest_path.exists() and not force:
            skipped += 1
            continue

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            dest_path.write_bytes(data)
            downloaded += 1
            print(f"[{i}/{total}] Downloaded: {filename} ({len(data):,} bytes)")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            failed += 1
            print(f"[{i}/{total}] FAILED: {filename} — {e}")

        # Be polite to the server
        if downloaded % 10 == 0 and downloaded > 0:
            time.sleep(1)

    print(f"\nDone. Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    download_all(force=force)
