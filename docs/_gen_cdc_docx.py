# -*- coding: utf-8 -*-
"""Régénère les 2 CDC DigiScore-WA (complet + livrable soir) — version à jour plan."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

OUT = Path("/home/aemtechnology/digiscore_wa/docs")
RES = Path("/home/aemtechnology/digiscore_wa/resoure")
NAVY = RGBColor(0x0B, 0x3D, 0x5C)
ACCENT = RGBColor(0x1A, 0x6B, 0x5C)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x4A, 0x4A, 0x4A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

def set_run_font(run, name="Calibri", size=11, bold=False, italic=False, color=DARK):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color

def shade_cell(cell, hex_color):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), hex_color)
    shading.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading)

def add_hline(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "1A6B5C")
    pBdr.append(bottom)
    pPr.append(pBdr)

def setup(doc):
    n = doc.styles["Normal"]
    n.font.name = "Calibri"
    n.font.size = Pt(11)
    n.font.color.rgb = DARK
    n.paragraph_format.space_after = Pt(6)
    n.paragraph_format.line_spacing = 1.12
    for sn, sz, col in [("Heading 1", 15, NAVY), ("Heading 2", 12, ACCENT), ("Heading 3", 11, NAVY)]:
        s = doc.styles[sn]
        s.font.name = "Calibri"
        s.font.size = Pt(sz)
        s.font.bold = True
        s.font.color.rgb = col
        s.paragraph_format.space_before = Pt(12 if "1" in sn else 10)
        s.paragraph_format.space_after = Pt(4)

def para(doc, text, bold=False, italic=False, size=11, center=False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold, italic=italic)
    return p

def bullet(doc, text, size=10):
    p = doc.add_paragraph(style="List Bullet")
    p.clear()
    set_run_font(p.add_run(text), size=size)

def numbered(doc, text, size=10):
    p = doc.add_paragraph(style="List Number")
    p.clear()
    set_run_font(p.add_run(text), size=size)

def callout(doc, label, text):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    shade_cell(c, "E8F5F1")
    p = c.paragraphs[0]
    set_run_font(p.add_run(label + " "), size=10, bold=True, color=ACCENT)
    set_run_font(p.add_run(text), size=10)
    doc.add_paragraph()

def table(doc, headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        shade_cell(cell, "0B3D5C")
        set_run_font(cell.paragraphs[0].add_run(h), size=9, bold=True, color=WHITE)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.rows[ri + 1].cells[ci]
            if ri % 2:
                shade_cell(cell, "F4F8FA")
            set_run_font(cell.paragraphs[0].add_run(str(val)), size=9)
    doc.add_paragraph()

def footer(doc, text):
    fp = doc.sections[0].footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(fp.add_run(text), size=8, color=GRAY)

def margins(doc, t=1.6, b=1.6, l=1.8, r=1.8):
    s = doc.sections[0]
    s.top_margin = Cm(t)
    s.bottom_margin = Cm(b)
    s.left_margin = Cm(l)
    s.right_margin = Cm(r)

def save_both(doc, name):
    p1 = OUT / name
    p2 = RES / name
    doc.save(p1)
    doc.save(p2)
    return p1, p2

# ═══════════════════════════════════════════════════════════
# COMPLET
# ═══════════════════════════════════════════════════════════

def build_complet():
    doc = Document()
    setup(doc)
    margins(doc, 2, 2, 2.2, 2.2)
    footer(doc, "DigiScore-WA · Cahier des charges complet · Équipe Alpha · CIF DigiCoop-WA+ · Sept. 2026")

    para(doc, "DIGICOOP-WA+  ·  CIF  ·  HACKATHON NATIONAL", bold=True, size=10, center=True)
    para(doc, "Équipe Alpha  ·  Thématique 02 — Scoring microcrédit  ·  Track A", size=9, center=True)
    add_hline(doc)
    para(doc, "DigiScore-WA", bold=True, size=28, center=True)
    para(doc, "Cahier des charges complet", bold=True, size=16, center=True)
    para(doc, "Spécification fonctionnelle, technique et organisationnelle — version actualisée", italic=True, size=11, center=True)
    para(doc, "Cible : institutions membres de la CIF  ·  Échantillon d'existant : FUCEC-Togo", size=10, center=True)
    para(doc, "Score /100 (seuils 40 / 70)  ·  Lomé · Septembre 2026", size=10, center=True)
    add_hline(doc)
    para(doc, "Copilote d'éligibilité et de plafond de microcrédit — Agent → Chef d'agence → CIC", italic=True, size=10, center=True)
    doc.add_page_break()

    doc.add_heading("Sommaire", 1)
    for i, t in enumerate([
        "Contexte et problématique",
        "Étude de l'existant (échantillon SFD) et besoin CIF",
        "Solution proposée",
        "Différenciation et innovations",
        "Modèle de décision, formules et score /100",
        "Workflows Agent → Chef d'agence → CIC",
        "Architecture technique et intégrabilité SI",
        "Modèle de données (BDD)",
        "Modules et périmètre IN / OUT 72 h",
        "Organisation, ressources, conformité",
    ], 1):
        para(doc, f"{i}.  {t}", size=11)
    doc.add_page_break()

    # 1
    doc.add_heading("1. Contexte et problématique", 1)
    para(doc, "Le programme DigiCoop-WA+ de la CIF organise des hackathons nationaux. La Thématique 02 vise le scoring microcrédit adapté aux SFD d'Afrique de l'Ouest.")
    para(doc, "L'analyse s'appuie sur un échantillon terrain (pratiques type FUCEC-Togo). DigiScore-WA est conçu pour l'ensemble des institutions du réseau CIF, pas une seule faîtière.", italic=True, size=10)
    para(doc, "Constats :", bold=True)
    bullet(doc, "Instruction manuelle longue (~3 h/dossier) et hétérogène entre agences.")
    bullet(doc, "Impayés observés (~8 %) ; risque dès J+1.")
    bullet(doc, "Le demandeur doit ouvrir un compte ; l'historique institutionnel existe souvent mais est sous-exploité comme moteur d'éligibilité/plafond.")
    bullet(doc, "Cas sans historique interne : crédits ailleurs à prouver par pièces ; cautionnaires au-delà d'un seuil ; contrôles BIC / fiscalité.")
    callout(doc, "Problématique :",
            "Comment objectiver éligibilité et plafond à partir du comportement du membre (interne ou preuves externes), sans remplacer la décision humaine, de façon déployable chez les SFD CIF ?")

    # 2
    doc.add_heading("2. Étude de l'existant et besoin", 1)
    doc.add_heading("2.1 Cycle crédit observé (9 composantes)", 2)
    table(doc, ["#", "Composante", "Ancrage"], [
        ["1", "Collecte", "Questionnaire A–E, preuves N1/N2/N3"],
        ["2", "Analyse économique", "Modèle 6 Q, marché 12 Q, risques"],
        ["3", "Analyse financière", "CAF, RCSD, 6 ratios, trésorerie, patrimoine"],
        ["4", "Gestion des risques", "4 familles, matrice P×I"],
        ["5", "Documents d'octroi", "Pièces, BIC, fiscalité"],
        ["6", "Décision", "Scorecard, mémo, comité"],
        ["7", "Amortissement", "Montant / durée / échéancier"],
        ["8", "Suivi portefeuille", "V1–V3, 12 signaux, PAR"],
        ["9", "Recouvrement", "4 niveaux"],
    ])
    doc.add_heading("2.2 Précisions terrain récentes", 2)
    bullet(doc, "Compte membre préalable ; historique interne prioritaire.")
    bullet(doc, "Sans historique interne : ouverture de compte + questionnaire crédits ailleurs + upload relevés/carnets ; refus si preuves exigibles absentes.")
    bullet(doc, "BIC + situation fiscale « en règle ».")
    bullet(doc, "Au-delà d'un seuil de montant : cautionnaires évalués (capacité de relais des échéances).")
    bullet(doc, "SI : sidecar obligatoire ; ADD-only ; APIs/passerelles en pilote ; perf >1 M clients.")

    # 3
    doc.add_heading("3. Solution proposée", 1)
    para(doc, "DigiScore-WA (WA = West Africa) est un copilote — pas un robot d'octroi. Il produit : score /100 explicable, montant éligible (plafond), message métier type crédit télécom, mémo, puis validation humaine.")
    table(doc, ["Module", "Contenu", "72 h"], [
        ["M1 Collecte", "Wizard A–E + N1–N3 + upload pièces", "Fonctionnel"],
        ["M2 Analyse", "CAF, RCSD, 6 ratios, trésorerie, patrimoine", "Fonctionnel"],
        ["M3 Score & plafond", "6 critères /100 + messages + cautions/BIC", "Fonctionnel"],
        ["M4 Mémo", "Mémo + fiche comité", "Fonctionnel"],
        ["M5 Décision", "Agent → Chef → CIC + amortissement", "Fonctionnel"],
        ["M6 / M7", "Suivi PAR & recouvrement", "Maquette"],
    ])

    # 4
    doc.add_heading("4. Différenciation et innovations", 1)
    numbered(doc, "Éligibilité type crédit télécom : plafond + messages explicites.")
    numbered(doc, "Historique membre + voie preuves externes (OCR / qualité photo) si pas d'historique interne.")
    numbered(doc, "BIC / fiscalité + cautionnaires scorés au-delà d'un seuil.")
    numbered(doc, "Gouvernance Agent → Chef d'agence → CIC avec audit.")
    numbered(doc, "ML explicable optionnel (contributions, anomalies, simulateur de résilience) — le ML éclaire, l'humain décide.")
    numbered(doc, "Sidecar intégrable : mapping champs, adapters, tables digiscore_* ADD-only.")
    callout(doc, "Pitch :",
            "« DigiScore-WA, c'est le crédit mobile appliqué aux institutions CIF : éligibilité et plafond depuis l'historique (ou preuves externes), score /100, cautions et BIC, décision humaine — sans toucher au transactionnel. »")

    # 5
    doc.add_heading("5. Modèle de décision, formules et score /100", 1)
    callout(doc, "Décision encadreurs :", "Score sur 100 (pas 1000). Seuils 40 / 70 — simples pour agents et CIC.")

    doc.add_heading("5.1 Formules financières", 2)
    para(doc, "EBE = CA − CMV − Charges_exploitation", size=10)
    para(doc, "CAF = EBE + Produits_financiers + (Revenus_perso − Charges_familiales)", size=10)
    para(doc, "RCSD = CAF / (Dettes_en_cours + Service_credit_sollicité)", size=10)
    table(doc, ["Règle RCSD", "Valeur"], [
        ["Norme confort", "≥ 150 % (1,50)"],
        ["Knock-out", "< 1,00 → bloque reco auto"],
    ])
    table(doc, ["Ratio", "Formule", "Seuil"], [
        ["Marge brute", "(Marge_brute/CA)×100", "Sectoriel"],
        ["BN/CA", "(RN/CA)×100", "Sectoriel"],
        ["Solvabilité", "FP / Total dettes", "> 1"],
        ["Rotation stocks", "(Stock_moy×365)/CAMV", "Sectoriel"],
        ["Participation", "(FP consol./Actif)×100", "> 35 %"],
        ["Fonds de roulement", "Actif circ./Passif circ.", "> 150 %"],
    ])
    para(doc, "Trésorerie : Solde_mensuel = entrées − sorties ; cumul ≥ 0 chaque mois. Patrimoine : Situation nette = Actifs − Passifs ; 5 signaux d'alerte (érosion CA, marge, créances, dettes fournisseurs, nette en baisse).", size=10)

    doc.add_heading("5.2 Score /100", 2)
    para(doc, "score = Σ (note_i/100) × poids_i × 100", size=10)
    table(doc, ["Critère", "Poids"], [
        ["Analyse financière", "25 %"],
        ["Capacité de remboursement", "20 %"],
        ["Historique de remboursement", "20 %"],
        ["Risque d'activité", "15 %"],
        ["Garanties (+ qualité cautions)", "10 %"],
        ["Qualité documentaire (+ BIC/fiscal)", "10 %"],
    ])
    table(doc, ["Score", "Zone", "Recommandation"], [
        ["0 – 40", "Risque élevé", "Rejet recommandé"],
        ["41 – 70", "Risque moyen", "Analyse / CIC"],
        ["71 – 100", "Risque faible", "Approbation recommandée"],
    ])
    para(doc, "Knock-outs : RCSD < 1 · ESG · incohérence critique · incidents graves · BIC/fiscal exigible manquant · seuil caution sans cautionnaire éligible.", size=10)

    doc.add_heading("5.3 Plafond, BIC, cautions", 2)
    bullet(doc, "montant_eligible = min(plafond produit, f(épargne, CAF, RCSD, score, hist, garanties+cautions), capacité échéance).")
    bullet(doc, "BIC + situation fiscale en_regle / a_verifier / non_conforme / non_fourni.")
    bullet(doc, "Si montant ≥ seuil_caution → évaluation cautionnaire (peut-il payer à la place ?).")

    # 6
    doc.add_heading("6. Workflows acteurs", 1)
    table(doc, ["Rôle", "Action"], [
        ["Agent de crédit", "Compte/membre, saisie, score/plafond, mémo, soumission"],
        ["Chef d'agence", "Valider / refuser / renvoyer / envoyer CIC (motif si ≠ reco)"],
        ["CIC", "Accorder / conditionner / refuser (zone grise & gros montants)"],
    ])
    table(doc, ["Score", "Suite"], [
        ["< 40 ou knockout", "Rejet reco ; override → CIC"],
        ["41–70", "CIC obligatoire"],
        ["> 70 et montant OK", "Validation chef simplifiée (humaine)"],
        ["Voie exceptionnelle", "CIC + cautions"],
    ])

    # 7
    doc.add_heading("7. Architecture et intégrabilité SI", 1)
    table(doc, ["Couche", "Choix"], [
        ["Front", "React PWA (TypeScript)"],
        ["Back", "FastAPI"],
        ["Moteur", "scoring/ règles + ML explicable optionnel"],
        ["BDD", "PostgreSQL + Docker"],
    ])
    para(doc, "Preuve d'intégrabilité : sidecar (pas de greffe transactionnelle) ; mapping de champs ; adapters stub→API pilote ; tables digiscore_* ADD-only ; agence_id ; index pour >1 M clients.", size=10)
    table(doc, ["Étape", "Livrable intégration"], [
        ["Conception H0", "Sidecar + schéma + mapping + interface Adapter"],
        ["Dev 72 h", "AdapterStub + mêmes API qu'en pilote"],
        ["Pilote", "Adapter réel + CREATE digiscore_* + atelier DSI"],
    ])

    # 8
    doc.add_heading("8. Modèle de données (synthèse)", 1)
    bullet(doc, "Cœur : membre, compte, mouvements, crédits passés, incidents, produits (seuil_caution).")
    bullet(doc, "BIC/fiscal : consentement_bic, rapport_bic, piece_justificative, situation_fiscale.")
    bullet(doc, "Cautions : cautionnaire, demande_caution, evaluation_cautionnaire.")
    bullet(doc, "Demande : collecte A–E, ratio_financier, score_resultat, décision 3 niveaux, audit.")
    bullet(doc, "Vision : suivi_portefeuille, par, recouvrement.")

    # 9
    doc.add_heading("9. Périmètre IN / OUT 72 h", 1)
    table(doc, ["IN", "OUT / vision"], [
        ["M1–M5 + score/100 + plafond + 3 rôles", "Connecteurs core banking / BIC / mobile money live"],
        ["Upload pièces + qualité photo (+ OCR démo)", "OCR production robuste"],
        ["Cautions + flags BIC/fiscal (seed)", "API BIC réelle"],
        ["Maquettes M6/M7", "Moteurs suivi/recouvrement live"],
        ["Adapters stub", "Multi-tenant / SSO / i18n éwé"],
    ])

    # 10
    doc.add_heading("10. Organisation, ressources, conformité", 1)
    table(doc, ["Rôle équipe", "Dossier"], [
        ["Data", "backend/db/, data/synthetic/"],
        ["Scoring", "scoring/"],
        ["Backend", "backend/app/"],
        ["Frontend", "frontend/"],
    ])
    table(doc, ["Ressource démo", "Min", "Reco"], [
        ["CPU", "2 vCPU", "4"],
        ["RAM", "4 Go", "8 Go"],
        ["Disque", "10 Go", "20 Go"],
    ])
    bullet(doc, "Données synthétiques uniquement ; audit des overrides ; amortissement ≤ capacité.")
    add_hline(doc)
    para(doc, "Fin du cahier des charges complet — DigiScore-WA · Équipe Alpha · CIF DigiCoop-WA+", italic=True, size=9, center=True)
    return save_both(doc, "DigiScore-WA_Cahier_des_charges_COMPLET.docx")

# ═══════════════════════════════════════════════════════════
# SOIR 5 MIN
# ═══════════════════════════════════════════════════════════

def build_soir():
    doc = Document()
    setup(doc)
    margins(doc)
    footer(doc, "DigiScore-WA · Livrable soir J1 · Problème · Idée · Architecture · Équipe Alpha")

    para(doc, "DIGICOOP-WA+  ·  CIF  ·  HACKATHON NATIONAL", bold=True, size=9, center=True)
    para(doc, "Équipe Alpha  ·  Thématique 02 — Scoring microcrédit", size=9, center=True)
    add_hline(doc)
    para(doc, "DigiScore-WA", bold=True, size=24, center=True)
    para(doc, "Livrable du soir — 5 minutes", bold=True, size=14, center=True)
    para(doc, "Problème  ·  Idée  ·  Architecture", italic=True, size=12, center=True)
    para(doc, "Institutions CIF  ·  Score /100  ·  Lomé 2026", size=9, center=True)
    add_hline(doc)

    doc.add_heading("Déroulement (5 min)", 1)
    table(doc, ["Temps", "Bloc", "Focus"], [
        ["0:00–1:00", "Problème", "Besoin commun SFD CIF"],
        ["1:00–3:30", "Idée", "Impacts, innovations, modèle /100"],
        ["3:30–5:00", "Architecture", "Stack, sidecar, scope 72 h"],
    ])

    doc.add_heading("1. Le problème", 1)
    para(doc, "Dans les institutions CIF, l'évaluation du microcrédit reste souvent manuelle, lente et inégale, alors que le risque commence dès J+1.")
    para(doc, "Méthode : FUCEC-Togo = échantillon d'existant. La solution vise toutes les institutions CIF.", italic=True, size=9)
    bullet(doc, "~3 h pour instruire un dossier ; ~8 % d'impayés (ordres de grandeur).")
    bullet(doc, "Le membre a (ou doit ouvrir) un compte : l'historique existe mais sert peu de moteur d'éligibilité/plafond.")
    bullet(doc, "Cas sans historique local, BIC/fiscalité, cautionnaires au-delà d'un seuil : encore très papier.")
    callout(doc, "Question :",
            "Comment objectiver éligibilité et plafond sans remplacer l'humain, de façon intégrable aux SI CIF ?")

    doc.add_heading("2. L'idée — DigiScore-WA", 1)
    para(doc, "Copilote d'octroi : historique membre (ou preuves externes) + formulaire → score /100 + plafond + message type crédit mobile → Agent → Chef d'agence → CIC.")

    doc.add_heading("2.1 Impacts", 2)
    table(doc, ["Impact", "Effet"], [
        ["Temps", "Cible pédagogique ~3 h → ~45 min"],
        ["Risque", "Détection plus précoce (cible ~8 % → ~5 %, à valider en pilote)"],
        ["Homogénéité", "Même grille / messages entre agences"],
        ["Gouvernance", "Chaîne 3 niveaux + audit des overrides"],
        ["Protection client", "Plafond et échéances bornés par la capacité"],
        ["Déploiement", "Pas de greffe sur le cœur transactionnel"],
    ])

    doc.add_heading("2.2 Innovations", 2)
    numbered(doc, "Plafond + messages type crédit télécom (pas seulement oui/non).")
    numbered(doc, "Voie sans historique interne : questionnaire + upload pièces ; refus si preuves absentes.")
    numbered(doc, "BIC / fiscalité + cautionnaires évalués (relais d'échéances) au-delà d'un seuil.")
    numbered(doc, "Score /100 (demande encadreurs) — seuils 40 / 70, simples à expliquer.")
    numbered(doc, "ML explicable optionnel ; règle d'or : le ML éclaire, l'humain décide.")
    numbered(doc, "Sidecar + mapping + adapters : intégrable en pilote sans refaire le moteur.")

    doc.add_heading("2.3 Modèle de décision (essentiel)", 2)
    para(doc, "Règles : CAF, RCSD (≥150 %, knockout <1), 6 ratios, trésorerie, patrimoine → score /100 (6 critères).", size=10)
    table(doc, ["Score", "Reco", "Humain"], [
        ["0–40", "Rejet", "Chef / CIC si override"],
        ["41–70", "Analyse", "CIC obligatoire"],
        ["71–100", "Approbation reco", "Chef (toujours humain)"],
    ])
    para(doc, "ML optionnel : contributions, anomalies, simulateur de résilience — jamais dans les knock-outs ni la décision finale.", size=9)
    callout(doc, "Phrase :",
            "« Le crédit mobile appliqué aux institutions CIF : éligibilité et plafond, score /100, cautions/BIC, décision Agent→Chef→CIC, sans toucher au transactionnel. »")

    doc.add_heading("3. L'architecture", 1)
    para(doc, "PWA (3 rôles) → FastAPI → moteur score & plafond → PostgreSQL → mémo / files / audit.", size=10)
    table(doc, ["Couche", "Choix"], [
        ["Front", "React PWA"],
        ["Back", "FastAPI"],
        ["Décision", "Règles + hooks ML optionnels"],
        ["Données", "PostgreSQL + seeds synthétiques"],
    ])
    bullet(doc, "Sidecar : lecture API/passerelle ; écriture digiscore_* ADD-only.")
    bullet(doc, "Hackathon = AdapterStub ; pilote = même API + adapter réel.")
    table(doc, ["IN 72 h", "OUT"], [
        ["M1–M5, score/100, 3 rôles, upload pièces", "Connecteurs live BIC/core banking"],
        ["Cautions + flags BIC/fiscal (seed)", "OCR/API production"],
        ["Maquettes M6/M7", "Multi-tenant / SSO"],
    ])
    para(doc, "Ressources démo : 2–4 vCPU · 4–8 Go RAM · Docker.", size=9)
    add_hline(doc)
    callout(doc, "Clôture :",
            "DigiScore-WA — copilote d'éligibilité et de plafond pour les institutions CIF, score /100, gouverné par l'humain, déployable à côté du SI.")
    para(doc, "Prêts pour les questions des mentors.", italic=True, size=10, center=True)
    return save_both(doc, "DigiScore-WA_Livrable_Soir_Probleme_Idee_Architecture.docx")

if __name__ == "__main__":
    a, b = build_complet()
    c, d = build_soir()
    print("COMPLET", a)
    print("COMPLET", b)
    print("SOIR", c)
    print("SOIR", d)
