-- Seeds metier DigiScore-WA — 12 profils + referentiel (dates = 2026-09-13)

INSERT INTO agency (code, name, city, topology) VALUES
    ('AGE-LME-01', 'COOPEC Demo Lome Centre', 'Lome', 'shared'),
    ('AGE-KPA-01', 'COOPEC Demo Kpalime', 'Kpalime', 'split');

INSERT INTO financial_institution (code, name, city, kind) VALUES
    ('IF-COOPEC-KPA', 'COOPEC Kpalime Union', 'Kpalime', 'coopec'),
    ('IF-COOPEC-SOK', 'COOPEC Sokode', 'Sokode', 'coopec'),
    ('IF-BTCI', 'BTCI Lome', 'Lome', 'banque'),
    ('IF-UTB', 'UTB', 'Lome', 'banque'),
    ('IF-WAGES', 'WAGES', 'Lome', 'microfinance');

INSERT INTO credit_product (code, label, min_amount, max_amount, max_term_months, indicative_rate, guarantor_threshold, min_guarantors, is_exceptional) VALUES
    ('PME-PMI', 'Crédit PME/PMI', 100000, 5000000, 24, 0.018, 2000000, 1, FALSE),
    ('SYSCOFOP', 'Crédit SYSCOFOP', 50000, 2000000, 12, 0.016, 2000000, 1, FALSE),
    ('VIR-SAL', 'Crédit virement salaire', 50000, 3000000, 18, 0.015, 2000000, 1, FALSE),
    ('EXC-10M', 'Crédit exceptionnel CIC', 5000000, 12000000, 36, 0.015, 2000000, 2, TRUE);

-- Plusieurs agents par agence (pas juste 'agent'/id=1) : sans ca, "mes dossiers"
-- et "base complete" affichent toujours le meme total sur la page Dossiers, vu
-- que credit_application.agent_id etait fige a 1 pour tout le monde. Ces comptes
-- ne sont pas connectables depuis l'ecran de connexion (ROLES n'a que agent/direct/cic)
-- : ce sont uniquement des proprietaires de dossiers pour la repartition du volume.
INSERT INTO app_user (login, full_name, role, agency_id, password_hash) VALUES
    ('agent', 'Ama Agent', 'agent', 1, '$2b$12$UAiMHdUPGagWNb96IlnlAOLVALfthuWjmV.Zps6Y3tFfDmP/YWC4q'),
    ('direct', 'Koffi Directeur', 'chef_agence', 1, '$2b$12$GNE/ytFWA6D2cXwAoQgJyuPPCZgc97UE6ryIJjSPHkrMbUB3J88Sy'),
    ('cic', 'Comite CIC', 'cic', 1, '$2b$12$pT0nytgemrYjKRsMcgpYA.moFRG5eYY0SuHpGMh63.4I3lWm6f30S'),
    ('agent2', 'Yawa Sena', 'agent', 1, '$2b$12$9OfpiTAhhmsHN9nRwDdFLOf7DiSl.eSp0MhZBA0Iu8Ypca.jMW1iC'),
    ('agent3', 'Kokou Amewou', 'agent', 2, '$2b$12$9OfpiTAhhmsHN9nRwDdFLOf7DiSl.eSp0MhZBA0Iu8Ypca.jMW1iC'),
    ('agent4', 'Afi Dogbe', 'agent', 2, '$2b$12$9OfpiTAhhmsHN9nRwDdFLOf7DiSl.eSp0MhZBA0Iu8Ypca.jMW1iC');

