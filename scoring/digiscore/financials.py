from digiscore.types import AnalyseIn, DemandeIn


def ebe(a: AnalyseIn) -> float:
    return a.ca - a.cmv - a.charges_exploitation


def surplus_personnel(a: AnalyseIn) -> float:
    return a.revenu_perso - a.charge_familiale


def caf(a: AnalyseIn) -> float:
    return ebe(a) + a.produits_financiers + surplus_personnel(a)


def service_credit_sollicite(demande: DemandeIn) -> float:
    if demande.duree_mois <= 0:
        return demande.montant
    interet = demande.montant * 0.018 * (demande.duree_mois / 12)
    return (demande.montant + interet) * (12 / demande.duree_mois)


def rcsd(a: AnalyseIn, demande: DemandeIn) -> float:
    service = a.charge_credits_en_cours + service_credit_sollicite(demande)
    if service <= 0:
        return 99.0
    return caf(a) / service


def ratios(a: AnalyseIn) -> dict[str, float]:
    ca = a.ca or 1
    marge = ((a.ca - a.cmv) / ca) * 100
    bn = (a.resultat_net / ca) * 100
    solv = a.fonds_propres / a.total_dettes if a.total_dettes else 99.0
    rot = (a.stock_moyen * 365 / a.cmv) if a.cmv else 0
    part = (a.fonds_propres / a.actif_total * 100) if a.actif_total else 0
    fr = (a.actif_circulant / a.passif_circulant * 100) if a.passif_circulant else 0
    return {
        "marge_brute_pct": round(marge, 2),
        "benefice_net_pct": round(bn, 2),
        "solvabilite": round(solv, 3),
        "rotation_stocks_jours": round(rot, 1),
        "participation_pct": round(part, 2),
        "fonds_roulement_pct": round(fr, 2),
    }


def nb_ratios_degrades(r: dict[str, float]) -> int:
    n = 0
    if r["solvabilite"] < 1:
        n += 1
    if r["participation_pct"] < 35:
        n += 1
    if r["fonds_roulement_pct"] < 150:
        n += 1
    if r["benefice_net_pct"] < 0:
        n += 1
    return n


def tresorerie_mois_critique(a: AnalyseIn) -> int | None:
    cumul = 0.0
    for row in sorted(a.tresorerie, key=lambda x: x.mois):
        cumul += row.flux_entrant - row.flux_sortant
        if cumul < 0:
            return row.mois
    return None


def situation_nette(a: AnalyseIn) -> float:
    p = a.patrimoine
    return (
        p.actifs_productifs
        + p.actifs_non_productifs
        - p.passifs_formels
        - p.passifs_informels
    )


def nb_signaux_patrimoine(a: AnalyseIn) -> int:
    p = a.patrimoine
    return sum(
        [
            p.signal_erosion_ca,
            p.signal_marge,
            p.signal_creances,
            p.signal_fournisseurs,
            p.signal_nette,
        ]
    )


def compute_all(a: AnalyseIn, demande: DemandeIn) -> dict:
    r = ratios(a)
    return {
        "ebe": round(ebe(a), 2),
        "caf": round(caf(a), 2),
        "rcsd": round(rcsd(a, demande), 3),
        **r,
        "nb_ratios_degrades": nb_ratios_degrades(r),
        "mois_critique": tresorerie_mois_critique(a),
        "situation_nette": round(situation_nette(a), 2),
        "nb_signaux": nb_signaux_patrimoine(a),
    }
