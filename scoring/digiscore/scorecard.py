from digiscore.types import DossierInput

POIDS = {
    "financier": 0.25,
    "capacite": 0.20,
    "historique": 0.20,
    "activite": 0.15,
    "garanties": 0.10,
    "documents": 0.10,
}


def _clip(n: float) -> float:
    return max(0.0, min(100.0, n))


def note_financier(fin: dict) -> float:
    n = 50.0
    if fin["solvabilite"] >= 1:
        n += 15
    else:
        n -= 20
    if fin["fonds_roulement_pct"] >= 150:
        n += 15
    else:
        n -= 10
    if fin["participation_pct"] >= 35:
        n += 10
    if fin["marge_brute_pct"] >= 30:
        n += 10
    n -= fin["nb_ratios_degrades"] * 8
    return _clip(n)


def note_capacite(fin: dict) -> float:
    rcsd = fin["rcsd"]
    if rcsd < 1:
        n = 15.0
    elif rcsd < 1.5:
        n = 45.0
    elif rcsd < 2:
        n = 72.0
    else:
        n = 88.0
    if fin["mois_critique"] is not None:
        n -= 18
    if fin["nb_signaux"] >= 2:
        n -= 12
    return _clip(n)


def note_historique(d: DossierInput) -> float:
    h = d.historique
    n = 40.0
    soldes = [c for c in h.credits_passes if c.statut == "solde"]
    impayes = [c for c in h.credits_passes if c.statut == "impaye"]
    n += min(30, len(soldes) * 12)
    if any(c.nb_retards == 0 for c in soldes):
        n += 10
    if impayes:
        n -= 35
    graves = [i for i in h.incidents if i.gravite == "grave"]
    n -= len(graves) * 20
    if d.membre.anciennete_mois >= 36:
        n += 10
    elif d.membre.anciennete_mois < 3:
        n -= 15
    if h.epargne_moy_6m >= 300000:
        n += 10
    if h.credits_ailleurs and h.preuves_externes_ok:
        n += 8
    return _clip(n)


def note_activite(d: DossierInput) -> float:
    n = 65.0
    if d.analyse.saisonnier:
        n -= 10
    if d.analyse.dependance_debouche:
        n -= 12
    if d.analyse.patrimoine.signal_erosion_ca:
        n -= 10
    return _clip(n)


def note_garanties(d: DossierInput) -> float:
    couverture = 0.0
    if d.demande.montant > 0:
        couverture = d.analyse.valeur_garanties / d.demande.montant
    n = 30 + min(50, couverture * 50)
    if d.demande.montant >= d.demande.seuil_caution:
        if d.demande.nb_cautions_eligibles >= d.demande.nb_cautions_min:
            n += 15
        else:
            n -= 25
    return _clip(n)


def note_documents(d: DossierInput) -> float:
    n = 40.0
    for p in (d.analyse.preuve_revenu, d.analyse.preuve_charge):
        n += {"N3": 20, "N2": 12, "N1": 4}.get(p, 0)
    if d.demande.situation_fiscale == "en_regle":
        n += 12
    elif d.demande.situation_fiscale == "non_conforme":
        n -= 25
    if d.historique.credits_ailleurs and not d.historique.preuves_externes_ok:
        n -= 30
    return _clip(n)


def compute_score(d: DossierInput, fin: dict) -> tuple[float, list[dict]]:
    notes = {
        "financier": note_financier(fin),
        "capacite": note_capacite(fin),
        "historique": note_historique(d),
        "activite": note_activite(d),
        "garanties": note_garanties(d),
        "documents": note_documents(d),
    }
    criteres = []
    total = 0.0
    for code, poids in POIDS.items():
        note = notes[code]
        contrib = (note / 100) * poids * 100
        total += contrib
        criteres.append(
            {"code": code, "note": round(note, 1), "poids": poids, "contribution": round(contrib, 2)}
        )
    return round(total, 1), criteres
