"""Unicité + mix de cas du générateur dense (pas de Postgres)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[1] / "db" / "seed"
sys.path.insert(0, str(SEED_DIR))

from generate_volume_csv import generate, has_external, profile_of  # noqa: E402


def test_volume_generator_unique_mix(tmp_path: Path):
    files = generate(tmp_path, n=300, n_apps=40)

    codes, phones, names = [], [], []
    with files["member"].open(encoding="utf-8") as f:
        members = list(csv.DictReader(f))
    assert len(members) == 300
    for row in members:
        codes.append(row["external_code"])
        phones.append(row["phone"])
        names.append((row["last_name"], row["first_name"]))
        blob = " ".join(row.values()).lower()
        assert "flooz" not in blob
        assert "t-money" not in blob
    assert len(set(codes)) == 300
    assert len(set(phones)) == 300
    assert len(set(names)) == 300

    mvt_by: dict[str, list[tuple]] = {}
    with files["mvt"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert "flooz" not in (row["label"] or "").lower()
            mvt_by.setdefault(row["account_no"], []).append(
                (row["moved_on"], row["movement_type"], row["amount"], row["label"])
            )
    fps = [tuple(rows) for rows in mvt_by.values()]
    assert len(fps) == len(set(fps))

    ext_by: dict[str, list[tuple]] = {}
    with files["ext_mvt"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert "flooz" not in (row["label"] or "").lower()
            ext_by.setdefault(row["account_no_mask"], []).append(
                (row["moved_on"], row["movement_type"], row["amount"], row["label"])
            )
    ext_fps = [tuple(rows) for rows in ext_by.values()]
    assert len(ext_fps) == len(set(ext_fps))

    with files["ext_acc"].open(encoding="utf-8") as f:
        ext_members = set()
        for row in csv.DictReader(f):
            ext_members.add(row["external_code"])
            assert not any(x in row["institution_code"].lower() for x in ("flooz", "emoney", "wallet"))

    acc_of = {}
    with files["account"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            acc_of[row["external_code"]] = row["account_no"]

    thin_zero = 0
    with_ext = 0
    without_ext = 0
    for i in range(1, 301):
        code = f"VOL-{i:07d}"
        profile = profile_of(i)
        acc = acc_of[code]
        got = len(mvt_by.get(acc, []))
        if profile == "thin":
            assert got <= 6
            if got == 0:
                thin_zero += 1
        elif profile == "frozen":
            assert 1 <= got <= 4
        elif profile == "ancien":
            assert 36 <= got <= 180
        elif profile == "late":
            assert 10 <= got <= 40
        elif profile == "seasonal":
            assert 12 <= got <= 36
        else:
            assert 8 <= got <= 36
        if has_external(profile, i):
            with_ext += 1
            assert code in ext_members
        else:
            without_ext += 1
            assert code not in ext_members

    assert thin_zero >= 1
    assert with_ext >= 1
    assert without_ext >= 1
    assert with_ext < 300
