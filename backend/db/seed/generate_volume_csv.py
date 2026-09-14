#!/usr/bin/env python3
"""Jeu CSV SFD : 120k membres, histoires uniques, mix de cas. Pas de mobile money."""

from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta
from pathlib import Path

ANCHOR = date(2026, 9, 13)
SEED = 20260913

INSTITUTIONS = [
    ("IF-COOPEC-KPA", "coopec"),
    ("IF-COOPEC-SOK", "coopec"),
    ("IF-BTCI", "banque"),
    ("IF-UTB", "banque"),
    ("IF-WAGES", "microfinance"),
]

_FIRST_A = [
    "Ko", "Ya", "Ma", "Se", "Ed", "Ak", "Af", "Fi", "Am", "To", "Be", "Sa",
    "El", "Wi", "Jo", "Pa", "Li", "No", "Vi", "Ce", "Do", "Gu", "Ha", "Ire",
]
_FIRST_B = [
    "djo", "wa", "fi", "mi", "na", "ku", "si", "la", "vi", "no", "te", "ri",
    "me", "so", "ba", "de", "ko", "ya", "li", "tu", "pe", "ra", "fo", "ne",
]
_LAST_A = [
    "Men", "Kof", "Dos", "Agb", "Abl", "Tet", "Gbe", "Sow", "Amo", "Law",
    "Aka", "Adj", "Fol", "Sam", "Per", "Nay", "Bok", "Ame", "Kpa", "Gna",
    "Ats", "Yaw", "Eko", "Ses", "Tog", "Dag", "Zin", "Ocl", "Avi", "Hod",
]
_LAST_B = [
    "sah", "fi", "sou", "eko", "lam", "teh", "glo", "ani", "ussou", "son",
    "kpo", "ovi", "ivi", "aka", "rin", "oho", "me", "dome", "tcha", "ssin",
    "uvi", "aga", "ue", "bo", "be", "ban", "de", "oo", "lessi", "onou",
]
OCC = [
    "commercant", "commercante", "agriculteur", "agricultrice", "couturier",
    "menuisier", "moto-taxi", "grossiste", "transformatrice", "mareyeuse",
    "mecanicien", "coiffeuse", "tisserand", "eleveur",
]
CITIES = ["Lome", "Kpalime", "Sokode", "Kara", "Aneho", "Tsevie", "Atakpame", "Dapaong", "Bassar"]
STREETS = ["rue du Marche", "av. de la Paix", "rue des Cocotiers", "quartier Gbossime", "rue Nyekonakpoe"]
MVT_LABELS = ("Depot epargne", "Retrait caisse", "Interet compte", "Depot campagne", "Retrait urgence")


def unique_identity(i: int) -> tuple[str, str, str]:
    idx = i - 1
    n_first = len(_FIRST_A) * len(_FIRST_B)
    fi, li = idx % n_first, idx // n_first
    fa, fb = divmod(fi, len(_FIRST_B))
    la = li % len(_LAST_A)
    lb = li // len(_LAST_A)
    first = _FIRST_A[fa] + _FIRST_B[fb]
    last = _LAST_A[la] + _LAST_B[lb]
    gender = "F" if (fi + li) % 2 == 0 else "M"
    return first, last, gender


def unique_phone(i: int) -> str:
    return f"{90 + (i % 3)}{i:06d}"


def unique_birth(i: int) -> date:
    return date(1958, 1, 1) + timedelta(days=(i * 17) % 18_000)


def dstr(d: date) -> str:
    return d.isoformat()


def profile_of(i: int) -> str:
    b = i % 100
    if b < 7:
        return "thin"
    if b < 12:
        return "frozen"
    if b < 20:
        return "late"
    if b < 30:
        return "seasonal"
    if b < 70:
        return "ancien"
    return "standard"


def rng_for(i: int) -> random.Random:
    return random.Random(SEED * 1_000_003 + i)