INSERT INTO member (external_code, last_name, first_name, gender, phone, area, agency_id, joined_on, status, marital_status, occupation) VALUES
    ('MEM-001', 'Mensah', 'Kodjo', 'M', '90111111', 'urbaine', 1, '2021-03-01', 'actif', 'marie', 'commercant'),
    ('MEM-002', 'Koffi', 'Ama', 'F', '90222222', 'urbaine', 1, '2020-06-15', 'actif', 'mariee', 'commercante'),
    ('MEM-003', 'Dossou', 'Yao', 'M', '90333333', 'urbaine', 1, '2019-01-10', 'actif', 'celibataire', 'moto-taxi'),
    ('MEM-004', 'Slim', 'Aisha', 'F', '90444444', 'urbaine', 1, '2026-07-20', 'actif', 'celibataire', 'vendeuse'),
    ('MEM-005', 'Agbeko', 'Jean', 'M', '90555555', 'rurale', 1, '2018-04-01', 'actif', 'marie', 'menuisier'),
    ('MEM-006', 'Sow', 'Fatou', 'F', '90666666', 'rurale', 2, '2022-01-15', 'actif', 'mariee', 'agricultrice'),
    ('MEM-007', 'Ablam', 'Kossi', 'M', '90777777', 'urbaine', 1, '2023-02-01', 'actif', 'marie', 'quincaillier'),
    ('MEM-008', 'Tetteh', 'Marie', 'F', '90888888', 'urbaine', 1, '2021-09-01', 'actif', 'mariee', 'commercante'),
    ('MEM-009', 'Gbeglo', 'Isaac', 'M', '90999999', 'urbaine', 1, '2016-05-01', 'actif', 'marie', 'grossiste'),
    ('MEM-010', 'Gele', 'Compte', 'M', '90000000', 'urbaine', 1, '2020-01-01', 'gele', 'celibataire', 'commercant'),
    ('MEM-011', 'Override', 'Demo', 'M', '90121212', 'urbaine', 1, '2019-08-01', 'actif', 'marie', 'couturier'),
    ('MEM-012', 'Extern', 'Bicok', 'F', '90343434', 'urbaine', 1, '2026-06-01', 'actif', 'celibataire', 'commercante');

INSERT INTO account (member_id, account_no, account_type, opened_on, status, current_balance) VALUES
    (1,  'CPT-001', 'epargne', '2021-03-01', 'actif', 450000),
    (2,  'CPT-002', 'epargne', '2020-06-15', 'actif', 280000),
    (3,  'CPT-003', 'epargne', '2019-01-10', 'actif', 40000),
    (4,  'CPT-004', 'epargne', '2026-07-20', 'actif', 35000),
    (5,  'CPT-005', 'epargne', '2018-04-01', 'actif', 620000),
    (6,  'CPT-006', 'epargne', '2022-01-15', 'actif', 180000),
    (7,  'CPT-007', 'epargne', '2023-02-01', 'actif', 150000),
    (8,  'CPT-008', 'epargne', '2021-09-01', 'actif', 90000),
    (9,  'CPT-009', 'epargne', '2016-05-01', 'actif', 1800000),
    (10, 'CPT-010', 'epargne', '2020-01-01', 'gele', 10000),
    (11, 'CPT-011', 'epargne', '2019-08-01', 'actif', 300000),
    (12, 'CPT-012', 'epargne', '2026-06-01', 'actif', 45000);

