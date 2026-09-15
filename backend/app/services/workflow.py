def next_queue(zone: str, message_code: str, montant: float) -> str:
    """A qui l'agent soumet le dossier.

    Toujours au chef d'agence : l'agent ne saisit jamais le CIC directement,
    meme pour un montant exceptionnel (VOIE_EXCEPTIONNELLE / >= 8M) — c'est le
    chef qui decide d'escalader (avis "escalader", voir /decision) apres avoir
    vu le dossier. `message_code` et `montant` restent dans la signature pour
    ne pas casser les appelants ; le routage ne depend plus que d'un seul
    niveau, mais can_chef_close() empeche toujours le chef de valider seul un
    dossier exceptionnel/eleve (voir plus bas) — il doit alors escalader.
    """
    del zone, message_code, montant
    return "chef"


def can_chef_close(zone: str, message_code: str, montant: float) -> bool:
    return zone == "approbation" and message_code != "VOIE_EXCEPTIONNELLE" and montant < 8_000_000
