from math import isclose

from digiscore.financials import caf, compute_all, ebe, rcsd, service_credit_sollicite
from digiscore.limits import montant_par_rcsd
from digiscore.types import AnalyseIn, DemandeIn


def test_caf_rcsd_ronds():
    a = AnalyseIn(
        ca=1000,
        cmv=400,
        charges_exploitation=200,
        produits_financiers=50,
        revenu_perso=100,
        charge_familiale=50,
        charge_credits_en_cours=0,
    )
    assert ebe(a) == 400
    assert caf(a) == 500
    d = DemandeIn(montant=0, duree_mois=12)
    # service sollicite 0 => RCSD eleve
    assert rcsd(a, d) > 1


def test_service_credit_et_rcsd_prennent_en_compte_la_dette_existante():
    a = AnalyseIn(
        ca=2_000,
        cmv=500,
        charges_exploitation=500,
        charge_credits_en_cours=200,
    )
    d = DemandeIn(montant=500, duree_mois=12)

    assert isclose(service_credit_sollicite(d), 509)
    assert isclose(rcsd(a, d), 1_000 / 709, rel_tol=1e-6)

    fin = compute_all(a, d)
    without_existing_debt = montant_par_rcsd(fin, 12)
    with_existing_debt = montant_par_rcsd(fin, 12, a.charge_credits_en_cours)
    assert with_existing_debt < without_existing_debt
    assert isclose(with_existing_debt, (1_000 / 1.5 - 200) / 1.1, rel_tol=1e-6)