INSERT INTO savings_snapshot (account_id, as_of, avg_balance_3m, avg_balance_6m, avg_balance_12m) VALUES
    (1,  '2026-09-13', 420000, 400000, 380000),
    (2,  '2026-09-13', 260000, 250000, 240000),
    (3,  '2026-09-13', 35000, 40000, 50000),
    (4,  '2026-09-13', 30000, 20000, 15000),
    (5,  '2026-09-13', 600000, 580000, 550000),
    (6,  '2026-09-13', 160000, 150000, 140000),
    (7,  '2026-09-13', 140000, 130000, 120000),
    (8,  '2026-09-13', 80000, 85000, 90000),
    (9,  '2026-09-13', 1700000, 1600000, 1500000),
    (10, '2026-09-13', 8000, 9000, 10000),
    (11, '2026-09-13', 280000, 270000, 260000),
    (12, '2026-09-13', 40000, 30000, 20000);

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label) VALUES
    (1, '2026-08-01', 'depot', 80000, 'Depot boutique Mensah 08'),
    (1, '2026-07-01', 'depot', 82000, 'Depot boutique Mensah 07'),
    (1, '2026-06-01', 'depot', 75000, 'Depot boutique Mensah 06'),
    (1, '2026-05-12', 'depot', 71000, 'Depot boutique Mensah 05'),
    (1, '2026-04-03', 'retrait', 15000, 'Retrait stock Mensah'),
    (1, '2026-03-15', 'interet', 2100, 'Interet CPT-001'),
    (2, '2026-08-05', 'depot', 40000, 'Depot etal Ama'),
    (2, '2026-07-18', 'depot', 38000, 'Depot etal Ama 07'),
    (3, '2026-08-10', 'retrait', 20000, 'Retrait urgence Yao'),
    (3, '2026-06-02', 'depot', 12000, 'Depot moto-taxi Yao'),
    (5, '2026-08-01', 'depot', 100000, 'Depot menuiserie Agbeko'),
    (5, '2026-07-01', 'depot', 98000, 'Depot menuiserie Agbeko 07'),
    (5, '2026-05-20', 'depot', 90000, 'Depot menuiserie Agbeko 05'),
    (9, '2026-08-01', 'depot', 200000, 'Depot entrepot Gbeglo'),
    (9, '2026-06-11', 'depot', 180000, 'Depot entrepot Gbeglo 06'),
    (9, '2026-03-01', 'interet', 8500, 'Interet CPT-009'),
    (4, '2026-08-15', 'depot', 10000, 'Premier depot Slim');

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 1,
       DATE '2024-01-08' + (g * 21),
       CASE WHEN g % 11 = 0 THEN 'interet' WHEN g % 6 = 0 THEN 'retrait' ELSE 'depot' END,
       28000 + g * 1730,
       'Livret Mensah dense #' || g
FROM generate_series(0, 39) AS g;

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 5,
       DATE '2023-02-10' + (g * 28),
       CASE WHEN g % 10 = 0 THEN 'interet' WHEN g % 7 = 0 THEN 'retrait' ELSE 'depot' END,
       41000 + g * 2210,
       'Atelier Agbeko dense #' || g
FROM generate_series(0, 35) AS g;

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 9,
       DATE '2022-03-04' + (g * 18),
       CASE WHEN g % 12 = 0 THEN 'interet' WHEN g % 5 = 0 THEN 'retrait' ELSE 'depot' END,
       95000 + g * 4500,
       'Entrepot Gbeglo dense #' || g
FROM generate_series(0, 47) AS g;

INSERT INTO past_credit (member_id, amount, term_months, granted_on, closed_on, status, late_count, max_days_late, source, institution_id) VALUES
    (1, 400000, 12, '2024-01-10', '2025-01-10', 'solde', 0, 0, 'interne', NULL),
    (1, 600000, 12, '2025-03-01', '2026-03-01', 'solde', 0, 0, 'interne', NULL),
    (2, 500000, 12, '2024-06-01', '2025-06-01', 'solde', 1, 5, 'interne', NULL),
    (3, 350000, 10, '2025-01-01', NULL, 'impaye', 4, 45, 'interne', NULL),
    (7, 250000, 8, '2025-04-01', '2026-01-01', 'solde', 2, 18, 'interne', NULL),
    (8, 200000, 6, '2025-02-01', '2025-08-01', 'solde', 1, 8, 'interne', NULL),
    (9, 2500000, 24, '2023-01-01', '2025-01-01', 'solde', 0, 0, 'interne', NULL),
    (9, 3000000, 24, '2025-02-01', NULL, 'en_cours', 0, 0, 'interne', NULL),
    (11, 300000, 10, '2024-02-01', '2025-01-01', 'solde', 0, 0, 'interne', NULL),
    (12, 280000, 12, '2024-02-01', '2025-02-01', 'solde', 0, 0, 'externe',
        (SELECT id FROM financial_institution WHERE code = 'IF-BTCI'));

