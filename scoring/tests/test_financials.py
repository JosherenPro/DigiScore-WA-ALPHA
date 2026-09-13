from digiscore.financials import caf, ebe, rcsd
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
