from digiscore.types import DossierInput


def is_thin_file(d: DossierInput) -> bool:
    soldes = [c for c in d.historique.credits_passes if c.statut == "solde"]
    faible_activite = d.historique.epargne_moy_6m < 80000 and d.historique.nb_mouvements_90j < 3
    return d.membre.anciennete_mois < 3 or (len(soldes) == 0 and faible_activite)


def montant_par_rcsd(fin: dict, demande_duree: int) -> float:
    """Montant max tel que CAF / (charges_existantes + service) >= 1.5 approximé."""
    caf = fin["caf"]
    # service annuel max = CAF / 1.5
    service_max = max(0, caf / 1.5)
    # service ~ montant * 1.1 / duree * 12
    if demande_duree <= 0:
        return service_max
    return service_max * (demande_duree / 12) / 1.1


def compute_plafond(d: DossierInput, fin: dict, score: float, thin: bool) -> tuple[float, float | None]:
    base_epargne = d.historique.epargne_moy_6m * (4 if thin else 8)
    base_caf = max(0, fin["caf"] * 0.6)
    hist_bonus = 1.0
    soldes = [c for c in d.historique.credits_passes if c.statut == "solde" and c.nb_retards == 0]
    if soldes:
        hist_bonus = 1.15
    if any(c.statut == "impaye" for c in d.historique.credits_passes):
        hist_bonus = 0.35

    cap_rcsd = montant_par_rcsd(fin, d.demande.duree_mois)
    raw = min(d.demande.plafond_produit, (base_epargne + base_caf) * hist_bonus, cap_rcsd)
    if thin:
        raw = min(raw, max(50000, d.historique.epargne_moy_6m * 3), 250000)
    if score < 40:
        raw *= 0.4
    elif score < 71:
        raw *= 0.75

    eligible = max(0, round(raw / 10000) * 10000)
    suggestion = None
    if score >= 80 and not thin and eligible > d.demande.montant * 1.15:
        suggestion = min(d.demande.plafond_produit, round(eligible * 1.1 / 10000) * 10000)
    return eligible, suggestion
