#!/usr/bin/env python3
"""Genere un jeu CSV SFD realiste : 120k membres + historiques (hors docker init)."""

from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(os.getenv("VOLUME_DIR", "data/synthetic/volume"))
N = int(os.getenv("VOLUME_MEMBERS", "120000"))
N_APPS = int(os.getenv("VOLUME_APPLICATIONS", "8000"))
ANCHOR = date(2026, 9, 13)
SEED = 20260913

# Syllabes pour 120k identites distinctes (pas 24 noms recopies).
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


def unique_identity(i: int) -> tuple[str, str, str]:
    """i=1..N → (first, last, gender). Couple prenom+nom unique (bijection sur i)."""
    idx = i - 1
    n_first = len(_FIRST_A) * len(_FIRST_B)
    fi, li = idx % n_first, idx // n_first
    fa, fb = divmod(fi, len(_FIRST_B))
    # li unique → (la, lb) unique (pas de wrap sur LAST_A)
    la = li % len(_LAST_A)
    lb = li // len(_LAST_A)
    first = _FIRST_A[fa] + _FIRST_B[fb]
    last = _LAST_A[la] + _LAST_B[lb]
    gender = "F" if (fi + li) % 2 == 0 else "M"
    return first, last, gender


def unique_phone(i: int) -> str:
    """8 chiffres uniques, style mobile TG (90/91/92 + 6 digits)."""
    return f"{90 + (i % 3)}{i:06d}"


def unique_birth(i: int) -> date:
    return date(1958, 1, 1) + timedelta(days=(i * 17) % 18_000)


def dstr(d: date) -> str:
    return d.isoformat()


def joined(rng: random.Random, profile: str) -> date:
    if profile == "thin":
        return ANCHOR - timedelta(days=rng.randint(15, 80))
    if profile == "ancien":
        return ANCHOR - timedelta(days=rng.randint(2000, 4000))
    return ANCHOR - timedelta(days=rng.randint(200, 2500))


