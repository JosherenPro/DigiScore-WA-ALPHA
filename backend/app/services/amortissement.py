"""Tableau d'amortissement actuariel avec assurance (M5).

Conventions Excel (onglets Parametres / Simulations) :
  B7  taux nominal annuel (decimal, ex. 0.018) -> t = B7 / 12
  B8  taux d'assurance annuel (decimal, defaut 0.12 = 12 %)
  B11 mensualite hors assurance = K * t / (1 - (1 + t) ** -n)
  B12 cotisation assurance mensuelle = K * B8 / 12 (constante, assise sur le
      capital initial, pas sur le restant du)
  B13 mensualite totale = B11 + B12
  B14 cout total = B13 * n - K (ajuste sur les mensualites reelles arrondies)

Le scoring (RCSD, plafond) garde son taux simple 1,8 % : l'amortissement est
un affichage M5, pas une entree du moteur de regles.
"""

from __future__ import annotations

TAUX_ASSURANCE_DEFAUT = 0.12


def mensualite_hors_assurance(capital: float, duree: int, taux_annuel: float) -> int:
    """B11 arrondie au franc CFA."""
    if duree <= 0:
        duree = 1
    if capital <= 0:
        return 0
    t = max(0.0, taux_annuel) / 12.0
    if t <= 0:
        return round(capital / duree)
    return round(capital * t / (1.0 - (1.0 + t) ** (-duree)))


def cotisation_assurance(capital: float, taux_assurance: float = TAUX_ASSURANCE_DEFAUT) -> int:
    """B12 arrondie au franc CFA (constante sur toute la duree)."""
    if capital <= 0:
        return 0
    return round(capital * max(0.0, taux_assurance) / 12.0)


def generer(
    montant: float,
    duree: int,
    taux_annuel: float = 0.018,
    taux_assurance: float = TAUX_ASSURANCE_DEFAUT,
) -> dict:
    """Construit le tableau + le resume B11/B12/B13/B14.

    Le dernier mois est ajuste pour solder exactement le restant du.
    """
    if duree <= 0:
        duree = 1
    montant = max(0.0, float(montant))
    t = max(0.0, float(taux_annuel)) / 12.0
    echeance = mensualite_hors_assurance(montant, duree, taux_annuel)
    assurance = cotisation_assurance(montant, taux_assurance)

    lignes: list[dict] = []
    restant = montant
    for i in range(1, duree + 1):
        interet = round(restant * t) if restant > 0 else 0
        if i < duree:
            capital = min(echeance - interet, restant)
            echeance_i = echeance
        else:
            capital = restant
            echeance_i = capital + interet
        restant = max(0.0, restant - capital)
        lignes.append(
            {
                "numero": i,
                "echeance": echeance_i,
                "capital": capital,
                "interet": interet,
                "assurance": assurance,
                "echeance_totale": echeance_i + assurance,
                "restant": restant,
            }
        )

    total_paye = sum(l["echeance_totale"] for l in lignes)
    return {
        "lignes": lignes,
        "mensualite_hors_assurance": echeance,
        "assurance_mensuelle": assurance,
        "mensualite_totale": echeance + assurance,
        "cout_total": total_paye - montant,
    }