INSERT INTO incident (member_id, incident_type, occurred_on, severity, detail) VALUES
    (3, 'retard', '2026-07-01', 'grave', 'Promesse non tenue + 45 j'),
    (3, 'contentieux', '2026-08-15', 'grave', 'Niveau recouvrement 3'),
    (7, 'retard', '2025-09-01', 'moyenne', '18 jours sur credit precedent');

INSERT INTO member_guarantee (member_id, kind, value_amount) VALUES
    (1, 'Stock commerce', 350000),
    (2, 'Equipement boutique', 200000),
    (5, 'Terrain familial', 800000),
    (9, 'Fonds de commerce + vehicule', 6000000);

INSERT INTO external_account (member_id, institution_id, account_no_mask, opened_on, status, current_balance) VALUES
    (12, (SELECT id FROM financial_institution WHERE code = 'IF-BTCI'), 'EXT-TCI-0000012', '2024-03-01', 'actif', 95000);

INSERT INTO external_account_movement (account_id, moved_on, movement_type, amount, label) VALUES
    (1, '2026-08-02', 'depot', 25000, 'Depot salaire BTCI Extern'),
    (1, '2026-07-02', 'depot', 24000, 'Depot salaire BTCI Extern 07'),
    (1, '2026-06-02', 'retrait', 8000, 'Retrait BTCI Extern'),
    (1, '2025-12-15', 'depot', 30000, 'Depot fin annee BTCI');

INSERT INTO external_savings_snapshot (account_id, as_of, avg_balance_3m, avg_balance_6m, avg_balance_12m) VALUES
    (1, '2026-09-13', 90000, 85000, 70000);

INSERT INTO bic_consent (member_id, signed_on, status, scan_path) VALUES
    (1, '2026-09-01', 'signe', 'seed/bic_consent_001.pdf'),
    (2, '2026-09-01', 'signe', 'seed/bic_consent_002.pdf'),
    (9, '2026-09-01', 'signe', 'seed/bic_consent_009.pdf'),
    (12, '2026-09-10', 'signe', 'seed/bic_consent_012.pdf');

INSERT INTO bic_report (member_id, external_credit_count, bic_incident_count, indebtedness_summary, source) VALUES
    (1, 0, 0, 'RAS', 'simulate'),
    (2, 1, 0, 'Credit conso cloture autre IMF', 'simulate'),
    (3, 2, 2, 'Deux incidents BIC', 'simulate'),
    (12, 1, 0, 'Credit banque 2024 solde', 'simulate');

