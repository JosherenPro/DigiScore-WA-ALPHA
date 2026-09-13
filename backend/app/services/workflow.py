def next_queue(zone: str, message_code: str, montant: float) -> str:
    if message_code == "VOIE_EXCEPTIONNELLE" or montant >= 8_000_000:
        return "cic"
    if zone == "analyse" or zone == "rejet":
        return "cic" if zone == "analyse" else "chef"
    return "chef"


def can_chef_close(zone: str, message_code: str, montant: float) -> bool:
    return zone == "approbation" and message_code != "VOIE_EXCEPTIONNELLE" and montant < 8_000_000
