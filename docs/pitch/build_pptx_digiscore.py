"""Génère le pitch DigiScore-WA — style repris de build_pptx.py (16:9, teal/or, cartes).

Source : docs du monorepo alpha (CDC, PITCH_DIFFERENCIATION, GUIDE_EQUIPE) + logos CIF / FUCEC / Togo.
Public : jury Hackathon CIF DigiCoop-WA+ (Lomé, septembre 2026).

Structure (7 temps demandés) : 1. Problème et contexte · 2. Solution · 3. Architecture de la base
de données (schéma graphique) · 4. Impact · 5. L'équipe · 6. Suite · 7. Mot de fin.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "DigiScore-WA_Pitch.pptx"

# Logos (fucec.webp -> png pour python-pptx)
CIF_LOGO = ROOT / "cif.png"
TOGO_LOGO = ROOT / "togo.png"
FUCEC_LOGO = ROOT / "fucec.png"
if not FUCEC_LOGO.exists() and (ROOT / "fucec.webp").exists():
    Image.open(ROOT / "fucec.webp").convert("RGBA").save(FUCEC_LOGO)
LOGOS = [p for p in (CIF_LOGO, FUCEC_LOGO, TOGO_LOGO) if p.exists()]

# Palette institutionnelle (échantillonnée sur les logos CIF / FUCEC / Togo)
TEAL = RGBColor(0x1F, 0x7A, 0x33)        # vert principal assombri
TEAL_DARK = RGBColor(0x0F, 0x40, 0x22)   # vert profond (fonds)
GOLD = RGBColor(0xF2, 0xC0, 0x10)        # jaune Togo / CIF
TURQ = RGBColor(0x2E, 0x9E, 0x50)        # vert secondaire
ORANGE = RGBColor(0xC0, 0x8A, 0x00)      # or foncé (texte sur blanc)
PURP = RGBColor(0x16, 0x66, 0x2E)        # vert profond
GREEN = RGBColor(0x16, 0x66, 0x2E)
RED = RGBColor(0xC8, 0x10, 0x2E)         # rouge Togo / FUCEC
INK = RGBColor(0x17, 0x3A, 0x2A)         # encre vert sombre
MUTED = RGBColor(0x5F, 0x7A, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF2, 0xF8, 0xF3)
BORDER = RGBColor(0xD6, 0xE7, 0xDA)
SOFT_TEAL = RGBColor(0xE7, 0xF4, 0xEA)
SOFT_GOLD = RGBColor(0xFF, 0xF7, 0xD6)
SOFT_ORG = RGBColor(0xFC, 0xF3, 0xDC)
SOFT_PURP = RGBColor(0xE8, 0xF5, 0xEE)
SOFT_RED = RGBColor(0xFB, 0xE9, 0xEC)
FUCEC_GREEN = RGBColor(0x16, 0x66, 0x2E)  # vert FUCEC (accent)
FUCEC_RED = RGBColor(0xE0, 0x20, 0x30)    # rouge FUCEC (accent)
FUCEC_GREEN_LIGHT = RGBColor(0x6F, 0xD4, 0x8F)  # vert FUCEC clair (fonds sombres)

FONT = "Poppins"
TOTAL = 9

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


def remove_shadow(shape):
    style = shape._element.find(qn("p:style"))
    if style is not None:
        effect_ref = style.find(qn("a:effectRef"))
        if effect_ref is not None:
            style.remove(effect_ref)


def add_slide(bg=WHITE):
    slide = prs.slides.add_slide(BLANK)
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = bg
    bg_shape.line.fill.background()
    bg_shape.shadow.inherit = False
    return slide


def add_rect(slide, x, y, w, h, fill, border=None, border_w=0.6, rounded=False):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        x, y, w, h,
    )
    if rounded:
        shape.adjustments[0] = 0.08
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
        shape.line.width = Pt(border_w)
    shape.shadow.inherit = False
    remove_shadow(shape)
    return shape


def add_card(slide, x, y, w, h, fill=WHITE, border=BORDER):
    return add_rect(slide, x, y, w, h, fill, border=border, rounded=True)


def add_text(slide, x, y, w, h, text, *, size=14, bold=False, color=INK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = Pt(4)
    frame.margin_top = frame.margin_bottom = Pt(4)
    lines = text.split("\n") if isinstance(text, str) else text
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        run = paragraph.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def add_rich_bullets(slide, x, y, w, h, items, *, size=11.5,
                     color=INK, accent=TEAL, bullet="▸", line_spacing=1.1):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Pt(2)
    frame.margin_top = frame.margin_bottom = Pt(2)
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = PP_ALIGN.LEFT
        paragraph.line_spacing = line_spacing
        paragraph.space_after = Pt(4)
        run = paragraph.add_run()
        run.text = f"{bullet} "
        run.font.size = Pt(size)
        run.font.color.rgb = accent
        run.font.bold = True
        run.font.name = FONT
        if isinstance(item, tuple):
            head, tail = item
            run = paragraph.add_run()
            run.text = f"{head} "
            run.font.size = Pt(size)
            run.font.color.rgb = TEAL
            run.font.bold = True
            run.font.name = FONT
            run = paragraph.add_run()
            run.text = tail
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.name = FONT
        else:
            run = paragraph.add_run()
            run.text = item
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.name = FONT
    return box


def add_picture_fit(slide, path, x, y, max_w, max_h):
    """Insère une image centrée dans la boîte (x, y, max_w, max_h), ratio conservé."""
    with Image.open(path) as im:
        ratio = im.width / im.height
    w, h = max_w, max_w / ratio
    if h > max_h:
        h, w = max_h, max_h * ratio
    left = x + int((max_w - w) / 2)
    top = y + int((max_h - h) / 2)
    return slide.shapes.add_picture(str(path), left, top, width=int(w), height=int(h))


def logo_strip(slide, x, y, w, h, card=True):
    """Bandeau blanc arrondi avec les trois logos, centrés."""
    if card:
        add_card(slide, x, y, w, h, fill=WHITE, border=BORDER)
    inner_y = y + int(h * 0.14)
    inner_h = int(h * 0.72)
    gap = Inches(0.10)
    sizes = []
    for path in LOGOS:
        with Image.open(path) as im:
            ratio = im.width / im.height
        sizes.append(inner_h * ratio)
    total = sum(sizes) + gap * (len(LOGOS) - 1)
    cursor = x + int((w - total) / 2)
    for path, iw in zip(LOGOS, sizes):
        slide.shapes.add_picture(str(path), int(cursor), inner_y, width=int(iw), height=int(inner_h))
        cursor += iw + gap


def section_header(slide, section, title, subtitle=None, logos=True):
    add_rect(slide, 0, 0, SW, Inches(1.20), TEAL)
    add_rect(slide, 0, Inches(1.20), SW, Pt(3.5), GOLD)
    add_rect(slide, 0, Inches(1.249), SW, Pt(1.8), FUCEC_RED)
    add_rect(slide, Inches(0.5), Inches(0.28), Inches(0.15), Inches(0.32), GOLD)
    add_text(slide, Inches(0.75), Inches(0.24), Inches(9.6), Inches(0.35),
             section.upper(), size=11, bold=True, color=GOLD)
    add_text(slide, Inches(0.5), Inches(0.52), Inches(10.4), Inches(0.6),
             title, size=21, bold=True, color=WHITE)
    if logos:
        logo_strip(slide, Inches(11.35), Inches(0.20), Inches(1.68), Inches(0.80))
    if subtitle:
        add_text(slide, Inches(0.5), Inches(1.36), Inches(12.3), Inches(0.32),
                 subtitle, size=11.5, color=MUTED)


def footer(slide, page_num, source="Équipe Alpha · CIF DigiCoop-WA+"):
    add_rect(slide, Inches(0.5), Inches(7.12), Inches(12.333), Pt(0.6), BORDER)
    add_text(slide, Inches(0.5), Inches(7.18), Inches(9.2), Inches(0.28),
             "DIGISCORE-WA · COPILOTE D'ÉLIGIBILITÉ ET DE PLAFOND DE CRÉDIT",
             size=8.5, color=MUTED)
    add_text(slide, Inches(9.0), Inches(7.18), Inches(2.8), Inches(0.28),
             source, size=8.2, color=MUTED, align=PP_ALIGN.RIGHT)
    add_text(slide, Inches(12.0), Inches(7.18), Inches(0.85), Inches(0.28),
             f"{page_num:02d} / {TOTAL:02d}", size=9, bold=True, color=MUTED,
             align=PP_ALIGN.RIGHT)


def kpi_card(slide, x, y, w, h, value, label, sublabel, color=TEAL):
    add_card(slide, x, y, w, h, fill=WHITE, border=color)
    add_rect(slide, x, y, w, Inches(0.06), color)
    box = slide.shapes.add_textbox(x, y + Inches(0.05), w, h - Inches(0.06))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = frame.margin_right = Pt(2)
    frame.margin_top = frame.margin_bottom = Pt(0)
    for index, (text, size, bold, c) in enumerate([
        (value, 14, True, color),
        (label, 9.5, True, INK),
        (sublabel, 8, False, MUTED),
    ]):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = PP_ALIGN.CENTER
        paragraph.space_after = Pt(1)
        run = paragraph.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = c
        run.font.name = FONT


def numbered_badge(slide, number, x, y, color=TEAL):
    add_rect(slide, x, y, Inches(0.45), Inches(0.45), color, rounded=True)
    add_text(slide, x, y + Inches(0.02), Inches(0.45), Inches(0.36), str(number),
             size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)


def arrow(slide, x, y, w, h, color=GOLD):
    add_rect(slide, x, y, w, h, color, rounded=True)


def hbar(slide, x, y, w, h, pct, fill, bg=LIGHT):
    add_rect(slide, x, y, w, h, bg, rounded=True)
    add_rect(slide, x, y, w * max(0.0, min(1.0, pct)), h, fill, rounded=True)


def add_notes(slide, text):
    notes_slide = slide.notes_slide
    notes_slide.placeholders[1].text = text


# ============================================================
# 1 — COUVERTURE
# ============================================================
s = add_slide(bg=TEAL)
add_rect(s, 0, 0, Inches(0.4), SH, GOLD)
add_rect(s, Inches(0.40), 0, Inches(0.07), SH, FUCEC_GREEN)
add_rect(s, Inches(0.47), 0, Inches(0.07), SH, FUCEC_RED)
add_text(s, Inches(0.8), Inches(0.45), Inches(11.5), Inches(0.35),
         "CIF DIGICOOP-WA+ · THÉMATIQUE 02 — SCORING MICROCRÉDIT · LOMÉ, SEPTEMBRE 2026",
         size=12, bold=True, color=GOLD)
add_text(s, Inches(0.8), Inches(0.95), Inches(11.8), Inches(1.05),
         "DigiScore-WA", size=46, bold=True, color=WHITE)
add_text(s, Inches(0.8), Inches(2.08), Inches(11.5), Inches(0.45),
         "Le copilote d'éligibilité et de plafond de crédit des SFD",
         size=19, bold=True, color=SOFT_TEAL)
add_text(s, Inches(0.8), Inches(2.60), Inches(11.5), Inches(0.35),
         "Score /100 · plafond type crédit télécom · BIC/fiscal · décision humaine Agent → Chef → CIC",
         size=12.5, color=WHITE)

cover_kpis = [
    ("/100", "Score explicable", "6 critères pondérés", FUCEC_GREEN_LIGHT),
    ("6", "Zones & KO", "0–40 · 41–70 · 71–100", GOLD),
    ("3", "Rôles humains", "Agent → Chef → CIC", ORANGE),
    ("< 1", "RCSD knockout", "≥ 1,5 confort", FUCEC_RED),
]
for index, (value, label, sublabel, color) in enumerate(cover_kpis):
    x = Inches(0.8 + index * 3.0)
    add_rect(s, x, Inches(3.15), Inches(2.8), Inches(1.45), TEAL_DARK,
             border=color, border_w=1.2, rounded=True)
    add_text(s, x, Inches(3.28), Inches(2.8), Inches(0.45), value,
             size=22, bold=True, color=color, align=PP_ALIGN.CENTER)
    add_text(s, x, Inches(3.82), Inches(2.8), Inches(0.32), label,
             size=10.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(s, x, Inches(4.15), Inches(2.8), Inches(0.28), sublabel,
             size=9, color=SOFT_TEAL, align=PP_ALIGN.CENTER)

for index, path in enumerate(LOGOS):
    x = Inches(0.8 + index * 2.6)
    add_card(s, x, Inches(5.05), Inches(2.3), Inches(1.05), fill=WHITE, border=BORDER)
    add_picture_fit(s, path, x + Inches(0.15), Inches(5.15), Inches(2.0), Inches(0.85))

add_text(s, Inches(8.6), Inches(5.35), Inches(3.9), Inches(0.45),
         "FUCEC-Togo = échantillon d'existant\nCible : institutions membres de la CIF",
         size=10.5, bold=True, color=SOFT_TEAL, align=PP_ALIGN.RIGHT)
add_text(s, Inches(0.8), Inches(6.35), Inches(11.7), Inches(0.30),
         "Pitch 8 min + 2 min Q&R · démo live obligatoire · données 100 % synthétiques · sidecar ADD-only",
         size=10, color=WHITE, align=PP_ALIGN.CENTER)
add_notes(s,
    "COUVERTURE — DigiScore-WA, équipe Alpha, thématique 02 scoring microcrédit, CIF DigiCoop-WA+ à Lomé. "
    "Pitch 8 minutes chronométré + 2 minutes de questions, démo live obligatoire. Ne pas dépasser 7 min 30. "
    "Phrase d'ouverture : « Les SFD évaluent encore le risque à la main, 3 h par dossier, alors que l'historique "
    "du membre existe déjà. Nous en faisons un score /100 et un plafond, sans jamais remplacer la décision humaine. »")


# ============================================================
# 2 — SOMMAIRE (7 TEMPS)
# ============================================================
s = add_slide()
section_header(s, "Feuille de route", "Notre pitch en 7 temps — 8 minutes chrono",
               "Minutage conseillé par le guide CIF : problème 1 min · solution + démo 4 min · impact 1 min 30 · équipe/suite 1 min.")
sections = [
    ("1", "Problème et contexte", "3 h par dossier · 8 % d'impayés · tout papier", TEAL, "0:00 – 1:00"),
    ("2", "Solution", "Score /100 · plafond · Agent → Chef → CIC", TURQ, "1:00 – 5:00"),
    ("3", "Architecture BDD", "Sidecar ADD-only · 2 cahiers", GREEN, "zoom 30 s"),
    ("4", "Impact", "45 min par dossier · décision tracée", ORANGE, "5:00 – 6:30"),
    ("5", "L'équipe", "Quatre métiers, un moteur", PURP, "6:30 – 7:00"),
    ("6", "Suite", "Pilote FUCEC · M6/M7 · ML réel", TURQ, "7:00 – 7:30"),
    ("7", "Mot de fin", "L'humain décide", GOLD, "7:30 – 8:00"),
]
for i, (num, title, detail, color, timing) in enumerate(sections):
    col = i % 4
    row = i // 4
    x = Inches(0.5 + col * 3.13)
    y = Inches(2.05 + row * 2.30)
    add_card(s, x, y, Inches(2.95), Inches(2.00), fill=WHITE, border=color)
    add_rect(s, x, y, Inches(2.95), Inches(0.12), color)
    numbered_badge(s, num, x + Inches(0.22), y + Inches(0.32), color)
    add_text(s, x + Inches(0.80), y + Inches(0.30), Inches(2.00), Inches(0.40), title,
             size=12, bold=True, color=TEAL)
    add_text(s, x + Inches(0.80), y + Inches(0.82), Inches(2.00), Inches(0.80), detail,
             size=9.5, color=INK)
    add_text(s, x + Inches(0.22), y + Inches(1.62), Inches(2.60), Inches(0.28), timing,
             size=8.5, bold=True, color=color, align=PP_ALIGN.RIGHT)
add_notes(s,
    "SOMMAIRE — Sept temps : problème, solution, architecture, impact, équipe, suite, mot de fin. Démo : MEM-001 "
    "bon payeur, MEM-004 thin-file KO, MEM-009 voie exceptionnelle CIC, MEM-010 compte gelé. "
    "Pitch 8 min chronométré + 2 min de questions, démo live obligatoire.")
footer(s, 2)


# ============================================================
# 3 — 1. PROBLÈME ET CONTEXTE
# ============================================================
s = add_slide()
section_header(s, "1 · Problème et contexte", "Instruire un microcrédit reste manuel, lent et hétérogène",
               "Contexte CIF : l'historique du membre existe mais n'est pas exploité comme moteur d'éligibilité.")
kpi_card(s, Inches(0.5), Inches(1.95), Inches(2.95), Inches(1.25), "~ 3 h", "Par dossier", "Instruction manuelle", TEAL)
kpi_card(s, Inches(3.65), Inches(1.95), Inches(2.95), Inches(1.25), "~ 8 %", "Impayés", "Retard dès J+1", RED)
kpi_card(s, Inches(6.80), Inches(1.95), Inches(2.95), Inches(1.25), "100 %", "BIC / fiscal papier", "Cautions peu évaluées", ORANGE)
kpi_card(s, Inches(9.95), Inches(1.95), Inches(2.88), Inches(1.25), "0", "Historique exploité", "Comme moteur de score", GOLD)

add_card(s, Inches(0.5), Inches(3.60), Inches(6.0), Inches(2.60), fill=WHITE, border=RED)
add_rect(s, Inches(0.5), Inches(3.60), Inches(6.0), Inches(0.12), RED)
add_text(s, Inches(0.78), Inches(3.85), Inches(5.4), Inches(0.35), "Ce que vit l'agent aujourd'hui", size=15, bold=True, color=RED)
add_rich_bullets(s, Inches(0.78), Inches(4.35), Inches(5.4), Inches(1.7), [
    ("3 heures :", "par dossier, CAF et RCSD recalculés à la main."),
    ("Hétérogène :", "chaque agence juge avec sa propre grille."),
    ("Invisible :", "aucune trace exploitable pour auditer."),
], size=11, accent=RED)

add_card(s, Inches(6.85), Inches(3.60), Inches(5.98), Inches(2.60), fill=SOFT_TEAL, border=TURQ)
add_text(s, Inches(7.13), Inches(3.85), Inches(5.4), Inches(0.35), "La question posée", size=15, bold=True, color=TEAL)
add_text(s, Inches(7.13), Inches(4.35), Inches(5.4), Inches(1.6),
         "Objectiver l'éligibilité et le plafond\nà partir du comportement du membre,\nsans remplacer la décision humaine :\nAgent → Chef d'agence → CIC.",
         size=13, bold=True, color=TEAL)

add_notes(s,
    "PROBLÈME — 3 h pour instruire un dossier, ~8 % d'impayés, tout demandeur doit ouvrir un compte membre, "
    "l'historique institutionnel existe mais n'est pas exploité, BIC/fiscal et cautions restent très papier. "
    "Problématique : objectiver l'éligibilité et le plafond depuis le comportement du membre, sans remplacer la "
    "décision humaine. Contexte : institutions membres de la CIF, FUCEC-Togo comme échantillon. Cycle observé en "
    "9 étapes, prototype déployable en 72 h sur Android/Windows, données synthétiques.")
footer(s, 3)


# ============================================================
# 4 — 2. SOLUTION
# ============================================================
s = add_slide()
section_header(s, "2 · Solution", "DigiScore-WA : le copilote d'octroi des SFD",
               "À partir du dossier du membre, il propose un score, un plafond et un message — la décision reste humaine.")
add_card(s, Inches(0.5), Inches(1.95), Inches(6.0), Inches(3.55), fill=WHITE, border=TEAL)
add_rect(s, Inches(0.5), Inches(1.95), Inches(6.0), Inches(0.12), TEAL)
add_text(s, Inches(0.78), Inches(2.20), Inches(5.4), Inches(0.35), "Ce que fait le copilote", size=15, bold=True, color=TEAL)
add_rich_bullets(s, Inches(0.78), Inches(2.70), Inches(5.4), Inches(2.6), [
    ("Il assemble :", "le dossier du membre — historique agence, preuves externes, collecte A–E, BIC/fiscal, cautions."),
    ("Il évalue :", "un score /100 sur 6 critères métier et un plafond recommandé, avec un message clair."),
    ("Il protège :", "des garde-fous bloquants (RCSD, ESG, fiscal, cautions, incidents) avant toute recommandation."),
    ("Il laisse décider :", "Agent → Chef d'agence → CIC ; chaque décision et override sont tracés."),
], size=11, accent=TEAL)

add_card(s, Inches(6.85), Inches(1.95), Inches(5.98), Inches(3.55), fill=SOFT_TEAL, border=TURQ)
add_text(s, Inches(7.13), Inches(2.20), Inches(5.4), Inches(0.35), "Ce que chacun y gagne", size=15, bold=True, color=TURQ)
gains = [
    ("Agent", "instruit plus vite, avec un message prêt pour l'entretien."),
    ("Chef d'agence", "des dossiers triés et comparables d'une agence à l'autre."),
    ("CIC", "la voie exceptionnelle instruite avec garanties et simulations."),
    ("Direction", "des décisions et un portefeuille lisibles, auditables."),
]
for i, (who, what) in enumerate(gains):
    y = Inches(2.78 + i * 0.66)
    add_rect(s, Inches(7.13), y + Inches(0.06), Inches(0.11), Inches(0.30), TURQ)
    add_text(s, Inches(7.38), y, Inches(1.75), Inches(0.32), who, size=10.5, bold=True, color=TEAL)
    add_text(s, Inches(9.20), y - Inches(0.02), Inches(3.45), Inches(0.60), what, size=9.5, color=INK)

add_card(s, Inches(0.5), Inches(5.70), Inches(12.33), Inches(1.10), fill=SOFT_GOLD, border=GOLD)
add_text(s, Inches(0.78), Inches(5.86), Inches(11.7), Inches(0.30),
         "La différence : plafond type télécom · membre préalable · 3 niveaux humains · ML shadow · sidecar ADD-only",
         size=11.5, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.78), Inches(6.24), Inches(11.7), Inches(0.30),
         "L'IA éclaire, l'humain décide.", size=10, color=MUTED, align=PP_ALIGN.CENTER)
add_notes(s,
    "SOLUTION — Décrire, pas détailler : DigiScore-WA lit le dossier du membre (historique, preuves externes, "
    "collecte, BIC/fiscal, cautions), en tire un score /100 sur 6 critères et un plafond recommandé avec un message "
    "clair, applique des garde-fous bloquants, puis laisse la décision à l'Agent, au Chef d'agence et au CIC avec "
    "trace et override. Gains : agent plus rapide, chef avec des dossiers comparables, CIC outillé pour la voie "
    "exceptionnelle, direction avec un portefeuille lisible. Les formules et le détail du score viendront en Q&R. DÉMO LIVE (2:00–5:00) : Kodjo → score 83,7, plafond 870 000, UPSELL ; Aisha thin-file → RCSD 0,41 KNOCKOUT_RCSD ; Isaac 10 M → VOIE_EXCEPTIONNELLE CIC ; compte gelé → aucune demande. Un membre manipule, un autre commente, capture de secours prête.")
footer(s, 4)


# ============================================================
# 5 — 3. ARCHITECTURE DE LA BASE DE DONNÉES (SCHÉMA)
# ============================================================
s = add_slide()
section_header(s, "3 · Architecture · Base de données", "Un sidecar ADD-only : on lit le SI, on n'écrit que digiscore_*",
               "40+ tables en 5 blocs — deux cahiers jamais fusionnés — dates point-in-time pour le PAR.")

blocs = [
    ("Référentiels", TEAL, [
        "agency", "credit_product", "app_user", "digiscore_member_map",
    ]),
    ("Membre & agence", TURQ, [
        "member", "account", "account_movement",
        "savings_snapshot", "past_credit",
    ]),
    ("Demande & collecte", ORANGE, [
        "credit_application", "income_expense", "wealth", "guarantor_review",
    ]),
    ("Score & décision", PURP, [
        "score_result", "financial_ratio", "decision", "audit_log",
    ]),
    ("Ailleurs & pilotage", GREEN, [
        "external_account", "bic_report",
        "outstanding_loan", "portfolio_followup", "recovery_case",
    ]),
]
for i, (name, color, tables) in enumerate(blocs):
    x = Inches(0.5 + i * 2.47)
    add_card(s, x, Inches(1.95), Inches(2.35), Inches(2.45), fill=WHITE, border=color)
    add_rect(s, x, Inches(1.95), Inches(2.35), Inches(0.10), color)
    add_text(s, x + Inches(0.10), Inches(2.12), Inches(2.15), Inches(0.28), name,
             size=9.5, bold=True, color=color, align=PP_ALIGN.CENTER)
    for j, table in enumerate(tables):
        y = Inches(2.52 + j * 0.35)
        add_rect(s, x + Inches(0.12), y, Inches(2.11), Inches(0.30), LIGHT, rounded=True)
        add_text(s, x + Inches(0.16), y + Inches(0.02), Inches(2.03), Inches(0.26), table,
                 size=7.8, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    if i < 4:
        arrow(s, x + Inches(2.37), Inches(3.10), Inches(0.09), Inches(0.16), GOLD)

add_card(s, Inches(0.5), Inches(4.85), Inches(12.33), Inches(1.55), fill=SOFT_TEAL, border=TURQ)
add_text(s, Inches(0.78), Inches(5.05), Inches(11.7), Inches(0.35),
         "Trois règles d'architecture", size=14, bold=True, color=TEAL)
add_text(s, Inches(0.78), Inches(5.50), Inches(11.7), Inches(0.80),
         "1. Deux cahiers jamais fusionnés   ·   2. Écriture digiscore_* uniquement, aucun ALTER du SI   ·   3. Dates partout → PAR constructible.",
         size=10.5, color=INK, align=PP_ALIGN.CENTER)

add_notes(s,
    "ARCHITECTURE BDD (zoom 30 s, critère faisabilité) — Sidecar ADD-only : on lit le SI via API/passerelle et "
    "mapping, on écrit uniquement dans les tables digiscore_* (CREATE/INSERT), jamais d'ALTER ni de greffe "
    "transactionnelle. 40+ tables en 5 blocs : référentiels, membre & agence, demande & collecte A–E, score & "
    "décision, ailleurs & pilotage PAR. Deux cahiers séparés (agence vs autres IF) pour ne pas fausser le solde. "
    "Les colonnes dates (disbursed_on, due_on, observed_on, as_of, period_month) rendent le PAR30 constructible "
    "et les features point-in-time. Environ 120k profils synthétiques + 12 profils golden pour la démo.")
footer(s, 5)


# ============================================================
# 6 — 4. IMPACT
# ============================================================
s = add_slide()
section_header(s, "4 · Impact", "3 h → 45 min, et une décision comparable partout",
               "Objectifs cibles du pilote : temps d'instruction, qualité du portefeuille, traçabilité.")
kpi_card(s, Inches(0.5), Inches(1.90), Inches(2.8), Inches(1.05), "3 h → 45 min", "Instruction", "×4 plus rapide", GREEN)
kpi_card(s, Inches(3.5), Inches(1.90), Inches(2.8), Inches(1.05), "8 % → 5 %", "Impayés (vision)", "Sous contrôle hebdo", ORANGE)
kpi_card(s, Inches(6.5), Inches(1.90), Inches(2.8), Inches(1.05), "100 %", "Décisions tracées", "Audit BCEAO", TEAL)
kpi_card(s, Inches(9.5), Inches(1.90), Inches(3.3), Inches(1.05), "1 grille", "Pour toutes les agences", "Fini le cas par cas", PURP)

add_card(s, Inches(0.5), Inches(3.60), Inches(12.33), Inches(2.30), fill=WHITE, border=TURQ)
add_text(s, Inches(0.78), Inches(3.82), Inches(11.7), Inches(0.35), "Bénéfices attendus (cible pilote)", size=14, bold=True, color=TEAL)
bars = [
    ("Temps d'instruction", "− 75 %", 0.75, GREEN),
    ("Dossiers documentés", "+ 40 %", 0.40, FUCEC_GREEN),
    ("Décisions tracées", "100 %", 1.00, TEAL),
    ("Dérive PAR détectée", "plus tôt", 0.60, ORANGE),
]
for i, (label, val, pct, color) in enumerate(bars):
    y = Inches(4.35 + i * 0.36)
    add_text(s, Inches(0.85), y, Inches(2.30), Inches(0.28), label, size=10, bold=True, color=TEAL)
    hbar(s, Inches(3.30), y + Inches(0.04), Inches(7.20), Inches(0.20), pct, color)
    add_text(s, Inches(10.70), y, Inches(1.90), Inches(0.28), val, size=10.5, bold=True, color=color)
add_card(s, Inches(0.5), Inches(5.95), Inches(12.33), Inches(0.90), fill=SOFT_GOLD, border=GOLD)
add_text(s, Inches(0.78), Inches(6.10), Inches(11.7), Inches(0.55),
         "Objectiver sans remplacer : le moteur recommande, l'agent/chef/CIC décide — et chaque écart devient une donnée pour améliorer la grille.",
         size=11.5, bold=True, color=TEAL, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
add_notes(s,
    "IMPACT (critère 15 %) — Cible : 3 h → 45 min par dossier, 8 % → 5 % d'impayés (vision), 100 % de décisions "
    "tracées pour l'audit BCEAO, une seule grille pour toutes les agences. Une estimation assumée suffit, à confirmer "
    "en pilote et mesurer via score_result, decision, audit_log. Message clé : objectiver sans remplacer, et chaque "
    "override devient une donnée d'amélioration.")
footer(s, 6)


# =======================# ============================================================
# 7 — 5. L'ÉQUIPE
# ============================================================
s = add_slide()
section_header(s, "5 · L'équipe", "Équipe Alpha — cinq profils, un seul moteur",
               "Finance, base de données, produit, data science, fullstack : une seule référence, le cahier des charges.")
membres = [
    ("ADEKOUDJO ADENKA KOMLA", "Chef de l'équipe\nFinance, banque et assurance", TEAL),
    ("AYOLA ESSOREOU MOISE", "Expert base de données\nDéveloppeur Backend", TURQ),
    ("KOUDJEGA FERDINE", "Conception fonctionnelle, communication et interface", ORANGE),
    ("AMAH-TCHOUTCHOU ELIKPLIM JOSUE", "Data Scientist", PURP),
    ("KOUASSI AHLONKOBA ARIELLE KEPHIRA", "Développeuse Fullstack, Designer", GOLD),
]
for i, (nom, role, color) in enumerate(membres):
    x = Inches(0.5 + i * 2.47)
    add_card(s, x, Inches(2.00), Inches(2.35), Inches(2.42), fill=WHITE, border=color)
    add_rect(s, x, Inches(2.00), Inches(2.35), Inches(0.12), color)
    numbered_badge(s, i + 1, x + Inches(0.16), Inches(2.22), color)
    add_text(s, x + Inches(0.12), Inches(2.82), Inches(2.11), Inches(0.85), nom,
             size=9.5, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
    add_text(s, x + Inches(0.12), Inches(3.45), Inches(2.11), Inches(0.85), role,
             size=8.6, color=MUTED, align=PP_ALIGN.CENTER)

add_card(s, Inches(0.5), Inches(4.75), Inches(12.33), Inches(1.85), fill=SOFT_TEAL, border=TURQ)
add_text(s, Inches(0.78), Inches(4.93), Inches(11.7), Inches(0.35), "Comment on a travaillé", size=14, bold=True, color=TEAL)
add_rich_bullets(s, Inches(0.78), Inches(5.38), Inches(11.7), Inches(1.05), [
    ("Monorepo :", "chacun clone, docker compose up, pytest scoring/tests avant merge."),
    ("Contrats :", "DossierInput / ScoreResult et message_code figés — aucun rename sans ping."),
    ("Revue croisée :", "le back ne masque pas un bug moteur, le front ne calcule aucune formule."),
], size=10.5, accent=TURQ)
add_notes(s,
    "ÉQUIPE (critère 5 %) — Cinq profils : Komla Adekoudjo (chef d'équipe, finance/banque), Moïse Ayola (base de "
    "données), Ferdine Koudjega (fonctionnel/UI), Josué Amah-Tchoutchou (data scientist), Arielle Kephira Kouassi "
    "(fullstack/designer). Faire parler plusieurs membres et assumer les limites du MVP.")
footer(s, 7)


# ============================================================
# 8 — 6. SUITE
# ============================================================
s = add_slide()
section_header(s, "6 · Suite", "Du prototype au pilote, puis au suivi complet",
               "Ce qui est fait, ce qui vient, et ce qu'on ne fera pas sans données réelles.")
suites = [
    ("MAINTENANT", "Prototype 72 h", TEAL, [
        "M1–M5 fonctionnels, 12 profils démo, 3 rôles.",
        "Moteur règles + plafond + messages, tests golden.",
        "ML shadow : scorecard, anomalies, résilience.",
    ]),
    ("PILOTE", "Avec la FUCEC", TURQ, [
        "Extraits réels dans les mêmes tables.",
        "Adapter réel + atelier DSI, sidecar ADD-only.",
        "Recalibrage des seuils sur historiques locaux.",
    ]),
    ("ENSUITE", "M6 / M7 + ML utile", ORANGE, [
        "Suivi PAR & recouvrement, alertes chef/CIC.",
        "Label PAR30 post-décaissement → modèle calibré.",
        "Mobile money / wallets, multi-SFD, i18n.",
    ]),
]
for i, (tag, title, color, items) in enumerate(suites):
    x = Inches(0.5 + i * 4.2)
    add_card(s, x, Inches(2.00), Inches(3.95), Inches(3.05), fill=WHITE, border=color)
    add_rect(s, x, Inches(2.00), Inches(3.95), Inches(0.12), color)
    add_text(s, x + Inches(0.25), Inches(2.22), Inches(3.45), Inches(0.28), tag, size=11, bold=True, color=color)
    add_text(s, x + Inches(0.25), Inches(2.55), Inches(3.45), Inches(0.35), title, size=14, bold=True, color=TEAL)
    add_rich_bullets(s, x + Inches(0.25), Inches(3.05), Inches(3.45), Inches(1.9), items, size=10.2, accent=color)

add_card(s, Inches(0.5), Inches(5.35), Inches(12.33), Inches(1.35), fill=SOFT_ORG, border=ORANGE)
add_text(s, Inches(0.78), Inches(5.52), Inches(11.7), Inches(0.30),
         "Ce qu'on ne vend pas", size=12.5, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.78), Inches(5.90), Inches(11.7), Inches(0.55),
         "De l'IA sans données réelles · un score seul, sans plafond ni message · le remplacement du comité de crédit.",
         size=11, color=INK, align=PP_ALIGN.CENTER)
add_notes(s,
    "SUITE (7:00–7:30) — Maintenant : prototype M1–M5 + ML shadow. Pilote FUCEC : extraits réels, adapter réel, "
    "recalibrage. Ensuite : M6/M7 PAR & recouvrement, vrai label PAR30 post-décaissement pour un ML calibré, mobile "
    "money. Ce qu'on ne vend pas : IA sans données réelles, score seul, remplacement du comité.")
footer(s, 8)


# ============================================================
# 9 — 7. MOT DE FIN
# ============================================================
s = add_slide(bg=TEAL)
add_rect(s, 0, 0, Inches(0.4), SH, GOLD)
add_rect(s, Inches(0.40), 0, Inches(0.07), SH, FUCEC_GREEN)
add_rect(s, Inches(0.47), 0, Inches(0.07), SH, FUCEC_RED)
add_text(s, Inches(0.8), Inches(0.55), Inches(11.5), Inches(0.35),
         "MERCI · QUESTIONS", size=13, bold=True, color=GOLD)
add_text(s, Inches(0.8), Inches(1.00), Inches(11.8), Inches(0.90),
         "DigiScore-WA", size=40, bold=True, color=WHITE)
add_text(s, Inches(0.8), Inches(1.95), Inches(11.5), Inches(0.40),
         "Le copilote d'éligibilité et de plafond des SFD CIF", size=17, bold=True, color=SOFT_TEAL)
add_text(s, Inches(0.8), Inches(2.55), Inches(11.5), Inches(0.80),
         "« Le ML éclaire, l'humain décide. »\nObjectiver sans remplacer : score explicable, plafond traçable, décision humaine auditée.",
         size=13, bold=True, color=GOLD)

closing = [
    ("Score /100", "6 critères, zones 40/70, KO priorisés", TURQ),
    ("Plafond type télécom", "montant + message, pas un oui/non", TURQ),
    ("3 niveaux humains", "Agent → Chef → CIC, override tracé", GOLD),
    ("Sidecar ADD-only", "déployable sans toucher au SI", GOLD),
    ("ML shadow", "vise juste, ne décide jamais", ORANGE),
    ("Données réelles ensuite", "pilote FUCEC, labels PAR30", ORANGE),
]
for i, (title, detail, color) in enumerate(closing):
    col = i % 3
    row = i // 3
    x = Inches(0.8 + col * 4.0)
    y = Inches(3.65 + row * 1.02)
    add_card(s, x, y, Inches(3.6), Inches(0.85), fill=TEAL_DARK, border=color)
    add_text(s, x + Inches(0.18), y + Inches(0.12), Inches(3.3), Inches(0.28), title,
             size=11.5, bold=True, color=color)
    add_text(s, x + Inches(0.18), y + Inches(0.44), Inches(3.3), Inches(0.30), detail,
             size=9, color=SOFT_TEAL)

for index, path in enumerate(LOGOS):
    x = Inches(0.8 + index * 1.5)
    add_card(s, x, Inches(5.95), Inches(1.30), Inches(0.75), fill=WHITE, border=BORDER)
    add_picture_fit(s, path, x + Inches(0.10), Inches(6.03), Inches(1.10), Inches(0.60))
add_text(s, Inches(5.6), Inches(6.02), Inches(6.9), Inches(0.65),
         "Équipe Alpha · Hackathon CIF DigiCoop-WA+ · Lomé, septembre 2026\nContacts : prénom.nom@…  ·  github.com/… (repo hackathon)",
         size=10.5, bold=True, color=WHITE, align=PP_ALIGN.RIGHT)
add_notes(s,
    "MOT DE FIN — Merci. Six points à retenir : score /100, plafond type télécom, 3 niveaux humains, sidecar "
    "ADD-only, ML shadow, données réelles pour la suite. Phrase de sortie : « Le ML éclaire, l'humain décide : "
    "objectiver sans remplacer. » Ouvrir les questions sur la démo. "
    "Trois questions difficiles à préparer (guide CIF) : "
    "(1) « Le ML décide-t-il ? » → non, shadow consultatif, jamais eligible/zone/KO ; il faudra des historiques "
    "FUCEC réels pour le calibrer. "
    "(2) « Et sans connexion, sur un Android d'entrée de gamme ? » → PWA mode dégradé, démo hors ligne, données "
    "pré-chargées, sidecar ADD-only. "
    "(3) « Que se passe-t-il si le score est contesté ? » → chaque point est traçable dans criteres[]/explication[], "
    "l'humain peut override avec motif, tout est historisé (audit_log, score_result_history).")


prs.core_properties.title = "DigiScore-WA — Pitch Hackathon CIF DigiCoop-WA+"
prs.core_properties.author = "Équipe Alpha"
prs.save(str(OUT))
print(f"PowerPoint genere : {OUT}")
print(f"Slides : {len(prs.slides)} · Format : 16:9 (13.333 x 7.5 pouces)")

try:
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", str(OUT), "--outdir", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    pdf_path = OUT.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"PDF de verification genere : {pdf_path}")
except Exception as exc:
    print(f"Note : conversion PDF non disponible ({exc})")
