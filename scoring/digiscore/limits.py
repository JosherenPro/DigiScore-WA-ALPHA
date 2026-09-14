from math import floor

from digiscore.financials import montant_pour_service
from digiscore.policy import RCSD_COMFORT_THRESHOLD, SCORE_ANALYSIS_MAX, SCORE_REJECTION_MAX
from digiscore.types import DossierInput


def is_thin_file(d: DossierInput) -> bool:
    soldes = [c for c in d.historique.credits_passes if c.statut == "solde"]
    faible_activite = d.historique.epargne_moy_6m < 80000 and d.historique.nb_mouvements_90j < 3
    return d.membre.anciennete_mois < 3 or (len(soldes) == 0 and faible_activite)


def montant_par_rcsd(fin: dict, demande_duree: int, service_dette_existant: float = 0) -> float:
    """Montant max respectant RCSD >= 1,50 après prise en compte des dettes en cours."""
    caf = fin["caf"]
    # CAF / (service existant + nouveau service) >= 1.5.
    service_max = max(0, caf / RCSD_COMFORT_THRESHOLD - service_dette_existant)
    return montant_pour_service(service_max, demande_duree)


def compute_plafond(d: DossierInput, fin: dict, score: float, thin: bool) -> tuple[float, float | None]:
    base_epargne = d.historique.epargne_moy_6m * (4 if thin else 8)
    base_caf = max(0, fin["caf"] * 0.6)
    hist_bonus = 1.0
    soldes = [c for c in d.historique.credits_passes if c.statut == "solde" and c.nb_retards == 0]
    if soldes:
        hist_bonus = 1.15
    if any(c.statut == "impaye" for c in d.historique.credits_passes):
        hist_bonus = 0.35

    cap_rcsd = montant_par_rcsd(
        fin,
        d.demande.duree_mois,
        d.analyse.charge_credits_en_cours,
    )
    raw = min(d.demande.plafond_produit, (base_epargne + base_caf) * hist_bonus, cap_rcsd)
    if thin:
        raw = min(raw, max(50000, d.historique.epargne_moy_6m * 3), 250000)
    if score <= SCORE_REJECTION_MAX:
        raw *= 0.4
    elif score <= SCORE_ANALYSIS_MAX:
        raw *= 0.75

    # Arrondir vers le bas évite de proposer un montant supérieur au plafond brut.
    eligible = max(0, floor(raw / 10000) * 10000)
    suggestion = None
    if score >= 80 and not thin and eligible > d.demande.montant * 1.15:
        suggestion = eligible
    return eligible, suggestion