def n_movements(profile: str, rng: random.Random, i: int) -> int:
    if profile == "thin":
        return 0 if i % 3 == 0 else rng.randint(1, 6)
    if profile == "frozen":
        return rng.randint(1, 4)
    if profile == "late":
        return rng.randint(10, 40)
    if profile == "seasonal":
        return rng.randint(12, 36)
    if profile == "ancien":
        return rng.randint(36, 180)
    return rng.randint(8, 36)


def has_external(profile: str, i: int) -> bool:
    if profile == "frozen":
        return False
    if profile == "thin":
        return i % 5 == 0
    return i % 10 in (0, 3, 7)


def joined(rng: random.Random, profile: str) -> date:
    if profile == "thin":
        return ANCHOR - timedelta(days=rng.randint(15, 80))
    if profile == "ancien":
        return ANCHOR - timedelta(days=rng.randint(2000, 4000))
    return ANCHOR - timedelta(days=rng.randint(200, 2500))


def mvt_row(i: int, k: int, opened: date, profile: str, rng: random.Random) -> tuple[date, str, int, str]:
    step = 7 + (i % 11) + (k % 5)
    day = opened + timedelta(days=k * step + (i % 13))
    if day > ANCHOR:
        day = ANCHOR - timedelta(days=1 + (k % 20))
    if profile == "late" and k % 4 == 0:
        typ = "retrait"
    elif k % 17 == 0:
        typ = "interet"
    else:
        typ = "depot" if (i + k) % 5 != 0 else "retrait"
    if profile == "seasonal" and (day.month in (6, 7, 8)):
        typ = "retrait"
    amt = 3000 + ((i * 7919 + k * 104729) % 220_000)
    if typ == "interet":
        amt = 200 + ((i + k * 97) % 8000)
    lab = f"{MVT_LABELS[(i + k) % len(MVT_LABELS)]} #{i}-{k}"
    return day, typ, amt, lab


def avgs_from_amounts(amounts: list[int]) -> tuple[int, int, int]:
    if not amounts:
        return 0, 0, 0
    a3 = int(sum(amounts[-3:]) / max(1, min(3, len(amounts))))
    a6 = int(sum(amounts[-6:]) / max(1, min(6, len(amounts))))
    a12 = int(sum(amounts[-12:]) / max(1, min(12, len(amounts))))
    return a3, a6, a12


