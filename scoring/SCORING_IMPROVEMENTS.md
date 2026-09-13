# Améliorations du moteur de scoring

## Objectif

Le moteur reste déterministe pour les décisions MVP. Les knockouts, les seuils
RCSD, le plafond et les messages doivent être auditables et reproductibles.
Le ML n'est pas utilisé pour contourner une règle de sécurité.

## Changements implémentés

### Politique centralisée

`digiscore/policy.py` centralise les paramètres sensibles :

- taux annuel simple du crédit : `1,8 %` ;
- RCSD knockout : `< 1,00` ;
- RCSD confort : `>= 1,50` ;
- seuil documentaire fiscal : `500 000 FCFA` ;
- seuil de voie exceptionnelle : `8 000 000 FCFA` ;
- priorité des messages de knockout.

Le pipeline ne contient plus une longue chaîne de conditions répétant cette
priorité. `select_knockout_message()` sélectionne le premier code présent selon
la politique métier. Les knockouts restent tous conservés dans la réponse pour
l'explicabilité.

### Formule de plafond cohérente

Le service annuel est calculé dans `financials.py` avec le taux de `1,8 %`.
Le plafond RCSD utilise maintenant l'inverse exact de cette formule via
`montant_pour_service()`. L'ancienne approximation `1.1` pouvait produire un
plafond incohérent avec le RCSD affiché.

Le plafond final respecte toujours :

```text
min(plafond produit, capacité épargne/CAF/historique, capacité RCSD)
```

Puis il applique le micro-plafond thin-file, le facteur de zone et un arrondi
inférieur à `10 000 FCFA`.

## Règle d'intégration

Les tests unitaires couvrent le package pur. Un test d'intégration doit aussi
rejouer le chemin réel :

```text
PostgreSQL -> dossier_builder -> run() -> ScoreResult
```

Cette séparation est importante : les fixtures unitaires peuvent être valides
alors que les seeds SQL portent une combinaison différente de CAF, montant,
fiscalité ou garanties. Les cas seed doivent donc être vérifiés avec le
backend, puis synchronisés avec `data/synthetic/cas_attendus.json`.

## ML : trajectoire recommandée

Les 120 000 profils synthétiques sont utiles pour tester la volumétrie, mais ne
constituent pas une base de risque crédit fiable. Ils ne fournissent pas une
cible historique indépendante comme `PAR30`, `PAR90` ou défaut après
décaissement.

La trajectoire proposée est :

1. conserver les règles et knockouts comme décision de référence ;
2. collecter des demandes historiques avec une cible future et la date de
   décision ;
3. entraîner une régression logistique ou un modèle gradient boosting avec
   séparation temporelle et contrôle des fuites ;
4. exécuter le modèle en *shadow mode* et comparer son risque au score métier ;
5. envisager un recalibrage validé par le métier, sans autoriser le modèle à
   lever un knockout.

## Vérifications

Depuis la racine du dépôt :

```bash
pytest scoring/tests -q
```

Les invariants à conserver sont :

- tout knockout implique `eligible=false` et `montant_eligible=0` ;
- le plafond ne dépasse jamais le plafond produit ;
- une dette existante réduit la capacité RCSD ;
- les frontières de zone `40/41/70/71` restent stables ;
- une demande exceptionnelle est soumise à une décision humaine/CIC.
