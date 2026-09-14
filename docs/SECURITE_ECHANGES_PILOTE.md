# Sécurité des échanges SI ↔ DigiScore (phase pilote)

**Statut :** spécification **si DigiScore est retenu**. **Non implémenté** dans la démo hackathon.

**Pitch (une phrase) :** DigiScore ne remplace pas le SI FUCEC / CIF. Les agents restent authentifiés **chez le partenaire**. En pilote, le SI appelle nos APIs avec une **identité machine d’agence** (HMAC) ; aujourd’hui la PWA simule seulement le circuit Agent → Chef → CIC avec 3 comptes démo.

---

## 1. Principe (sidecar)

```text
Agent FUCEC  ──s’identifie──►  SI métier (déjà en place)
                                      │
                                      │  HMAC agence  (à brancher au pilote)
                                      ▼
                               DigiScore API
                                      │
                                      ▼
                               Postgres DigiScore (tables ADD-only)
```

| Qui | Fait foi sur | DigiScore ne fait pas |
|-----|----------------|------------------------|
| SI partenaire | L’humain (agent / chef / CIC dans **leur** annuaire) | Recréer l’AD, le SSO, les 200 logins agence |
| DigiScore | La **machine** qui appelle (cette COOPEC / cette agence a le droit) | Décider à la place du comité |

Tables `digiscore_*` et objets d’octroi = **ADD-only**. Zéro `ALTER` / `DROP` sur le schéma transactionnel partenaire.

La démo actuelle (`POST /auth/login` + JWT 3 rôles) **simule** le flux hiérarchique pour le jury. Elle n’est **pas** le modèle d’intégration SI.

---

## 2. Identité machine — table additive (à créer au pilote)

```text
api_client
  id              SERIAL PK
  agency_id       FK → agency(id)
  name            VARCHAR(80)          -- « Passerelle SI Lomé »
  key_id          VARCHAR(40) UNIQUE   -- public, ex. ds_ag1_live
  secret_hash     VARCHAR(128)         -- bcrypt/argon2 ; le secret n’est montré qu’une fois
  is_active       BOOLEAN DEFAULT TRUE
  scopes          JSONB                -- ["agent"] | ["chef_agence"] | ["cic"]
  created_at      TIMESTAMPTZ
```

- **Une clé par agence** (ou par environnement SI), pas une clé par agent.
- Seed pilote : 1 client `AGE-LME-01`, 1 client `AGE-KPA-01`, scopes `agent` par défaut.
- Rotation : désactiver `is_active`, émettre un nouveau `key_id`. Pas de secret en Git.

---

## 3. Protocole HMAC-SHA256 (défaut recommandé)

Headers :

| Header | Rôle |
|--------|------|
| `X-Api-Key` | `key_id` public |
| `X-Timestamp` | Unix secondes |
| `X-Signature` | hex HMAC-SHA256 |
| `X-Actor-External` | optionnel : code agent **du SI** (audit seulement) |

Chaîne signée :

```text
timestamp + "\n" + METHOD + "\n" + path + query + "\n" + SHA256(body)
```

Règles :

- Rejeter si `|now - timestamp| > 300` secondes (anti-rejeu grossier).
- Vérifier HMAC en temps constant.
- `X-Actor-External` va dans `audit_log.detail` ; **aucun** `app_user` créé pour cet agent.

Scopes : un client `agent` ne peut pas poser un avis CIC. Le SI atteste l’humain ; DigiScore atteste l’agence.

### Variantes (si le DSI les exige)

| Mécanisme | Quand |
|-----------|--------|
| **HMAC-SHA256** | Défaut pilote : secret partagé, simple à brancher |
| **Ed25519** | Si le partenaire refuse de stocker un secret et fournit une clé publique |
| **mTLS** | Si la DSI impose un certificat client sur le reverse-proxy |

Ne pas empiler les trois au jour 1.

---

## 4. Hors périmètre (volontaire)

- Une API key **par agent** (PKI, rotation, UX).
- OAuth2 / Keycloak / Azure AD **dès J1** (SSO institutionnel = chantier DSI, après le pilote HMAC).
- Multi-tenant multi-SFD isolées dans une seule base.
- Remplacer l’écran crédit du core banking.

---

## 5. Données pour un vrai ML plus tard (pas les 120k synthétiques)

Quand la FUCEC fournira des historiques **réels**, dater l’issue crédit :

- `outstanding_loan.disbursed_on`, `due_on`, `observed_on`
- `application_id` NOT NULL
- agrégats d’épargne **point-in-time** (recalcul depuis `account_movement`, pas un snapshot unique)

Ne **pas** entraîner un modèle de défaut sur le générateur volume.

---

## 6. Démo aujourd’hui vs pilote

| | Démo / pitch (code actuel) | Pilote (ce document) |
|--|----------------------------|----------------------|
| Humain | 3 logins DigiScore `agent` / `chef` / `cic` + mot de passe `demo` + JWT | Compte **SI** ; DigiScore ne les recrée pas |
| Machine | localhost, CORS Vite | `api_client` + HMAC |
| But | Simuler Agent → Chef → CIC | Greffer le sidecar sans toucher au transactionnel |