def generate(out: Path, n: int, n_apps: int) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "member": out / "member.csv",
        "account": out / "account.csv",
        "snap": out / "savings_snapshot.csv",
        "mvt": out / "account_movement.csv",
        "credit": out / "past_credit.csv",
        "inc": out / "incident.csv",
        "gar": out / "member_guarantee.csv",
        "bic_c": out / "bic_consent.csv",
        "bic_r": out / "bic_report.csv",
        "map": out / "digiscore_member_map.csv",
        "ext_acc": out / "external_account.csv",
        "ext_mvt": out / "external_account_movement.csv",
        "ext_snap": out / "external_savings_snapshot.csv",
        "app": out / "credit_application.csv",
        "ie": out / "income_expense.csv",
        "wealth": out / "wealth.csv",
        "cash": out / "monthly_cashflow.csv",
        "act": out / "activity.csv",
        "hh": out / "household.csv",
        "ecom": out / "economic_model.csv",
        "mkt": out / "market.csv",
        "doc": out / "supporting_document.csv",
        "follow": out / "portfolio_followup.csv",
        "rec": out / "recovery_case.csv",
        "loan": out / "outstanding_loan.csv",
    }
    handles = {k: p.open("w", newline="", encoding="utf-8") for k, p in files.items()}
    w = {k: csv.writer(h) for k, h in handles.items()}

    w["member"].writerow(
        ["external_code", "last_name", "first_name", "gender", "birth_date", "phone", "address",
         "area", "agency_id", "joined_on", "status", "marital_status", "occupation"]
    )
    w["account"].writerow(["external_code", "account_no", "account_type", "opened_on", "status", "current_balance"])
    w["snap"].writerow(["account_no", "as_of", "avg_balance_3m", "avg_balance_6m", "avg_balance_12m"])
    w["mvt"].writerow(["account_no", "moved_on", "movement_type", "amount", "label"])
    w["credit"].writerow(
        ["external_code", "institution_code", "amount", "term_months", "granted_on", "closed_on",
         "status", "late_count", "max_days_late", "source"]
    )
    w["inc"].writerow(["external_code", "incident_type", "occurred_on", "severity", "detail"])
    w["gar"].writerow(["external_code", "kind", "value_amount"])
    w["bic_c"].writerow(["external_code", "signed_on", "status", "scan_path"])
    w["bic_r"].writerow(["external_code", "external_credit_count", "bic_incident_count", "indebtedness_summary", "source"])
    w["map"].writerow(["external_code", "source_system"])
    w["ext_acc"].writerow(["external_code", "institution_code", "account_no_mask", "opened_on", "status", "current_balance"])
    w["ext_mvt"].writerow(["account_no_mask", "moved_on", "movement_type", "amount", "label"])
    w["ext_snap"].writerow(["account_no_mask", "as_of", "avg_balance_3m", "avg_balance_6m", "avg_balance_12m"])
    w["app"].writerow(
        ["app_ref", "external_code", "product_id", "purpose", "requested_amount", "term_months",
         "status", "tax_status", "has_external_credits", "external_proofs_ok"]
    )
    w["ie"].writerow(
        ["app_ref", "revenue", "cogs", "operating_costs", "financial_income", "personal_income",
         "family_cost", "existing_debt_service", "equity", "total_debt", "total_assets",
         "current_assets", "current_liabilities", "avg_inventory", "net_income",
         "income_proof_level", "expense_proof_level"]
    )
    w["wealth"].writerow(
        ["app_ref", "productive_assets", "non_productive_assets", "formal_liabilities",
         "informal_liabilities", "signal_revenue_erosion", "signal_margin",
         "signal_receivables", "signal_payables", "signal_net_worth"]
    )
    w["cash"].writerow(["app_ref", "month_no", "period_month", "inflow", "outflow"])
    w["act"].writerow(["app_ref", "activity_type", "description", "seniority_months", "location_area", "is_seasonal", "proof_level"])
    w["hh"].writerow(["app_ref", "household_size", "housing", "dependents"])
    w["ecom"].writerow(["app_ref", "client_segments", "product_service", "avg_price", "unit_variable_cost", "monthly_fixed_cost", "sales_rhythm"])
    w["mkt"].writerow(["app_ref", "high_season", "low_season", "daily_volume", "competitor_count", "single_outlet_dependency", "proof_level"])
    w["doc"].writerow(["app_ref", "document_type", "file_path", "ocr_quality"])
    w["follow"].writerow(["external_code", "visit_code", "visit_on", "days_late", "signal"])
    w["rec"].writerow(["external_code", "level", "action", "owner_name", "opened_on"])
    w["loan"].writerow(
        ["external_code", "principal", "outstanding", "days_late", "status", "disbursed_on", "due_on", "observed_on"]
    )

    n_mvt = n_ext = n_cred = n_inc = n_app = 0
    app_codes: list[tuple[str, str, bool]] = []

    for i in range(1, n + 1):
        rng = rng_for(i)
        profile = profile_of(i)
        code = f"VOL-{i:07d}"
        first, last, gender = unique_identity(i)
        jd = joined(rng, profile)
        status = "gele" if profile == "frozen" else "actif"
        area = "rurale" if profile == "seasonal" or i % 5 == 0 else "urbaine"
        agency = 1 + (i % 2)
        city = CITIES[i % len(CITIES)]
        address = f"{1 + (i % 240)} {STREETS[i % len(STREETS)]}, {city}"
        w["member"].writerow([
            code, last, first, gender, dstr(unique_birth(i)), unique_phone(i),
            address, area, agency, dstr(jd), status,
            "mariee" if gender == "F" and i % 3 else ("marie" if gender == "M" and i % 3 else "celibataire"),
            OCC[i % len(OCC)],
        ])
        w["map"].writerow([code, "core_stub"])

        acc = f"CPTV-{code}"
        nm = n_movements(profile, rng, i)
        amounts: list[int] = []
        last_day = jd
        for k in range(nm):
            day, typ, amt, lab = mvt_row(i, k, jd, profile, rng)
            w["mvt"].writerow([acc, dstr(day), typ, amt, lab])
            amounts.append(amt if typ == "depot" else -amt)
            last_day = day
            n_mvt += 1
        bal = max(0, 15_000 + ((i * 4099) % 1_100_000) + sum(amounts) // 8)
        if profile in ("thin", "frozen"):
            bal = rng.randint(2000, 35_000)
        acc_status = "gele" if profile == "frozen" else "actif"
        w["account"].writerow([code, acc, "epargne", dstr(jd), acc_status, max(0, bal)])
        a3, a6, a12 = avgs_from_amounts([abs(x) for x in amounts] or [bal])
        w["snap"].writerow([acc, dstr(ANCHOR), a3, a6, a12])

        ext = has_external(profile, i)
        inst_code = INSTITUTIONS[(i * 3) % len(INSTITUTIONS)][0]
        if ext:
            mask = f"EXT-{inst_code[-3:]}-{i:07d}"
            opened_e = jd + timedelta(days=10 + (i % 40))
            if opened_e > ANCHOR:
                opened_e = jd
            n_em = rng.randint(12, 48)
            e_amts: list[int] = []
            ebal = 8000 + ((i * 11003) % 400_000)
            for k in range(n_em):
                day, typ, amt, lab = mvt_row(i + 9_000_000, k, opened_e, "standard", rng)
                w["ext_mvt"].writerow([mask, dstr(day), typ, amt, f"Ailleurs {lab}"])
                e_amts.append(amt)
                n_ext += 1
            w["ext_acc"].writerow([code, inst_code, mask, dstr(opened_e), "actif", ebal])
            ea3, ea6, ea12 = avgs_from_amounts(e_amts)
            w["ext_snap"].writerow([mask, dstr(ANCHOR), ea3, ea6, ea12])
            w["credit"].writerow([
                code, inst_code, 80_000 + ((i * 41) % 900_000), rng.choice([6, 10, 12]),
                dstr(opened_e), r"\N", "solde" if i % 2 else "en_cours",
                0, 0, "externe",
            ])
            n_cred += 1
            w["bic_c"].writerow([code, dstr(ANCHOR - timedelta(days=1 + i % 20)), "signe", f"seed/bic_{code}.pdf"])
            w["bic_r"].writerow([code, 1, 1 if profile == "late" else 0, f"Credit {inst_code} membre {i}", "simulate"])

        if profile not in ("thin", "frozen") and rng.random() < (0.85 if profile == "ancien" else 0.45):
            ncred = 1 if rng.random() < 0.7 else 2
            for cidx in range(ncred):
                amt = 80_000 + ((i * 37 + cidx * 13_000) % 1_400_000)
                granted = jd + timedelta(days=60 + cidx * 200 + (i % 90))
                if granted > ANCHOR:
                    granted = ANCHOR - timedelta(days=90 + cidx)
                st = "impaye" if profile == "late" and cidx == 0 else ("en_cours" if cidx == 0 and profile == "ancien" and i % 4 == 0 else "solde")
                closed = r"\N" if st != "solde" else dstr(min(ANCHOR, granted + timedelta(days=180 + (i % 120))))
                late = rng.randint(2, 6) if st == "impaye" else (rng.randint(0, 2) if profile != "ancien" else 0)
                w["credit"].writerow([code, r"\N", amt, rng.choice([6, 8, 10, 12]), dstr(granted), closed, st, late, late * 8, "interne"])
                n_cred += 1
                if st in ("en_cours", "impaye"):
                    days_late = late * 8 if st == "impaye" else 0
                    disb = granted
                    due = disb + timedelta(days=30 * 12)
                    w["loan"].writerow([code, amt, max(20_000, amt // 3), days_late, st, dstr(disb), dstr(due), dstr(ANCHOR)])

        if profile == "late":
            w["inc"].writerow([code, "retard", dstr(ANCHOR - timedelta(days=10 + i % 70)), "grave", f"Retard dossier {code}"])
            n_inc += 1
            w["follow"].writerow([code, rng.choice(["V1", "V2", "V3"]), dstr(ANCHOR - timedelta(days=1 + i % 40)), 15 + (i % 40), f"Signal {code}"])
            w["rec"].writerow([code, 1 + (i % 4), f"Relance {code}", f"Agent-{1 + i % 9}", dstr(ANCHOR - timedelta(days=20 + i % 10))])
        elif rng.random() < 0.02:
            w["inc"].writerow([code, "retard", dstr(ANCHOR - timedelta(days=20 + i % 180)), "moyenne", f"Retard leger {code}"])
            n_inc += 1

        if profile in ("ancien", "standard") and rng.random() < 0.28:
            w["gar"].writerow([code, rng.choice(["Stock", "Terrain", "Equipement", "Vehicule"]), 80_000 + ((i * 997) % 1_800_000)])

        if status == "actif" and n_app < n_apps and (profile in ("ancien", "standard", "seasonal", "late") or (profile == "thin" and ext)):
            n_app += 1
            app_codes.append((code, profile, ext))

        if i % 20000 == 0:
            print(f"  membres {i}/{n}")

    for j, (code, profile, ext) in enumerate(app_codes, start=1):
        rng = rng_for(10_000_000 + j)
        i_num = int(code.split("-")[1])
        ref = f"APP-{j:06d}"
        seasonal = profile == "seasonal"
        amt = 120_000 + ((j * 7919 + i_num) % 2_800_000)
        w["app"].writerow([
            ref, code, 2 if seasonal else 1,
            f"Fonds {code}" if not seasonal else f"Intrants {code}",
            amt, rng.choice([8, 10, 12]), "brouillon",
            rng.choice(["en_regle", "en_regle", "a_verifier", "non_fourni"]),
            ext, ext,
        ])
        ca = 400_000 + ((i_num * 8191) % 6_000_000)
        cmv = int(ca * (0.4 + (i_num % 20) / 100))
        charges = int(ca * (0.12 + (j % 10) / 100))
        w["ie"].writerow([
            ref, ca, cmv, charges, (i_num % 30) * 1000, 40_000 + (i_num % 200) * 1000,
            20_000 + (j % 70) * 1000, (i_num % 40) * 1000,
            int(ca * 0.2), int(ca * 0.08), int(ca * 0.45), int(ca * 0.18), int(ca * 0.1),
            int(cmv * 0.15), int(ca * 0.08), rng.choice(["N1", "N2", "N3"]), rng.choice(["N1", "N2"]),
        ])
        w["wealth"].writerow([ref, int(ca * 0.2), int(ca * 0.05), int(ca * 0.08), int(ca * 0.02), False, False, False, False, False])
        for m in range(1, 13):
            inn = 40_000 + ((i_num * m * 13) % 240_000)
            outflow = 30_000 + ((i_num * m * 17) % 180_000)
            if seasonal and m in (6, 7, 8):
                inn, outflow = 25_000 + (i_num % 20) * 1000, 160_000 + (j % 30) * 1000
            period = date(2025, m, 1)
            w["cash"].writerow([ref, m, dstr(period), inn, outflow])
        w["act"].writerow([ref, "agriculture" if seasonal else "commerce", f"Activite {code}", 8 + (i_num % 90), CITIES[i_num % len(CITIES)], seasonal, "N2"])
        w["hh"].writerow([ref, 2 + (i_num % 6), rng.choice(["locataire", "proprietaire"]), i_num % 5])
        w["ecom"].writerow([ref, "menages locaux", f"Offre {code}", 500 + (i_num % 8000), 200 + (j % 4000), 30_000 + (i_num % 50) * 1000, "hebdo"])
        w["mkt"].writerow([ref, "oct-dec", "juin-aout", 5 + (i_num % 40), 1 + (i_num % 8), i_num % 9 == 0, "N2"])
        w["doc"].writerow([ref, "CNI", f"seed/cni_{code}.jpg", "ok"])
        if ext:
            w["doc"].writerow([ref, "RELEVE", f"seed/releve_{code}.pdf", "ok"])

    for h in handles.values():
        h.close()

    _assert_unique(files["member"], files["account"], files["mvt"], files["ext_mvt"], files["ext_acc"])
    manifest = out / "MANIFEST.txt"
    sizes = [f"{p.name:32s} {p.stat().st_size / 1_048_576:8.2f} Mo" for p in sorted(out.glob("*.csv"))]
    manifest.write_text(
        f"Jeu volumetrique DigiScore-WA v2 (seed={SEED})\n"
        f"Membres: {n}\nDemandes: {len(app_codes)}\n"
        f"Mouvements agence ~ {n_mvt}\nMouvements ailleurs ~ {n_ext}\n"
        f"Credits ~ {n_cred}\nIncidents ~ {n_inc}\n\n"
        + "\n".join(sizes)
        + "\n",
        encoding="utf-8",
    )
    print(manifest.read_text())
    print(f"CSV ecrits dans {out.resolve()}")
    return files


def main() -> None:
    out = Path(os.getenv("VOLUME_DIR", "data/synthetic/volume"))
    n = int(os.getenv("VOLUME_MEMBERS", "120000"))
    n_apps = int(os.getenv("VOLUME_APPLICATIONS", "20000"))
    generate(out, n, n_apps)


def _assert_unique(members_p: Path, accounts_p: Path, mvt_p: Path, ext_mvt_p: Path, ext_acc_p: Path) -> None:
    codes, phones, names, accs = set(), set(), set(), set()
    with members_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert row["external_code"] not in codes, row["external_code"]
            assert row["phone"] not in phones, row["phone"]
            key = (row["last_name"], row["first_name"])
            assert key not in names, key
            blob = " ".join(row.values()).lower()
            assert "flooz" not in blob and "t-money" not in blob and "tmoney" not in blob
            codes.add(row["external_code"])
            phones.add(row["phone"])
            names.add(key)
    with accounts_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert row["account_no"] not in accs, row["account_no"]
            accs.add(row["account_no"])
    by_acc: dict[str, list[tuple[str, str, str, str]]] = {}
    with mvt_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            blob = (row.get("label") or "").lower()
            assert "flooz" not in blob and "t-money" not in blob
            by_acc.setdefault(row["account_no"], []).append(
                (row["moved_on"], row["movement_type"], row["amount"], row["label"])
            )
    series: set[tuple] = set()
    for acc, rows in by_acc.items():
        fp = tuple(rows)
        assert fp not in series, acc
        series.add(fp)
    ext_by: dict[str, list[tuple[str, str, str, str]]] = {}
    with ext_mvt_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            blob = (row.get("label") or "").lower()
            assert "flooz" not in blob and "t-money" not in blob
            ext_by.setdefault(row["account_no_mask"], []).append(
                (row["moved_on"], row["movement_type"], row["amount"], row["label"])
            )
    ext_series: set[tuple] = set()
    for mask, rows in ext_by.items():
        fp = tuple(rows)
        assert fp not in ext_series, mask
        ext_series.add(fp)
    if ext_acc_p.exists():
        with ext_acc_p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                kind_blob = row["institution_code"].lower()
                assert "flooz" not in kind_blob and "emoney" not in kind_blob and "wallet" not in kind_blob
    print(f"UNICITE OK : {len(codes)} membres, {len(series)} series agence, {len(ext_series)} series ailleurs")


if __name__ == "__main__":
    main()