INSERT INTO credit_application (member_id, product_id, agent_id, agency_id, purpose, requested_amount, term_months, status, tax_status, has_external_credits, external_proofs_ok, esg_exclusion) VALUES
    (1,  1, 1, 1, 'Renouvellement stock boutique', 500000, 12, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (2,  1, 1, 1, 'Agrandissement etal', 2500000, 12, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (3,  1, 1, 1, 'Relance activite', 300000, 10, 'brouillon', 'a_verifier', FALSE, TRUE, FALSE),
    (4,  1, 1, 1, 'Premier credit commerce', 400000, 8, 'brouillon', 'non_fourni', FALSE, FALSE, FALSE),
    (5,  1, 1, 1, 'Petit materiel', 250000, 10, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (6,  2, 1, 2, 'Intrants campagne', 600000, 10, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (7,  1, 1, 1, 'Fonds de roulement', 450000, 12, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (8,  1, 1, 1, 'Stock trop lourd vs CAF', 800000, 12, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (9,  4, 1, 1, 'Extension entrepot (exceptionnel)', 10000000, 24, 'brouillon', 'en_regle', FALSE, TRUE, FALSE),
    (11, 1, 1, 1, 'Dossier override demo', 400000, 10, 'soumis_chef', 'en_regle', FALSE, TRUE, FALSE),
    (12, 1, 1, 1, 'Credit avec preuves externes', 350000, 10, 'brouillon', 'en_regle', TRUE, TRUE, FALSE);

-- Sans ca, applied_at retombe sur DEFAULT NOW() pour les 11 lignes : meme
-- instant pour toutes, donc aucune courbe "dossiers crees par semaine"
-- possible cote dashboard agent. Etale sur les dernieres semaines.
UPDATE credit_application
SET applied_at = NOW() - ((member_id * 6) || ' days')::interval
WHERE member_id BETWEEN 1 AND 12;

INSERT INTO income_expense (application_id, revenue, cogs, operating_costs, financial_income, main_activity_income, secondary_income, spouse_income, personal_income, rent_cost, school_cost, existing_debt_service, family_cost, equity, total_debt, total_assets, current_assets, current_liabilities, avg_inventory, net_income, income_proof_level, expense_proof_level) VALUES
    (1,  3600000, 1800000, 600000, 20000, 1200000, 100000, 80000, 200000, 60000, 40000, 0, 80000, 800000, 200000, 1500000, 700000, 250000, 300000, 400000, 'N3', 'N2'),
    (2,  2800000, 1500000, 500000, 10000, 800000, 50000, 40000, 150000, 50000, 30000, 20000, 70000, 500000, 300000, 1100000, 500000, 280000, 250000, 200000, 'N2', 'N2'),
    (3,  1200000, 800000, 350000, 0, 200000, 0, 0, 80000, 40000, 20000, 80000, 50000, 80000, 400000, 300000, 120000, 180000, 90000, 20000, 'N1', 'N1'),
    (4,  900000, 500000, 200000, 0, 200000, 0, 0, 60000, 25000, 10000, 0, 30000, 50000, 80000, 200000, 80000, 60000, 40000, 40000, 'N1', 'N1'),
    (5,  1800000, 700000, 400000, 15000, 700000, 80000, 0, 180000, 20000, 30000, 0, 60000, 900000, 150000, 1400000, 400000, 120000, 150000, 250000, 'N2', 'N2'),
    (6,  2000000, 900000, 350000, 0, 650000, 40000, 20000, 120000, 15000, 25000, 0, 50000, 400000, 220000, 900000, 350000, 200000, 200000, 180000, 'N2', 'N2'),
    (7,  1500000, 800000, 400000, 0, 400000, 30000, 20000, 100000, 40000, 25000, 15000, 50000, 220000, 280000, 600000, 250000, 200000, 160000, 80000, 'N2', 'N1'),
    (8,  800000, 550000, 300000, 0, 180000, 0, 0, 50000, 35000, 20000, 40000, 40000, 60000, 350000, 250000, 90000, 160000, 70000, -20000, 'N1', 'N1'),
    (9,  18000000, 8000000, 2500000, 200000, 5500000, 400000, 200000, 800000, 150000, 80000, 200000, 200000, 8000000, 3500000, 18000000, 6000000, 2000000, 2500000, 2200000, 'N3', 'N3'),
    (10, 2200000, 1100000, 450000, 10000, 650000, 40000, 30000, 150000, 45000, 25000, 0, 60000, 400000, 180000, 900000, 400000, 180000, 180000, 180000, 'N2', 'N2'),
    (11, 1400000, 700000, 300000, 0, 400000, 20000, 0, 100000, 30000, 20000, 0, 40000, 200000, 100000, 500000, 220000, 120000, 120000, 120000, 'N2', 'N2');

INSERT INTO wealth (application_id, productive_assets, non_productive_assets, formal_liabilities, informal_liabilities, signal_revenue_erosion, signal_margin, signal_receivables, signal_payables, signal_net_worth) VALUES
    (1, 700000, 200000, 150000, 50000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (2, 500000, 150000, 250000, 50000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (3, 120000, 40000, 300000, 100000, TRUE, TRUE, FALSE, TRUE, TRUE),
    (4, 80000, 20000, 40000, 20000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (5, 900000, 400000, 100000, 50000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (6, 400000, 150000, 180000, 40000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (7, 280000, 80000, 200000, 80000, FALSE, TRUE, FALSE, TRUE, FALSE),
    (8, 90000, 30000, 280000, 70000, TRUE, TRUE, TRUE, FALSE, TRUE),
    (9, 9000000, 2000000, 3000000, 500000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (10, 400000, 120000, 120000, 40000, FALSE, FALSE, FALSE, FALSE, FALSE),
    (11, 250000, 80000, 80000, 20000, FALSE, FALSE, FALSE, FALSE, FALSE);

INSERT INTO activity (application_id, activity_type, description, seniority_months, location_area, is_seasonal, proof_level) VALUES
    (1, 'tertiaire', 'Boutique vivres', 60, 'Lome', FALSE, 'N3'),
    (2, 'tertiaire', 'Tissus', 48, 'Lome', FALSE, 'N2'),
    (3, 'tertiaire', 'Moto-taxi + petit commerce', 24, 'Lome', FALSE, 'N1'),
    (4, 'tertiaire', 'Tablette rue', 8, 'Lome', FALSE, 'N1'),
    (5, 'secondaire', 'Atelier menuiserie', 96, 'Agoe', FALSE, 'N2'),
    (6, 'primaire', 'Mais / soja', 40, 'Kpalime', TRUE, 'N2'),
    (7, 'tertiaire', 'Quincaillerie', 30, 'Lome', FALSE, 'N2'),
    (8, 'tertiaire', 'Alimentation', 18, 'Lome', FALSE, 'N1'),
    (9, 'tertiaire', 'Grossiste cereales', 120, 'Lome', FALSE, 'N3'),
    (10, 'tertiaire', 'Pieces auto', 40, 'Lome', FALSE, 'N2'),
    (11, 'secondaire', 'Couture', 10, 'Lome', FALSE, 'N2');

INSERT INTO household (application_id, household_size, housing, dependents) VALUES
    (1, 5, 'locataire', 3), (2, 4, 'locataire', 2), (3, 3, 'locataire', 1),
    (4, 2, 'chez_parents', 0), (5, 6, 'proprietaire', 4), (6, 5, 'proprietaire', 3),
    (7, 4, 'locataire', 2), (8, 4, 'locataire', 2), (9, 7, 'proprietaire', 4),
    (10, 4, 'locataire', 2), (11, 3, 'locataire', 1);

INSERT INTO economic_model (application_id, client_segments, product_service, avg_price, unit_variable_cost, monthly_fixed_cost, sales_rhythm) VALUES
    (1, 'Menages quartier', 'Vivres', 500, 280, 80000, 'quotidien'),
    (6, 'Grossistes locaux', 'Mais / soja', 180, 90, 40000, 'saisonnier'),
    (9, 'Detaillants region', 'Cereales vrac', 12000, 8000, 350000, 'hebdomadaire');

INSERT INTO market (application_id, high_season, low_season, daily_volume, competitor_count, single_outlet_dependency, proof_level) VALUES
    (1, 'dec-jan', 'juin-aout', 40, 6, FALSE, 'N2'),
    (6, 'oct-dec', 'juin-aout', 8, 3, TRUE, 'N2'),
    (9, 'toute_annee', 'juin', 25, 4, FALSE, 'N3');

-- Tresorerie a l'echelle reelle de chaque dossier (revenue/cogs/operating_costs
-- d'income_expense), pas un flux plat identique pour tous : un flux uniforme a
-- 200k/160k etait ~7x trop petit pour le dossier 9 (CA 18M/an) et surestimait
-- le dossier 4 (CA 900k/an), ce qui rendait le simulateur de resilience
-- structurellement voue a l'echec (creux < 0 des le mois 1) independamment du
-- scenario choisi. Bruit mensuel deterministe + creux saisonnier (dossier 6,
-- agriculture) : jamais un lissage plat du CA annuel (cf. commentaire schema.sql).
INSERT INTO monthly_cashflow (application_id, month_no, period_month, inflow, outflow)
SELECT
    ie.application_id, m, make_date(2025, m, 1),
    ROUND(
        (ie.revenue::numeric / 12)
        * CASE
            WHEN a.is_seasonal AND m IN (6, 7, 8) THEN 0.35
            ELSE 0.9 + ((ie.application_id * m) % 5) / 25.0
          END
    ),
    ROUND(
        ((ie.cogs + ie.operating_costs)::numeric / 12)
        * CASE
            WHEN a.is_seasonal AND m IN (6, 7, 8) THEN 1.3
            ELSE 0.9 + ((ie.application_id * m * 3) % 5) / 25.0
          END
    )
FROM income_expense ie
JOIN activity a ON a.application_id = ie.application_id
CROSS JOIN generate_series(1, 12) AS m
WHERE ie.application_id BETWEEN 1 AND 11;

INSERT INTO application_guarantee (application_id, kind, value_amount, proof_level) VALUES
    (1, 'Stock', 350000, 'N2'),
    (2, 'Etal', 180000, 'N2'),
    (5, 'Outillage', 400000, 'N2'),
    (9, 'Entrepot + vehicule', 8000000, 'N3');

INSERT INTO guarantor (last_name, first_name, phone, relationship, member_id) VALUES
    ('Mensah', 'Paul', '91111111', 'frere', 1),
    ('Koffi', 'Grace', '92222222', 'epouse', NULL);

INSERT INTO application_guarantor (application_id, guarantor_id, guarantee_type, pledged_amount) VALUES
    (9, 1, 'solidaire', 5000000),
    (9, 2, 'solidaire', 5000000);

INSERT INTO guarantor_review (application_guarantor_id, income, expenses, relay_caf, relay_rcsd, relay_score, eligible, reason) VALUES
    (1, 900000, 300000, 600000, 1.80, 78, TRUE, 'Capacite de relais suffisante'),
    (2, 700000, 250000, 450000, 1.60, 72, TRUE, 'OK');

INSERT INTO supporting_document (application_id, document_type, file_path, ocr_quality, status) VALUES
    (1, 'CNI', 'seed/cni_001.jpg', 'ok', 'valide'),
    (1, 'FISCAL', 'seed/fiscal_001.jpg', 'ok', 'valide'),
    (11, 'RELEVE', 'seed/releve_012.jpg', 'ok', 'valide'),
    (11, 'CARNET', 'seed/carnet_012.jpg', 'ok', 'valide'),
    (11, 'BIC', 'seed/bic_012.jpg', 'ok', 'valide'),
    (11, 'FISCAL', 'seed/fiscal_012.jpg', 'ok', 'valide');

INSERT INTO par_indicator (agency_id, par30_pct, par90_pct) VALUES (1, 6.2, 2.1), (2, 8.4, 3.5);

INSERT INTO portfolio_followup (member_id, visit_code, visit_on, officer_id, days_late, signal) VALUES
    (3, 'V2', '2026-08-20', 1, 45, 'Absence aux visites'),
    (6, 'V1', '2026-09-01', 1, 0, 'Baisse de stock saisonniere');

INSERT INTO recovery_case (member_id, level, action, owner_name, opened_on, next_on) VALUES
    (3, 3, 'Relance chef d''agence', 'Koffi Chef', '2026-08-15', '2026-09-20');

INSERT INTO recovery_action (case_id, action_on, action_type, note) VALUES
    (1, '2026-08-16', 'appel', 'Promesse de paiement non tenue'),
    (1, '2026-08-28', 'visite', 'Absent au domicile');

INSERT INTO outstanding_loan (member_id, application_id, principal, outstanding, days_late, status, disbursed_on, due_on, observed_on) VALUES
    (3, NULL, 350000, 210000, 45, 'impaye', '2025-01-01', '2025-11-01', '2026-09-13'),
    (9, NULL, 3000000, 2200000, 0, 'en_cours', '2025-02-01', '2027-02-01', '2026-09-13');

INSERT INTO digiscore_member_map (member_id, external_code, source_system)
SELECT id, external_code, 'core_stub' FROM member;

INSERT INTO audit_log (application_id, user_id, action, detail) VALUES
    (10, 1, 'soumission', 'Dossier override soumis au chef');
