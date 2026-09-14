-- DigiScore-WA — schema membre-centrique (identifiants EN, commentaires FR)
-- ADD-only cote SI partenaire : prefixe digiscore_* pour objets d'octroi.
-- Invariants : pas de demande sans member + account ; caution si seuil atteint.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Referentiel
-- ---------------------------------------------------------------------------
CREATE TABLE agency (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20) UNIQUE NOT NULL,
    name        VARCHAR(120) NOT NULL,
    city        VARCHAR(80) NOT NULL DEFAULT 'Lome',
    topology    VARCHAR(20) NOT NULL DEFAULT 'shared'
                CHECK (topology IN ('shared', 'split'))
);
COMMENT ON TABLE agency IS 'Agence / COOPEC. topology=shared (base unique) ou split (base locale).';
COMMENT ON COLUMN agency.topology IS 'Topologie SI : shared = base partagee, split = bases divisees.';

CREATE TABLE credit_product (
    id                    SERIAL PRIMARY KEY,
    code                  VARCHAR(30) UNIQUE NOT NULL,
    label                 VARCHAR(120) NOT NULL,
    min_amount            NUMERIC(14, 0) NOT NULL DEFAULT 50000,
    max_amount            NUMERIC(14, 0) NOT NULL DEFAULT 3000000,
    max_term_months       INT NOT NULL DEFAULT 18,
    indicative_rate       NUMERIC(6, 3) NOT NULL DEFAULT 0.018,
    guarantor_threshold   NUMERIC(14, 0) NOT NULL DEFAULT 2000000,
    min_guarantors        INT NOT NULL DEFAULT 1,
    is_exceptional        BOOLEAN NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE credit_product IS 'Catalogue produits. Au-dela de guarantor_threshold : cautionnaires evalues.';
COMMENT ON COLUMN credit_product.guarantor_threshold IS 'Seuil (FCFA) a partir duquel des cautions eligibles sont exigibles.';
COMMENT ON COLUMN credit_product.is_exceptional IS 'Voie exceptionnelle (gros tickets) : CIC obligatoire.';

CREATE TABLE financial_institution (
    id      SERIAL PRIMARY KEY,
    code    VARCHAR(30) UNIQUE NOT NULL,
    name    VARCHAR(120) NOT NULL,
    city    VARCHAR(80) NOT NULL DEFAULT 'Lome',
    kind    VARCHAR(20) NOT NULL
            CHECK (kind IN ('coopec', 'banque', 'microfinance'))
);
COMMENT ON TABLE financial_institution IS 'Autres IF (COOPEC, banque, IMF). Pas de mobile money.';

CREATE TABLE app_user (
    id             SERIAL PRIMARY KEY,
    login          VARCHAR(40) UNIQUE NOT NULL,
    full_name      VARCHAR(80) NOT NULL,
    role           VARCHAR(20) NOT NULL CHECK (role IN ('agent', 'chef_agence', 'cic')),
    agency_id      INT REFERENCES agency (id),
    password_hash  VARCHAR(128)
);
COMMENT ON TABLE app_user IS 'Utilisateurs DigiScore demo (agent, chef d''agence, CIC). Mot de passe = simulation du flux, pas l''annuaire SI.';
COMMENT ON COLUMN app_user.password_hash IS 'bcrypt. Login demo : agent / chef / cic, mot de passe demo.';

-- ---------------------------------------------------------------------------
-- Membre / compte / historique institutionnel
-- ---------------------------------------------------------------------------
CREATE TABLE member (
    id              SERIAL PRIMARY KEY,
    external_code   VARCHAR(40) UNIQUE NOT NULL,
    last_name       VARCHAR(80) NOT NULL,
    first_name      VARCHAR(80) NOT NULL,
    gender          CHAR(1),
    birth_date      DATE,
    phone           VARCHAR(20),
    address         VARCHAR(200),
    area            VARCHAR(20) NOT NULL DEFAULT 'urbaine'
                    CHECK (area IN ('urbaine', 'rurale')),
    agency_id       INT NOT NULL REFERENCES agency (id),
    joined_on       DATE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'actif'
                    CHECK (status IN ('actif', 'gele', 'radie')),
    marital_status  VARCHAR(40),
    occupation      VARCHAR(80)
);
COMMENT ON TABLE member IS 'Membre institution. Compte prealable obligatoire avant toute demande.';
COMMENT ON COLUMN member.external_code IS 'Identifiant SI partenaire (NUM_CLIENT / CODE_MEMBRE). Lookup indexe.';
COMMENT ON COLUMN member.status IS 'actif | gele | radie — codes metier conserves pour le moteur / l''API.';
COMMENT ON COLUMN member.area IS 'Zone d''habitation (urbaine / rurale).';

CREATE INDEX idx_member_external_code ON member (external_code);
CREATE INDEX idx_member_name ON member (last_name, first_name);
CREATE INDEX idx_member_agency ON member (agency_id);
CREATE INDEX idx_member_status ON member (status);

CREATE TABLE account (
    id               SERIAL PRIMARY KEY,
    member_id        INT NOT NULL REFERENCES member (id),
    account_no       VARCHAR(30) UNIQUE NOT NULL,
    account_type     VARCHAR(20) NOT NULL DEFAULT 'epargne',
    opened_on        DATE NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'actif'
                     CHECK (status IN ('actif', 'gele', 'cloture')),
    current_balance  NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE account IS 'Compte d''operations / epargne du membre.';
COMMENT ON COLUMN account.account_no IS 'Numero de compte — lookup indexe, jamais de scan.';
COMMENT ON COLUMN account.status IS 'Compte gele = garde-fou : aucune demande.';

CREATE INDEX idx_account_no ON account (account_no);
CREATE INDEX idx_account_member ON account (member_id);

CREATE TABLE account_movement (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES account (id),
    moved_on        DATE NOT NULL,
    movement_type   VARCHAR(20) NOT NULL CHECK (movement_type IN ('depot', 'retrait', 'interet')),
    amount          NUMERIC(14, 0) NOT NULL,
    label           VARCHAR(160)
);
COMMENT ON TABLE account_movement IS 'Mouvements. Charger les N derniers (LIMIT), pas tout l''historique.';

CREATE INDEX idx_movement_account_date ON account_movement (account_id, moved_on DESC);

CREATE TABLE savings_snapshot (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES account (id),
    as_of           DATE NOT NULL DEFAULT DATE '2026-09-13',
    avg_balance_3m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_6m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_12m NUMERIC(14, 0) NOT NULL DEFAULT 0,
    UNIQUE (account_id, as_of)
);
COMMENT ON TABLE savings_snapshot IS 'Agregats epargne precalcules (perf 1M+) : evite de relire tous les mouvements.';
COMMENT ON COLUMN savings_snapshot.as_of IS 'Date de photo. UNIQUE(account_id, as_of).';

CREATE TABLE past_credit (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member (id),
    institution_id  INT REFERENCES financial_institution (id),
    amount          NUMERIC(14, 0) NOT NULL,
    term_months     INT NOT NULL,
    granted_on      DATE,
    closed_on       DATE,
    status          VARCHAR(20) NOT NULL
                    CHECK (status IN ('solde', 'en_cours', 'impaye')),
    late_count      INT NOT NULL DEFAULT 0,
    max_days_late   INT NOT NULL DEFAULT 0,
    source          VARCHAR(20) NOT NULL DEFAULT 'interne'
                    CHECK (source IN ('interne', 'externe', 'bic'))
);
COMMENT ON TABLE past_credit IS 'Credits internes (ou externes/BIC). source=interne | externe | bic.';
COMMENT ON COLUMN past_credit.institution_id IS 'NULL = cette COOPEC. Renseigne si source externe/bic.';

CREATE INDEX idx_past_credit_member ON past_credit (member_id);

CREATE TABLE incident (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member (id),
    incident_type   VARCHAR(40) NOT NULL,
    occurred_on     DATE NOT NULL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'faible'
                    CHECK (severity IN ('faible', 'moyenne', 'grave')),
    detail          TEXT
);
COMMENT ON TABLE incident IS 'Incidents de remboursement / contentieux. severity=grave = knockout.';

CREATE INDEX idx_incident_member ON incident (member_id);

CREATE TABLE member_guarantee (
    id           SERIAL PRIMARY KEY,
    member_id    INT NOT NULL REFERENCES member (id),
    kind         VARCHAR(80) NOT NULL,
    value_amount NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE member_guarantee IS 'Garanties materielles deja connues au niveau membre.';

CREATE TABLE external_account (
    id               SERIAL PRIMARY KEY,
    member_id        INT NOT NULL REFERENCES member (id) ON DELETE CASCADE,
    institution_id   INT NOT NULL REFERENCES financial_institution (id),
    account_no_mask  VARCHAR(40) NOT NULL UNIQUE,
    opened_on        DATE NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'actif'
                     CHECK (status IN ('actif', 'gele', 'cloture')),
    current_balance  NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE external_account IS 'Compte chez une autre IF (extrait). Pas de mobile money.';

CREATE INDEX idx_ext_account_member ON external_account (member_id);

CREATE TABLE external_account_movement (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES external_account (id) ON DELETE CASCADE,
    moved_on        DATE NOT NULL,
    movement_type   VARCHAR(20) NOT NULL CHECK (movement_type IN ('depot', 'retrait', 'interet')),
    amount          NUMERIC(14, 0) NOT NULL,
    label           VARCHAR(160)
);
COMMENT ON TABLE external_account_movement IS 'Releve ailleurs. Jamais melange a account_movement.';

CREATE INDEX idx_ext_mvt_account_date ON external_account_movement (account_id, moved_on DESC);

CREATE TABLE external_savings_snapshot (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES external_account (id) ON DELETE CASCADE,
    as_of           DATE NOT NULL,
    avg_balance_3m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_6m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_12m NUMERIC(14, 0) NOT NULL DEFAULT 0,
    UNIQUE (account_id, as_of)
);
COMMENT ON TABLE external_savings_snapshot IS 'Photo epargne ailleurs, datee.';

-- ---------------------------------------------------------------------------
-- Demande + collecte terrain A-E
-- ---------------------------------------------------------------------------
CREATE TABLE credit_application (
    id                          SERIAL PRIMARY KEY,
    member_id                   INT NOT NULL REFERENCES member (id),
    product_id                  INT NOT NULL REFERENCES credit_product (id),
    agent_id                    INT REFERENCES app_user (id),
    agency_id                   INT REFERENCES agency (id),
    purpose                     VARCHAR(200) NOT NULL,
    requested_amount            NUMERIC(14, 0) NOT NULL,
    term_months                 INT NOT NULL,
    status                      VARCHAR(30) NOT NULL DEFAULT 'brouillon'
                                CHECK (status IN (
                                    'brouillon', 'analyse', 'soumis_chef',
                                    'renvoye', 'soumis_cic', 'accorde',
                                    'conditionne', 'refuse', 'clos'
                                )),
    tax_status                  VARCHAR(20) NOT NULL DEFAULT 'non_fourni'
                                CHECK (tax_status IN (
                                    'en_regle', 'a_verifier', 'non_conforme', 'non_fourni'
                                )),
    has_external_credits        BOOLEAN NOT NULL DEFAULT FALSE,
    external_proofs_ok          BOOLEAN NOT NULL DEFAULT FALSE,
    esg_exclusion               BOOLEAN NOT NULL DEFAULT FALSE,
    applied_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guarantor_threshold_reached BOOLEAN GENERATED ALWAYS AS (
                                    requested_amount >= 2000000
                                ) STORED
);
COMMENT ON TABLE credit_application IS 'Demande du jour. Impossible sans member+account actifs.';
COMMENT ON COLUMN credit_application.tax_status IS 'Situation fiscale : en_regle | a_verifier | non_conforme | non_fourni.';
COMMENT ON COLUMN credit_application.has_external_credits IS 'Credits ailleurs (hors institution) declares.';
COMMENT ON COLUMN credit_application.external_proofs_ok IS 'Pieces externes fournies (releve, carnet, echeancier, BIC).';
COMMENT ON COLUMN credit_application.guarantor_threshold_reached IS 'Flag genere : montant >= 2 000 000 FCFA (politique produit par defaut).';

CREATE INDEX idx_application_member ON credit_application (member_id);
CREATE INDEX idx_application_status ON credit_application (status);
CREATE INDEX idx_application_agency ON credit_application (agency_id);

CREATE TABLE household (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    household_size  INT NOT NULL DEFAULT 1,
    housing         VARCHAR(40),
    dependents      INT NOT NULL DEFAULT 0
);
COMMENT ON TABLE household IS 'Collecte A — menage (taille, logement, personnes a charge).';

CREATE TABLE activity (
    id                SERIAL PRIMARY KEY,
    application_id    INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    activity_type     VARCHAR(80) NOT NULL,
    description       TEXT,
    seniority_months  INT NOT NULL DEFAULT 12,
    location_area     VARCHAR(40),
    is_seasonal       BOOLEAN NOT NULL DEFAULT FALSE,
    proof_level       CHAR(2) DEFAULT 'N1'
);
COMMENT ON TABLE activity IS 'Collecte B — activite. is_seasonal = creux de tresorerie possibles.';

CREATE TABLE economic_model (
    id                   SERIAL PRIMARY KEY,
    application_id       INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    client_segments      VARCHAR(160),
    product_service      VARCHAR(160),
    avg_price            NUMERIC(14, 0),
    unit_variable_cost   NUMERIC(14, 0),
    monthly_fixed_cost   NUMERIC(14, 0),
    sales_rhythm         VARCHAR(40)
);
COMMENT ON TABLE economic_model IS 'Collecte C — modele economique (6 questions type FUCEC).';

CREATE TABLE market (
    id                         SERIAL PRIMARY KEY,
    application_id             INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    high_season                VARCHAR(40),
    low_season                 VARCHAR(40),
    daily_volume               NUMERIC(12, 1),
    competitor_count           INT,
    single_outlet_dependency   BOOLEAN NOT NULL DEFAULT FALSE,
    proof_level                CHAR(2) DEFAULT 'N1'
);
COMMENT ON TABLE market IS 'Collecte D — marche. Dependance a un seul debouche = risque activite.';

CREATE TABLE income_expense (
    id                      SERIAL PRIMARY KEY,
    application_id          INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    revenue                 NUMERIC(14, 0) NOT NULL DEFAULT 0,
    cogs                    NUMERIC(14, 0) NOT NULL DEFAULT 0,
    operating_costs         NUMERIC(14, 0) NOT NULL DEFAULT 0,
    financial_income        NUMERIC(14, 0) NOT NULL DEFAULT 0,
    main_activity_income    NUMERIC(14, 0) NOT NULL DEFAULT 0,
    secondary_income        NUMERIC(14, 0) NOT NULL DEFAULT 0,
    spouse_income           NUMERIC(14, 0) NOT NULL DEFAULT 0,
    personal_income         NUMERIC(14, 0) NOT NULL DEFAULT 0,
    rent_cost               NUMERIC(14, 0) NOT NULL DEFAULT 0,
    school_cost             NUMERIC(14, 0) NOT NULL DEFAULT 0,
    existing_debt_service   NUMERIC(14, 0) NOT NULL DEFAULT 0,
    family_cost             NUMERIC(14, 0) NOT NULL DEFAULT 0,
    equity                  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    total_debt              NUMERIC(14, 0) NOT NULL DEFAULT 0,
    total_assets            NUMERIC(14, 0) NOT NULL DEFAULT 0,
    current_assets          NUMERIC(14, 0) NOT NULL DEFAULT 0,
    current_liabilities     NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_inventory           NUMERIC(14, 0) NOT NULL DEFAULT 0,
    net_income              NUMERIC(14, 0) NOT NULL DEFAULT 0,
    income_proof_level      CHAR(2) DEFAULT 'N1',
    expense_proof_level     CHAR(2) DEFAULT 'N1'
);
COMMENT ON TABLE income_expense IS 'Collecte E — revenus/charges. revenue=CA, cogs=CMV. Preuves N1/N2/N3.';
COMMENT ON COLUMN income_expense.revenue IS 'Chiffre d''affaires annuel (CA).';
COMMENT ON COLUMN income_expense.cogs IS 'Cout des marchandises vendues (CMV).';

CREATE TABLE wealth (
    id                      SERIAL PRIMARY KEY,
    application_id          INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    productive_assets       NUMERIC(14, 0) NOT NULL DEFAULT 0,
    non_productive_assets   NUMERIC(14, 0) NOT NULL DEFAULT 0,
    formal_liabilities      NUMERIC(14, 0) NOT NULL DEFAULT 0,
    informal_liabilities    NUMERIC(14, 0) NOT NULL DEFAULT 0,
    signal_revenue_erosion  BOOLEAN NOT NULL DEFAULT FALSE,
    signal_margin           BOOLEAN NOT NULL DEFAULT FALSE,
    signal_receivables      BOOLEAN NOT NULL DEFAULT FALSE,
    signal_payables         BOOLEAN NOT NULL DEFAULT FALSE,
    signal_net_worth        BOOLEAN NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE wealth IS 'Patrimoine + 5 signaux (2-3 simultanés ? revue Chef/CIC).';

CREATE TABLE monthly_cashflow (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    month_no        INT NOT NULL CHECK (month_no BETWEEN 1 AND 12),
    period_month    DATE,
    inflow          NUMERIC(14, 0) NOT NULL DEFAULT 0,
    outflow         NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE monthly_cashflow IS 'Tresorerie 12 mois. Interdit de lisser le CA annuel en 12 parts egales.';
COMMENT ON COLUMN monthly_cashflow.period_month IS '1er du mois calendaire (ancre saison).';

CREATE TABLE application_guarantee (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    kind            VARCHAR(80) NOT NULL,
    value_amount    NUMERIC(14, 0) NOT NULL DEFAULT 0,
    proof_level     CHAR(2) DEFAULT 'N2'
);
COMMENT ON TABLE application_guarantee IS 'Garanties rattachees a la demande (N1-N3).';

CREATE TABLE financial_ratio (
    id                  SERIAL PRIMARY KEY,
    application_id      INT NOT NULL UNIQUE REFERENCES credit_application (id) ON DELETE CASCADE,
    ebe                 NUMERIC(14, 2),
    caf                 NUMERIC(14, 2),
    rcsd                NUMERIC(8, 3),
    gross_margin_pct    NUMERIC(8, 2),
    net_margin_pct      NUMERIC(8, 2),
    solvency            NUMERIC(8, 3),
    inventory_days      NUMERIC(10, 1),
    equity_ratio_pct    NUMERIC(8, 2),
    working_capital_pct NUMERIC(8, 2),
    net_worth           NUMERIC(14, 2),
    weak_ratio_count    INT NOT NULL DEFAULT 0,
    stress_month        INT,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE financial_ratio IS 'Resultats M2 courants. Historique = financial_ratio_history.';

CREATE TABLE financial_ratio_history (
    history_id          SERIAL PRIMARY KEY,
    archived_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    application_id      INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    ebe                 NUMERIC(14, 2),
    caf                 NUMERIC(14, 2),
    rcsd                NUMERIC(8, 3),
    gross_margin_pct    NUMERIC(8, 2),
    net_margin_pct      NUMERIC(8, 2),
    solvency            NUMERIC(8, 3),
    inventory_days      NUMERIC(10, 1),
    equity_ratio_pct    NUMERIC(8, 2),
    working_capital_pct NUMERIC(8, 2),
    net_worth           NUMERIC(14, 2),
    weak_ratio_count    INT NOT NULL DEFAULT 0,
    stress_month        INT,
    computed_at         TIMESTAMPTZ
);
COMMENT ON TABLE financial_ratio_history IS 'Copies avant ecrasement /analyser.';

-- ---------------------------------------------------------------------------
-- BIC / fiscal / pieces
-- ---------------------------------------------------------------------------
CREATE TABLE bic_consent (
    id          SERIAL PRIMARY KEY,
    member_id   INT NOT NULL REFERENCES member (id),
    signed_on   DATE NOT NULL DEFAULT CURRENT_DATE,
    status      VARCHAR(20) NOT NULL DEFAULT 'signe',
    scan_path   VARCHAR(255)
);
COMMENT ON TABLE bic_consent IS 'Consentement BIC trace (scan + date).';

CREATE TABLE bic_report (
    id                     SERIAL PRIMARY KEY,
    member_id              INT REFERENCES member (id),
    application_id         INT REFERENCES credit_application (id),
    external_credit_count  INT NOT NULL DEFAULT 0,
    bic_incident_count     INT NOT NULL DEFAULT 0,
    indebtedness_summary   TEXT,
    source                 VARCHAR(20) NOT NULL DEFAULT 'simulate'
                           CHECK (source IN ('simulate', 'api', 'fichier'))
);
COMMENT ON TABLE bic_report IS 'Rapport BIC. source=simulate en hackathon, api en pilote.';

CREATE TABLE supporting_document (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    document_type   VARCHAR(30) NOT NULL
                    CHECK (document_type IN (
                        'BIC', 'FISCAL', 'RELEVE', 'CARNET',
                        'ECHEANCIER', 'ATTESTATION_SOLDE', 'CNI', 'AUTRE'
                    )),
    file_path       VARCHAR(255),
    ocr_quality     VARCHAR(20) NOT NULL DEFAULT 'ok'
                    CHECK (ocr_quality IN ('ok', 'flou', 'sombre', 'coupe')),
    status          VARCHAR(20) NOT NULL DEFAULT 'recu',
    validated_at    TIMESTAMPTZ
);
COMMENT ON TABLE supporting_document IS 'Pieces : BIC, fiscal, releve, carnet, echeancier, attestation, CNI.';
COMMENT ON COLUMN supporting_document.ocr_quality IS 'Controle qualite photo : ok | flou | sombre | coupe.';

-- ---------------------------------------------------------------------------
-- Cautionnaires
-- ---------------------------------------------------------------------------
CREATE TABLE guarantor (
    id              SERIAL PRIMARY KEY,
    last_name       VARCHAR(80) NOT NULL,
    first_name      VARCHAR(80) NOT NULL,
    phone           VARCHAR(20),
    relationship    VARCHAR(40),
    member_id       INT REFERENCES member (id)
);
COMMENT ON TABLE guarantor IS 'Cautionnaire. member_id renseigne s''il est deja membre.';

CREATE TABLE application_guarantor (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    guarantor_id    INT NOT NULL REFERENCES guarantor (id),
    guarantee_type  VARCHAR(20) NOT NULL DEFAULT 'solidaire'
                    CHECK (guarantee_type IN ('simple', 'solidaire')),
    pledged_amount  NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE application_guarantor IS 'Lien demande ? caution (simple ou solidaire).';

CREATE TABLE guarantor_review (
    id                      SERIAL PRIMARY KEY,
    application_guarantor_id INT NOT NULL REFERENCES application_guarantor (id) ON DELETE CASCADE,
    income                  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    expenses                NUMERIC(14, 0) NOT NULL DEFAULT 0,
    relay_caf               NUMERIC(14, 0),
    relay_rcsd              NUMERIC(8, 3),
    relay_score             NUMERIC(6, 2),
    eligible                BOOLEAN NOT NULL DEFAULT FALSE,
    reason                  TEXT
);
COMMENT ON TABLE guarantor_review IS 'Sait-il payer les echeances si le principal ne peut plus ?';

-- ---------------------------------------------------------------------------
-- Score / amortissement / decision / audit (objets DigiScore)
-- ---------------------------------------------------------------------------
CREATE TABLE score_result (
    id                    SERIAL PRIMARY KEY,
    application_id        INT NOT NULL UNIQUE REFERENCES credit_application (id) ON DELETE CASCADE,
    score_total           NUMERIC(6, 2) NOT NULL,
    thin_file             BOOLEAN NOT NULL DEFAULT FALSE,
    eligible              BOOLEAN NOT NULL DEFAULT FALSE,
    requested_amount      NUMERIC(14, 0) NOT NULL,
    eligible_amount       NUMERIC(14, 0) NOT NULL,
    suggested_max_amount  NUMERIC(14, 0),
    message_code          VARCHAR(40) NOT NULL,
    message_text          TEXT NOT NULL,
    criteria              JSONB NOT NULL DEFAULT '[]',
    knockouts             JSONB NOT NULL DEFAULT '[]',
    explanation           JSONB NOT NULL DEFAULT '[]',
    engine_version        VARCHAR(40) NOT NULL DEFAULT 'rules-v1',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE score_result IS 'Sortie moteur courante (1 ligne / demande). Historique = score_result_history.';

CREATE TABLE score_result_history (
    history_id            SERIAL PRIMARY KEY,
    archived_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    application_id        INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    score_total           NUMERIC(6, 2) NOT NULL,
    thin_file             BOOLEAN NOT NULL DEFAULT FALSE,
    eligible              BOOLEAN NOT NULL DEFAULT FALSE,
    requested_amount      NUMERIC(14, 0) NOT NULL,
    eligible_amount       NUMERIC(14, 0) NOT NULL,
    suggested_max_amount  NUMERIC(14, 0),
    message_code          VARCHAR(40) NOT NULL,
    message_text          TEXT NOT NULL,
    criteria              JSONB NOT NULL DEFAULT '[]',
    knockouts             JSONB NOT NULL DEFAULT '[]',
    explanation           JSONB NOT NULL DEFAULT '[]',
    engine_version        VARCHAR(40) NOT NULL DEFAULT 'rules-v1',
    scored_at             TIMESTAMPTZ
);
COMMENT ON TABLE score_result_history IS 'Copies avant ecrasement /analyser. ADD-only.';

CREATE INDEX idx_score_history_app ON score_result_history (application_id, archived_at DESC);

CREATE TABLE amortization_line (
    id                  SERIAL PRIMARY KEY,
    application_id      INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    installment_no      INT NOT NULL,
    installment_amount  NUMERIC(14, 0) NOT NULL,
    principal           NUMERIC(14, 0) NOT NULL,
    interest_amount     NUMERIC(14, 0) NOT NULL,
    remaining_principal NUMERIC(14, 0) NOT NULL,
    due_on              DATE
);
COMMENT ON TABLE amortization_line IS 'Tableau d''amortissement calcule sur le montant retenu (eligible).';
COMMENT ON COLUMN amortization_line.due_on IS 'Date d''echeance (M6 : retard, echeances du jour).';

CREATE TABLE decision (
    id              SERIAL PRIMARY KEY,
    application_id  INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    level           VARCHAR(20) NOT NULL CHECK (level IN ('agent', 'chef_agence', 'cic')),
    opinion         VARCHAR(20) NOT NULL
                    CHECK (opinion IN (
                        'soumettre', 'valider', 'refuser', 'renvoyer',
                        'escalader', 'accorder', 'conditionner'
                    )),
    reason          TEXT,
    is_override     BOOLEAN NOT NULL DEFAULT FALSE,
    user_id         INT REFERENCES app_user (id),
    decided_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE decision IS 'Avis humain. Motif obligatoire si ecart a la recommandation.';

CREATE INDEX idx_decision_application ON decision (application_id, decided_at DESC);

CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    application_id  INT REFERENCES credit_application (id),
    user_id         INT REFERENCES app_user (id),
    action          VARCHAR(60) NOT NULL,
    detail          TEXT,
    logged_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE audit_log IS 'Trace BCEAO : qui, quoi, quand, motif.';

CREATE TABLE digiscore_member_map (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member (id),
    external_code   VARCHAR(40) NOT NULL,
    source_system   VARCHAR(40) NOT NULL DEFAULT 'core_stub'
);
COMMENT ON TABLE digiscore_member_map IS 'Liaison ADD-only ID interne ? code SI partenaire. Pas de FK physique vers le core.';

CREATE INDEX idx_digiscore_map_code ON digiscore_member_map (external_code);

-- ---------------------------------------------------------------------------
-- Vision M6 / M7 (maquettes + structure pret pour pilote)
-- ---------------------------------------------------------------------------
CREATE TABLE outstanding_loan (
    id              SERIAL PRIMARY KEY,
    member_id       INT NOT NULL REFERENCES member (id),
    application_id  INT REFERENCES credit_application (id),
    principal       NUMERIC(14, 0) NOT NULL,
    outstanding     NUMERIC(14, 0) NOT NULL,
    days_late       INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'en_cours'
                    CHECK (status IN ('en_cours', 'solde', 'impaye')),
    disbursed_on    DATE,
    due_on          DATE,
    observed_on     DATE,
    restructured    BOOLEAN NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE outstanding_loan IS 'Credits decaisses (PAR). Structure M6, moteur live = OUT 72h.';
COMMENT ON COLUMN outstanding_loan.disbursed_on IS 'Date de decaissement (cible PAR constructible).';
COMMENT ON COLUMN outstanding_loan.restructured IS 'Credit restructure : compte au numerateur PAR (FUCEC).';

CREATE INDEX idx_loan_member ON outstanding_loan (member_id);
CREATE INDEX idx_loan_late ON outstanding_loan (days_late DESC);

CREATE TABLE loan_payment (
    id                   SERIAL PRIMARY KEY,
    outstanding_loan_id  INT NOT NULL REFERENCES outstanding_loan (id) ON DELETE CASCADE,
    paid_on              DATE NOT NULL,
    amount               NUMERIC(14, 0) NOT NULL,
    kind                 VARCHAR(20) NOT NULL DEFAULT 'echeance'
                         CHECK (kind IN ('echeance', 'anticipe', 'reechelonnement')),
    external_ref         VARCHAR(60)
);
COMMENT ON TABLE loan_payment IS 'Paiements recus (import core banking / saisie) : retard FIFO + taux de recuperation.';

CREATE INDEX idx_loan_payment_loan ON loan_payment (outstanding_loan_id, paid_on);

CREATE TABLE portfolio_followup (
    id           SERIAL PRIMARY KEY,
    member_id    INT NOT NULL REFERENCES member (id),
    visit_code   VARCHAR(4) CHECK (visit_code IN ('V1', 'V2', 'V3')),
    visit_on     DATE,
    officer_id   INT REFERENCES app_user (id),
    days_late    INT NOT NULL DEFAULT 0,
    signal       VARCHAR(80),
    signal_code  VARCHAR(40),
    visit_status VARCHAR(20) NOT NULL DEFAULT 'realisee'
                 CHECK (visit_status IN ('planifiee', 'realisee', 'manquee')),
    next_on      DATE,
    action_taken VARCHAR(160)
);
COMMENT ON TABLE portfolio_followup IS 'Visites V1-V3 et signaux d''alerte portefeuille (12 types FUCEC).';

CREATE TABLE par_indicator (
    id                   SERIAL PRIMARY KEY,
    agency_id            INT REFERENCES agency (id),
    as_of                DATE NOT NULL DEFAULT DATE '2026-09-13',
    par1_pct             NUMERIC(6, 2) NOT NULL DEFAULT 0,
    par30_pct            NUMERIC(6, 2) NOT NULL DEFAULT 0,
    par90_pct            NUMERIC(6, 2) NOT NULL DEFAULT 0,
    encours_brut         NUMERIC(16, 0) NOT NULL DEFAULT 0,
    restructured_amount  NUMERIC(16, 0) NOT NULL DEFAULT 0,
    computed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE par_indicator IS 'Snapshot PAR 1 / 30 / 90 par agence (calcule ou seed en maquette).';

CREATE TABLE recovery_case (
    id                SERIAL PRIMARY KEY,
    member_id         INT NOT NULL REFERENCES member (id),
    level             INT NOT NULL CHECK (level BETWEEN 1 AND 4),
    action            VARCHAR(120),
    owner_name        VARCHAR(80),
    opened_on         DATE,
    next_on           DATE,
    priority          VARCHAR(4),
    status            VARCHAR(20) NOT NULL DEFAULT 'ouvert'
                      CHECK (status IN ('ouvert', 'clos')),
    recovered_amount  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    last_action_on    DATE,
    closed_on         DATE
);
COMMENT ON TABLE recovery_case IS 'Dossier recouvrement 4 niveaux (relance ? contentieux).';

CREATE TABLE recovery_action (
    id                SERIAL PRIMARY KEY,
    case_id           INT NOT NULL REFERENCES recovery_case (id) ON DELETE CASCADE,
    action_on         DATE NOT NULL,
    action_type       VARCHAR(60) NOT NULL,
    note              TEXT,
    promise_on        DATE,
    promise_kept      BOOLEAN,
    amount_recovered  NUMERIC(14, 0) NOT NULL DEFAULT 0
);
COMMENT ON TABLE recovery_action IS 'Journal d''actions de recouvrement (M7).';

-- ---------------------------------------------------------------------------
-- ML consultatif (additif) — GUIDE_ML_BACKEND_DATA.md
-- ---------------------------------------------------------------------------
CREATE TABLE resilience_simulation (
    id                    SERIAL PRIMARY KEY,
    application_id        INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    scenario              VARCHAR(60) NOT NULL,
    requested_amount      NUMERIC(14, 0) NOT NULL,
    term_months           INT NOT NULL,
    horizon_months        INT NOT NULL,
    iterations            INT NOT NULL,
    random_seed           INT NOT NULL,
    model_version         VARCHAR(40) NOT NULL,
    incident_probability  NUMERIC(6, 5) NOT NULL,
    critical_month        INT,
    result_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by            INT REFERENCES app_user (id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE resilience_simulation IS 'Snapshots de simulation de resilience rejouables (seed + result_json).';

CREATE INDEX idx_resilience_application ON resilience_simulation (application_id, created_at DESC);