def main() -> None:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    members_p = OUT / "member.csv"
    accounts_p = OUT / "account.csv"
    snap_p = OUT / "savings_snapshot.csv"
    mvt_p = OUT / "account_movement.csv"
    credit_p = OUT / "past_credit.csv"
    inc_p = OUT / "incident.csv"
    gar_p = OUT / "member_guarantee.csv"
    bic_c_p = OUT / "bic_consent.csv"
    bic_r_p = OUT / "bic_report.csv"
    app_p = OUT / "credit_application.csv"
    ie_p = OUT / "income_expense.csv"
    wealth_p = OUT / "wealth.csv"
    cash_p = OUT / "monthly_cashflow.csv"
    act_p = OUT / "activity.csv"
    hh_p = OUT / "household.csv"
    follow_p = OUT / "portfolio_followup.csv"
    rec_p = OUT / "recovery_case.csv"
    loan_p = OUT / "outstanding_loan.csv"
    map_p = OUT / "digiscore_member_map.csv"

    fm = members_p.open("w", newline="", encoding="utf-8")
    fa = accounts_p.open("w", newline="", encoding="utf-8")
    fs = snap_p.open("w", newline="", encoding="utf-8")
    fv = mvt_p.open("w", newline="", encoding="utf-8")
    fc = credit_p.open("w", newline="", encoding="utf-8")
    fi = inc_p.open("w", newline="", encoding="utf-8")
    fg = gar_p.open("w", newline="", encoding="utf-8")
    fbc = bic_c_p.open("w", newline="", encoding="utf-8")
    fbr = bic_r_p.open("w", newline="", encoding="utf-8")
    fmap = map_p.open("w", newline="", encoding="utf-8")

    wm = csv.writer(fm)
    wa = csv.writer(fa)
    ws = csv.writer(fs)
    wv = csv.writer(fv)
    wc = csv.writer(fc)
    wi = csv.writer(fi)
    wg = csv.writer(fg)
    wbc = csv.writer(fbc)
    wbr = csv.writer(fbr)
    wmap = csv.writer(fmap)

    wm.writerow(["external_code", "last_name", "first_name", "gender", "birth_date", "phone", "address", "area", "agency_id", "joined_on", "status", "marital_status", "occupation"])
    wa.writerow(["external_code", "account_no", "account_type", "opened_on", "status", "current_balance"])
    ws.writerow(["account_no", "avg_balance_3m", "avg_balance_6m", "avg_balance_12m"])
    wv.writerow(["account_no", "moved_on", "movement_type", "amount", "label"])
    wc.writerow(["external_code", "amount", "term_months", "granted_on", "closed_on", "status", "late_count", "max_days_late", "source"])
    wi.writerow(["external_code", "incident_type", "occurred_on", "severity", "detail"])
    wg.writerow(["external_code", "kind", "value_amount"])
    wbc.writerow(["external_code", "signed_on", "status", "scan_path"])
    wbr.writerow(["external_code", "external_credit_count", "bic_incident_count", "indebtedness_summary", "source"])
    wmap.writerow(["external_code", "source_system"])

    app_codes: list[str] = []
    n_mvt = n_cred = n_inc = 0

    for i in range(1, N + 1):
        roll = rng.random()
        if roll < 0.07:
            profile = "thin"
        elif roll < 0.12:
            profile = "frozen"
        elif roll < 0.20:
            profile = "late"
        elif roll < 0.30:
            profile = "seasonal"
        elif roll < 0.42:
            profile = "ancien"
        else:
            profile = "good"

        code = f"VOL-{i:07d}"
        first, last, gender = unique_identity(i)
        jd = joined(rng, profile)
        status = "gele" if profile == "frozen" else "actif"
        area = "rurale" if profile == "seasonal" or i % 5 == 0 else "urbaine"
        agency = 1 + (i % 2)
        city = CITIES[i % len(CITIES)]
        address = f"{1 + (i % 240)} {STREETS[i % len(STREETS)]}, {city}"
        wm.writerow([
            code, last, first, gender, dstr(unique_birth(i)), unique_phone(i),
            address, area, agency, dstr(jd), status,
            "mariee" if gender == "F" and i % 3 else ("marie" if gender == "M" and i % 3 else "celibataire"),
            OCC[i % len(OCC)],
        ])
        wmap.writerow([code, "core_stub"])

        acc = f"CPTV-{code}"
        bal = 8000 if profile in ("thin", "frozen") else rng.randint(40_000, 900_000)
        if profile == "good":
            bal = rng.randint(200_000, 1_200_000)
        acc_status = "gele" if profile == "frozen" else "actif"
        wa.writerow([code, acc, "epargne", dstr(jd), acc_status, bal])
        a3 = int(bal * rng.uniform(0.85, 1.05))
        a6 = int(bal * rng.uniform(0.75, 1.0))
        a12 = int(bal * rng.uniform(0.65, 0.95))
        ws.writerow([acc, a3, a6, a12])

        if profile != "frozen" and rng.random() < 0.78:
            months = 4 if profile == "thin" else rng.randint(6, 12)
            for k in range(months):
                day = ANCHOR.replace(day=1) - timedelta(days=30 * k)
                typ = "retrait" if (profile == "late" and k == 0) else "depot"
                amt = rng.randint(8_000, 25_000) if profile == "thin" else rng.randint(20_000, 120_000)
                wv.writerow([acc, dstr(day), typ, amt, "Epargne" if typ == "depot" else "Retrait"])
                n_mvt += 1

        if profile not in ("thin", "frozen") and rng.random() < 0.42:
            ncred = 1 if rng.random() < 0.7 else 2
            for cidx in range(ncred):
                amt = 80_000 + ((i * 37 + cidx * 13_000) % 1_400_000)
                granted = jd + timedelta(days=rng.randint(60, 800))
                if granted > ANCHOR:
                    granted = ANCHOR - timedelta(days=90)
                st = "impaye" if profile == "late" and cidx == 0 else rng.choice(["solde", "solde", "en_cours"])
                closed = r"\N" if st != "solde" else dstr(granted + timedelta(days=365))
                late = rng.randint(2, 6) if st == "impaye" else (rng.randint(0, 2) if profile != "good" else 0)
                wc.writerow([code, amt, rng.choice([6, 8, 10, 12]), dstr(granted), closed, st, late, late * 8, "interne"])
                n_cred += 1

        if profile == "late" and rng.random() < 0.65:
            wi.writerow([code, "retard", dstr(ANCHOR - timedelta(days=rng.randint(10, 80))), "grave", "Retard promesse"])
            n_inc += 1
        elif rng.random() < 0.03:
            wi.writerow([code, "retard", dstr(ANCHOR - timedelta(days=rng.randint(20, 200))), "moyenne", "Retard leger"])
            n_inc += 1

        if profile in ("good", "ancien") and rng.random() < 0.28:
            wg.writerow([code, rng.choice(["Stock", "Terrain", "Equipement", "Vehicule"]), rng.randint(80_000, 2_000_000)])

        if rng.random() < 0.32:
            wbc.writerow([code, dstr(ANCHOR - timedelta(days=rng.randint(1, 40))), "signe", f"seed/bic_{code}.pdf"])
        if rng.random() < 0.14:
            wbr.writerow([code, rng.randint(0, 2), 1 if profile == "late" else 0, "Synthese BIC simulee", "simulate"])

        if i <= N_APPS and status == "actif":
            app_codes.append(code)

        if i % 20000 == 0:
            print(f"  membres {i}/{N}")

    fm.close()
    fa.close()
    fs.close()
    fv.close()
    fc.close()
    fi.close()
    fg.close()
    fbc.close()
    fbr.close()
    fmap.close()

    fapp = app_p.open("w", newline="", encoding="utf-8")
    fie = ie_p.open("w", newline="", encoding="utf-8")
    fw = wealth_p.open("w", newline="", encoding="utf-8")
    fcash = cash_p.open("w", newline="", encoding="utf-8")
    fact = act_p.open("w", newline="", encoding="utf-8")
    fhh = hh_p.open("w", newline="", encoding="utf-8")
    wapp = csv.writer(fapp)
    wie = csv.writer(fie)
    ww = csv.writer(fw)
    wcash = csv.writer(fcash)
    wact = csv.writer(fact)
    whh = csv.writer(fhh)
    wapp.writerow(["app_ref", "external_code", "product_id", "purpose", "requested_amount", "term_months", "status", "tax_status", "has_external_credits", "external_proofs_ok"])
    wie.writerow(["app_ref", "revenue", "cogs", "operating_costs", "financial_income", "personal_income", "family_cost", "existing_debt_service", "equity", "total_debt", "total_assets", "current_assets", "current_liabilities", "avg_inventory", "net_income", "income_proof_level", "expense_proof_level"])
    ww.writerow(["app_ref", "productive_assets", "non_productive_assets", "formal_liabilities", "informal_liabilities", "signal_revenue_erosion", "signal_margin", "signal_receivables", "signal_payables", "signal_net_worth"])
    wcash.writerow(["app_ref", "month_no", "inflow", "outflow"])
    wact.writerow(["app_ref", "activity_type", "description", "seniority_months", "location_area", "is_seasonal", "proof_level"])
    whh.writerow(["app_ref", "household_size", "housing", "dependents"])

    for j, code in enumerate(app_codes, start=1):
        ref = f"APP-{j:06d}"
        seasonal = j % 11 == 0
        amt = 120_000 + ((j * 7919) % 2_800_000)
        wapp.writerow([
            ref, code, 2 if seasonal else 1,
            "Fonds de roulement" if not seasonal else "Intrants campagne",
            amt, rng.choice([8, 10, 12]), "brouillon",
            rng.choice(["en_regle", "en_regle", "a_verifier", "non_fourni"]),
            rng.random() < 0.12, rng.random() < 0.08,
        ])
        ca = rng.randint(800_000, 6_000_000)
        cmv = int(ca * rng.uniform(0.4, 0.65))
        charges = int(ca * rng.uniform(0.12, 0.22))
        wie.writerow([
            ref, ca, cmv, charges, rng.randint(0, 30_000), rng.randint(40_000, 250_000),
            rng.randint(20_000, 90_000), rng.randint(0, 40_000),
            int(ca * 0.2), int(ca * 0.08), int(ca * 0.45), int(ca * 0.18), int(ca * 0.1),
            int(cmv * 0.15), int(ca * 0.08), rng.choice(["N1", "N2", "N3"]), rng.choice(["N1", "N2"]),
        ])
        ww.writerow([ref, int(ca * 0.2), int(ca * 0.05), int(ca * 0.08), int(ca * 0.02), False, False, False, False, False])
        for m in range(1, 13):
            inn = 40_000 if seasonal and m in (6, 7, 8) else rng.randint(120_000, 280_000)
            out = 180_000 if seasonal and m in (6, 7, 8) else rng.randint(90_000, 200_000)
            wcash.writerow([ref, m, inn, out])
        wact.writerow([ref, "agriculture" if seasonal else "commerce", rng.choice(CITIES), rng.randint(8, 96), rng.choice(CITIES), seasonal, "N2"])
        whh.writerow([ref, rng.randint(2, 7), rng.choice(["locataire", "proprietaire"]), rng.randint(0, 4)])

    fapp.close()
    fie.close()
    fw.close()
    fcash.close()
    fact.close()
    fhh.close()

    with follow_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["external_code", "visit_code", "visit_on", "days_late", "signal"])
        for i in range(1, 3001):
            w.writerow([f"VOL-{i:07d}", rng.choice(["V1", "V2", "V3"]), dstr(ANCHOR - timedelta(days=rng.randint(1, 60))), rng.choice([0, 0, 5, 15, 45]), rng.choice(["Absence aux visites", "Baisse de stock", "Retard echeance", ""])])

    with rec_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["external_code", "level", "action", "owner_name", "opened_on"])
        for i in range(1, 1501):
            w.writerow([f"VOL-{i:07d}", rng.randint(1, 4), "Relance telephonique", "Koffi Chef", dstr(ANCHOR - timedelta(days=20))])

    with loan_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["external_code", "principal", "outstanding", "days_late", "status"])
        for i in range(50, 5050):
            w.writerow([f"VOL-{i:07d}", rng.randint(150_000, 800_000), rng.randint(40_000, 400_000), rng.choice([0, 0, 0, 12, 40]), rng.choice(["en_cours", "en_cours", "impaye"])])

    manifest = OUT / "MANIFEST.txt"
    sizes = []
    for p in sorted(OUT.glob("*.csv")):
        sizes.append(f"{p.name:28s} {p.stat().st_size / 1_048_576:8.2f} Mo")
    manifest.write_text(
        f"Jeu volumetrique DigiScore-WA (seed={SEED})\n"
        f"Membres: {N}\nDemandes: {len(app_codes)}\n"
        f"Mouvements ~ {n_mvt}\nCredits passes ~ {n_cred}\nIncidents ~ {n_inc}\n\n"
        + "\n".join(sizes)
        + "\n",
        encoding="utf-8",
    )
    _assert_unique(members_p, accounts_p)
    print(manifest.read_text())
    print(f"CSV ecrits dans {OUT.resolve()}")


def _assert_unique(members_p: Path, accounts_p: Path) -> None:
    codes, phones, names, accs = set(), set(), set(), set()
    with members_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert row["external_code"] not in codes, row["external_code"]
            assert row["phone"] not in phones, row["phone"]
            key = (row["last_name"], row["first_name"])
            assert key not in names, key
            codes.add(row["external_code"])
            phones.add(row["phone"])
            names.add(key)
    with accounts_p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert row["account_no"] not in accs, row["account_no"]
            accs.add(row["account_no"])
    assert len(codes) == len(phones) == len(names) == len(accs)
    print(f"UNICITE OK : {len(codes)} membres, 0 doublon code/tel/nom/compte")


if __name__ == "__main__":
    main()
