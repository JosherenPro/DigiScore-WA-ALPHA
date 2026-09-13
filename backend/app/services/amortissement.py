def generer(montant: float, duree: int, taux_mensuel: float = 0.018) -> list[dict]:
    if duree <= 0:
        duree = 1
    restant = montant
    interet_total = montant * taux_mensuel * (duree / 12)
    echeance = round((montant + interet_total) / duree)
    rows = []
    for i in range(1, duree + 1):
        interet = round(restant * taux_mensuel / 12)
        capital = min(echeance - interet, restant)
        restant = max(0, restant - capital)
        rows.append(
            {
                "numero": i,
                "echeance": echeance,
                "capital": capital,
                "interet": interet,
                "restant": restant,
            }
        )
    return rows
