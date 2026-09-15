#!/usr/bin/env python3
"""Charge data/synthetic/volume/*.csv dans Postgres (après schema + seed 12 profils)."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

DSN = os.getenv("DATABASE_URL", "postgresql://digiscore:digiscore@localhost:5432/digiscore")
VOL = Path(os.getenv("VOLUME_DIR", "data/synthetic/volume"))


def copy_csv(cur, table: str, columns: str, path: Path) -> None:
    sql = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '\\N')"
    with path.open("r", encoding="utf-8") as f:
        with cur.copy(sql) as cp:
            while True:
                chunk = f.read(1024 * 256)
                if not chunk:
                    break
                cp.write(chunk)
    # Sans ANALYZE, une table (temp ou definitive) qui vient d'etre remplie par
    # COPY n'a pas de statistiques : le planificateur sous-estime son cardinal
    # (heuristique par defaut ~1000 lignes) et peut choisir une boucle imbriquee
    # sans index sur les JOIN qui suivent — des millions de lignes deviennent
    # alors des heures au lieu de secondes. Coute quelques ms, evite ce piege
    # a chaque INSERT ... SELECT ... JOIN stg_* qui suit un COPY.
    cur.execute(f"ANALYZE {table}")


def _exists(name: str) -> Path | None:
    path = VOL / name
    return path if path.exists() else None


def _already_loaded(cur) -> bool:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seed_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute("SELECT value FROM seed_meta WHERE key = 'volume_loaded'")
    row = cur.fetchone()
    if row and row[0] == "v2":
        return True
    cur.execute("SELECT COUNT(*) FROM member WHERE external_code LIKE 'VOL-%'")
    n_vol = (cur.fetchone() or (0,))[0]
    if n_vol:
        raise SystemExit(
            "Volume v1 (ou incomplet) déjà en base. Recharge unique v2 : "
            "docker compose down -v && docker compose up -d "
            "(laptop : VOLUME_MEMBERS=5000)."
        )
    return False


def _mark_loaded(cur) -> None:
    cur.execute(
        """
            INSERT INTO seed_meta (key, value) VALUES ('volume_loaded', 'v2')
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, loaded_at = NOW()
        """
    )


def _load_member_join(
    cur,
    stg: str,
    stg_ddl: str,
    columns: str,
    csv_name: str,
    insert_sql: str,
    label: str,
) -> None:
    path = _exists(csv_name)
    if not path:
        print(f"{label} skip (pas de {csv_name})")
        return
    cur.execute(stg_ddl)
    copy_csv(cur, stg, columns, path)
    cur.execute(insert_sql)
    print(label, cur.rowcount)
    # La table reelle qui vient de recevoir l'INSERT...SELECT n'a pas encore
    # de statistiques a jour (voir commentaire de copy_csv) : un JOIN suivant
    # contre elle (ex. account_movement -> account) choisirait sinon un plan
    # catastrophique. ANALYZE global (pas de table precise ici, cout marginal
    # face au temps perdu par un mauvais plan).
    cur.execute("ANALYZE")


def main() -> None:
    if not (VOL / "member.csv").exists():
        raise SystemExit("CSV absents. Lance d'abord: python backend/db/seed/generate_volume_csv.py")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            if _already_loaded(cur):
                print("Volume déjà chargé (seed_meta / VOL-*), skip COPY.")
                conn.commit()
                return

            cur.execute(
                """
                CREATE TEMP TABLE stg_member (
                    external_code VARCHAR(40), last_name VARCHAR(80), first_name VARCHAR(80),
                    gender CHAR(1), birth_date DATE, phone VARCHAR(20), address VARCHAR(200),
                    area VARCHAR(20), agency_id INT, joined_on DATE, status VARCHAR(20),
                    marital_status VARCHAR(40), occupation VARCHAR(80)
                )
                """
            )
            copy_csv(
                cur,
                "stg_member",
                "external_code,last_name,first_name,gender,birth_date,phone,address,area,agency_id,joined_on,status,marital_status,occupation",
                VOL / "member.csv",
            )
            cur.execute(
                """
                INSERT INTO member (external_code, last_name, first_name, gender, birth_date, phone, address, area, agency_id, joined_on, status, marital_status, occupation)
                SELECT * FROM stg_member
                ON CONFLICT (external_code) DO NOTHING
                """
            )
            print("members", cur.rowcount)

            cur.execute(
                """
                CREATE TEMP TABLE stg_account (
                    external_code VARCHAR(40), account_no VARCHAR(30), account_type VARCHAR(20),
                    opened_on DATE, status VARCHAR(20), current_balance NUMERIC
                )
                """
            )
            copy_csv(cur, "stg_account", "external_code,account_no,account_type,opened_on,status,current_balance", VOL / "account.csv")
            cur.execute(
                """
                INSERT INTO account (member_id, account_no, account_type, opened_on, status, current_balance)
                SELECT m.id, s.account_no, s.account_type, s.opened_on, s.status, s.current_balance
                FROM stg_account s
                JOIN member m ON m.external_code = s.external_code
                ON CONFLICT (account_no) DO NOTHING
                """
            )
            print("accounts", cur.rowcount)

            snap = _exists("savings_snapshot.csv")
            if snap:
                cur.execute(
                    """
                    CREATE TEMP TABLE stg_snap (
                        account_no VARCHAR(30), as_of DATE,
                        avg_balance_3m NUMERIC, avg_balance_6m NUMERIC, avg_balance_12m NUMERIC
                    )
                    """
                )
                copy_csv(cur, "stg_snap", "account_no,as_of,avg_balance_3m,avg_balance_6m,avg_balance_12m", snap)
                cur.execute(
                    """
                    INSERT INTO savings_snapshot (account_id, as_of, avg_balance_3m, avg_balance_6m, avg_balance_12m)
                    SELECT a.id, s.as_of, s.avg_balance_3m, s.avg_balance_6m, s.avg_balance_12m
                    FROM stg_snap s
                    JOIN account a ON a.account_no = s.account_no
                    """
                )
                print("snapshots", cur.rowcount)

            mvt = _exists("account_movement.csv")
            if mvt:
                cur.execute(
                    "CREATE TEMP TABLE stg_mvt (account_no VARCHAR(30), moved_on DATE, movement_type VARCHAR(20), amount NUMERIC, label VARCHAR(160))"
                )
                copy_csv(cur, "stg_mvt", "account_no,moved_on,movement_type,amount,label", mvt)
                cur.execute(
                    """
                    INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
                    SELECT a.id, s.moved_on, s.movement_type, s.amount, s.label
                    FROM stg_mvt s JOIN account a ON a.account_no = s.account_no
                    """
                )
                print("movements", cur.rowcount)

            _load_member_join(
                cur,
                "stg_pc",
                """
                CREATE TEMP TABLE stg_pc (
                    external_code VARCHAR(40), institution_code VARCHAR(30), amount NUMERIC, term_months INT, granted_on DATE,
                    closed_on DATE, status VARCHAR(20), late_count INT, max_days_late INT, source VARCHAR(20)
                )
                """,
                "external_code,institution_code,amount,term_months,granted_on,closed_on,status,late_count,max_days_late,source",
                "past_credit.csv",
                """
                INSERT INTO past_credit (member_id, institution_id, amount, term_months, granted_on, closed_on, status, late_count, max_days_late, source)
                SELECT m.id, fi.id, s.amount, s.term_months, s.granted_on, s.closed_on, s.status, s.late_count, s.max_days_late, s.source
                FROM stg_pc s
                JOIN member m ON m.external_code = s.external_code
                LEFT JOIN financial_institution fi ON fi.code = NULLIF(s.institution_code, '')
                """,
                "past_credit",
            )

            _load_member_join(
                cur,
                "stg_inc",
                "CREATE TEMP TABLE stg_inc (external_code VARCHAR(40), incident_type VARCHAR(40), occurred_on DATE, severity VARCHAR(20), detail TEXT)",
                "external_code,incident_type,occurred_on,severity,detail",
                "incident.csv",
                """
                INSERT INTO incident (member_id, incident_type, occurred_on, severity, detail)
                SELECT m.id, s.incident_type, s.occurred_on, s.severity, s.detail
                FROM stg_inc s JOIN member m ON m.external_code = s.external_code
                """,
                "incidents",
            )

            _load_member_join(
                cur,
                "stg_gar",
                "CREATE TEMP TABLE stg_gar (external_code VARCHAR(40), kind VARCHAR(80), value_amount NUMERIC)",
                "external_code,kind,value_amount",
                "member_guarantee.csv",
                """
                INSERT INTO member_guarantee (member_id, kind, value_amount)
                SELECT m.id, s.kind, s.value_amount
                FROM stg_gar s JOIN member m ON m.external_code = s.external_code
                """,
                "member_guarantee",
            )

            _load_member_join(
                cur,
                "stg_bic_c",
                "CREATE TEMP TABLE stg_bic_c (external_code VARCHAR(40), signed_on DATE, status VARCHAR(20), scan_path VARCHAR(255))",
                "external_code,signed_on,status,scan_path",
                "bic_consent.csv",
                """
                INSERT INTO bic_consent (member_id, signed_on, status, scan_path)
                SELECT m.id, s.signed_on, s.status, s.scan_path
                FROM stg_bic_c s JOIN member m ON m.external_code = s.external_code
                """,
                "bic_consent",
            )

            _load_member_join(
                cur,
                "stg_bic_r",
                """
                CREATE TEMP TABLE stg_bic_r (
                    external_code VARCHAR(40), external_credit_count INT, bic_incident_count INT,
                    indebtedness_summary TEXT, source VARCHAR(20)
                )
                """,
                "external_code,external_credit_count,bic_incident_count,indebtedness_summary,source",
                "bic_report.csv",
                """
                INSERT INTO bic_report (member_id, external_credit_count, bic_incident_count, indebtedness_summary, source)
                SELECT m.id, s.external_credit_count, s.bic_incident_count, s.indebtedness_summary, s.source
                FROM stg_bic_r s JOIN member m ON m.external_code = s.external_code
                """,
                "bic_report",
            )

            _load_member_join(
                cur,
                "stg_map",
                "CREATE TEMP TABLE stg_map (external_code VARCHAR(40), source_system VARCHAR(40))",
                "external_code,source_system",
                "digiscore_member_map.csv",
                """
                INSERT INTO digiscore_member_map (member_id, external_code, source_system)
                SELECT m.id, s.external_code, s.source_system
                FROM stg_map s JOIN member m ON m.external_code = s.external_code
                """,
                "digiscore_member_map",
            )

            ext_acc = _exists("external_account.csv")
            if ext_acc:
                cur.execute(
                    """
                    CREATE TEMP TABLE stg_ext_acc (
                        external_code VARCHAR(40), institution_code VARCHAR(30),
                        account_no_mask VARCHAR(40), opened_on DATE, status VARCHAR(20), current_balance NUMERIC
                    )
                    """
                )
                copy_csv(
                    cur,
                    "stg_ext_acc",
                    "external_code,institution_code,account_no_mask,opened_on,status,current_balance",
                    ext_acc,
                )
                cur.execute(
                    """
                    INSERT INTO external_account (member_id, institution_id, account_no_mask, opened_on, status, current_balance)
                    SELECT m.id, fi.id, s.account_no_mask, s.opened_on, s.status, s.current_balance
                    FROM stg_ext_acc s
                    JOIN member m ON m.external_code = s.external_code
                    JOIN financial_institution fi ON fi.code = s.institution_code
                    """
                )
                print("external_account", cur.rowcount)
                em = _exists("external_account_movement.csv")
                if em:
                    cur.execute(
                        "CREATE TEMP TABLE stg_ext_mvt (account_no_mask VARCHAR(40), moved_on DATE, movement_type VARCHAR(20), amount NUMERIC, label VARCHAR(160))"
                    )
                    copy_csv(cur, "stg_ext_mvt", "account_no_mask,moved_on,movement_type,amount,label", em)
                    cur.execute(
                        """
                        INSERT INTO external_account_movement (account_id, moved_on, movement_type, amount, label)
                        SELECT a.id, s.moved_on, s.movement_type, s.amount, s.label
                        FROM stg_ext_mvt s JOIN external_account a ON a.account_no_mask = s.account_no_mask
                        """
                    )
                    print("external_movements", cur.rowcount)
                es = _exists("external_savings_snapshot.csv")
                if es:
                    cur.execute(
                        "CREATE TEMP TABLE stg_ext_snap (account_no_mask VARCHAR(40), as_of DATE, avg_balance_3m NUMERIC, avg_balance_6m NUMERIC, avg_balance_12m NUMERIC)"
                    )
                    copy_csv(cur, "stg_ext_snap", "account_no_mask,as_of,avg_balance_3m,avg_balance_6m,avg_balance_12m", es)
                    cur.execute(
                        """
                        INSERT INTO external_savings_snapshot (account_id, as_of, avg_balance_3m, avg_balance_6m, avg_balance_12m)
                        SELECT a.id, s.as_of, s.avg_balance_3m, s.avg_balance_6m, s.avg_balance_12m
                        FROM stg_ext_snap s JOIN external_account a ON a.account_no_mask = s.account_no_mask
                        """
                    )
                    print("external_snapshots", cur.rowcount)

            app_csv = _exists("credit_application.csv")
            if app_csv:
                cur.execute(
                    """
                    CREATE TEMP TABLE stg_app (
                        app_ref VARCHAR(20), external_code VARCHAR(40), product_id INT,
                        purpose VARCHAR(200), requested_amount NUMERIC, term_months INT,
                        status VARCHAR(30), tax_status VARCHAR(20),
                        has_external_credits BOOLEAN, external_proofs_ok BOOLEAN
                    )
                    """
                )
                copy_csv(
                    cur,
                    "stg_app",
                    "app_ref,external_code,product_id,purpose,requested_amount,term_months,status,tax_status,has_external_credits,external_proofs_ok",
                    app_csv,
                )
                cur.execute("CREATE TEMP TABLE map_app (app_ref VARCHAR(20) PRIMARY KEY, application_id INT NOT NULL)")
                cur.execute(
                    """
                    WITH numbered AS (
                        SELECT s.*, m.id AS member_id, m.agency_id,
                               row_number() OVER (ORDER BY s.app_ref) AS rn
                        FROM stg_app s
                        JOIN member m ON m.external_code = s.external_code
                    ),
                    agents AS (
                        SELECT id, agency_id,
                               row_number() OVER (PARTITION BY agency_id ORDER BY id) AS rn,
                               count(*) OVER (PARTITION BY agency_id) AS n
                        FROM app_user WHERE role = 'agent'
                    ),
                    -- Un agent par membre (pas par dossier) : le meme membre garde
                    -- le meme agent d'un dossier a l'autre, comme un vrai portefeuille
                    -- de clients attitres. member_id % 97 avant le %n : l'agence est
                    -- deja assignee via (index % 2) cote generateur, donc member_id %
                    -- 2 (ou tout petit modulo correle a 2) est CONSTANT au sein d'une
                    -- meme agence et enverrait 100% des dossiers sur un seul agent.
                    -- 97 est premier et sans rapport avec ce pas de 2, ce qui casse
                    -- la correlation et repartit vraiment entre les agents.
                    picked AS (
                        SELECT n.*, a.id AS agent_id
                        FROM numbered n
                        JOIN agents a
                          ON a.agency_id = n.agency_id
                         AND a.rn = ((n.member_id % 97) % a.n) + 1
                    ),
                    ins AS (
                        INSERT INTO credit_application (
                            member_id, product_id, agent_id, agency_id, purpose,
                            requested_amount, term_months, status, tax_status,
                            has_external_credits, external_proofs_ok, applied_at
                        )
                        -- Sans ca, applied_at retombe sur DEFAULT NOW() pour les
                        -- 20 000 lignes : meme instant pour tout le monde, donc
                        -- aucune courbe "dossiers crees par semaine" possible cote
                        -- dashboard agent. Etale sur ~90 jours, deterministe (pas
                        -- d'appel random() ici).
                        SELECT member_id, product_id, agent_id, agency_id, purpose,
                               requested_amount, term_months, status, tax_status,
                               has_external_credits, external_proofs_ok,
                               NOW() - (((member_id * 37) % 90) || ' days')::interval
                                     - (((member_id * 13) % 24) || ' hours')::interval
                        FROM picked
                        ORDER BY rn
                        RETURNING id
                    ),
                    ins_n AS (
                        SELECT id, row_number() OVER (ORDER BY id) AS rn FROM ins
                    )
                    INSERT INTO map_app (app_ref, application_id)
                    SELECT n.app_ref, i.id
                    FROM numbered n
                    JOIN ins_n i ON i.rn = n.rn
                    """
                )
                print("applications", cur.rowcount)
                # credit_application et map_app viennent d'etre remplies par un
                # INSERT...SELECT, pas un COPY : meme piege de stats perimees
                # que dans copy_csv, avant les nombreux JOIN sur map_app qui suivent.
                cur.execute("ANALYZE")

                ie = _exists("income_expense.csv")
                if ie:
                    cur.execute(
                        """
                        CREATE TEMP TABLE stg_ie (
                            app_ref VARCHAR(20), revenue NUMERIC, cogs NUMERIC, operating_costs NUMERIC,
                            financial_income NUMERIC, personal_income NUMERIC, family_cost NUMERIC,
                            existing_debt_service NUMERIC, equity NUMERIC, total_debt NUMERIC,
                            total_assets NUMERIC, current_assets NUMERIC, current_liabilities NUMERIC,
                            avg_inventory NUMERIC, net_income NUMERIC,
                            income_proof_level CHAR(2), expense_proof_level CHAR(2)
                        )
                        """
                    )
                    copy_csv(
                        cur,
                        "stg_ie",
                        "app_ref,revenue,cogs,operating_costs,financial_income,personal_income,family_cost,existing_debt_service,equity,total_debt,total_assets,current_assets,current_liabilities,avg_inventory,net_income,income_proof_level,expense_proof_level",
                        ie,
                    )
                    cur.execute(
                        """
                        INSERT INTO income_expense (
                            application_id, revenue, cogs, operating_costs, financial_income,
                            personal_income, family_cost, existing_debt_service, equity, total_debt,
                            total_assets, current_assets, current_liabilities, avg_inventory,
                            net_income, income_proof_level, expense_proof_level
                        )
                        SELECT m.application_id, s.revenue, s.cogs, s.operating_costs, s.financial_income,
                               s.personal_income, s.family_cost, s.existing_debt_service, s.equity, s.total_debt,
                               s.total_assets, s.current_assets, s.current_liabilities, s.avg_inventory,
                               s.net_income, s.income_proof_level, s.expense_proof_level
                        FROM stg_ie s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("income_expense", cur.rowcount)

                wealth = _exists("wealth.csv")
                if wealth:
                    cur.execute(
                        """
                        CREATE TEMP TABLE stg_wealth (
                            app_ref VARCHAR(20), productive_assets NUMERIC, non_productive_assets NUMERIC,
                            formal_liabilities NUMERIC, informal_liabilities NUMERIC,
                            prob_erosion BOOLEAN, signal_margin BOOLEAN, signal_receivables BOOLEAN,
                            signal_payables BOOLEAN, signal_net_worth BOOLEAN
                        )
                        """
                    )
                    # CSV header: signal_revenue_erosion — mapped positionally
                    copy_csv(
                        cur,
                        "stg_wealth",
                        "app_ref,productive_assets,non_productive_assets,formal_liabilities,informal_liabilities,prob_erosion,signal_margin,signal_receivables,signal_payables,signal_net_worth",
                        wealth,
                    )
                    cur.execute(
                        """
                        INSERT INTO wealth (
                            application_id, productive_assets, non_productive_assets,
                            formal_liabilities, informal_liabilities, signal_revenue_erosion,
                            signal_margin, signal_receivables, signal_payables, signal_net_worth
                        )
                        SELECT m.application_id, s.productive_assets, s.non_productive_assets,
                               s.formal_liabilities, s.informal_liabilities, s.prob_erosion,
                               s.signal_margin, s.signal_receivables, s.signal_payables, s.signal_net_worth
                        FROM stg_wealth s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("wealth", cur.rowcount)

                cash = _exists("monthly_cashflow.csv")
                if cash:
                    cur.execute(
                        "CREATE TEMP TABLE stg_cash (app_ref VARCHAR(20), month_no INT, period_month DATE, inflow NUMERIC, outflow NUMERIC)"
                    )
                    copy_csv(cur, "stg_cash", "app_ref,month_no,period_month,inflow,outflow", cash)
                    cur.execute(
                        """
                        INSERT INTO monthly_cashflow (application_id, month_no, period_month, inflow, outflow)
                        SELECT m.application_id, s.month_no, s.period_month, s.inflow, s.outflow
                        FROM stg_cash s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("monthly_cashflow", cur.rowcount)

                act = _exists("activity.csv")
                if act:
                    cur.execute(
                        """
                        CREATE TEMP TABLE stg_act (
                            app_ref VARCHAR(20), activity_type VARCHAR(80), description TEXT,
                            seniority_months INT, location_area VARCHAR(40), is_seasonal BOOLEAN, proof_level CHAR(2)
                        )
                        """
                    )
                    copy_csv(
                        cur,
                        "stg_act",
                        "app_ref,activity_type,description,seniority_months,location_area,is_seasonal,proof_level",
                        act,
                    )
                    cur.execute(
                        """
                        INSERT INTO activity (
                            application_id, activity_type, description, seniority_months,
                            location_area, is_seasonal, proof_level
                        )
                        SELECT m.application_id, s.activity_type, s.description, s.seniority_months,
                               s.location_area, s.is_seasonal, s.proof_level
                        FROM stg_act s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("activity", cur.rowcount)

                hh = _exists("household.csv")
                if hh:
                    cur.execute(
                        "CREATE TEMP TABLE stg_hh (app_ref VARCHAR(20), household_size INT, housing VARCHAR(40), dependents INT)"
                    )
                    copy_csv(cur, "stg_hh", "app_ref,household_size,housing,dependents", hh)
                    cur.execute(
                        """
                        INSERT INTO household (application_id, household_size, housing, dependents)
                        SELECT m.application_id, s.household_size, s.housing, s.dependents
                        FROM stg_hh s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("household", cur.rowcount)

                ecom = _exists("economic_model.csv")
                if ecom:
                    cur.execute(
                        """
                        CREATE TEMP TABLE stg_ecom (
                            app_ref VARCHAR(20), client_segments VARCHAR(160), product_service VARCHAR(160),
                            avg_price NUMERIC, unit_variable_cost NUMERIC, monthly_fixed_cost NUMERIC, sales_rhythm VARCHAR(40)
                        )
                        """
                    )
                    copy_csv(
                        cur,
                        "stg_ecom",
                        "app_ref,client_segments,product_service,avg_price,unit_variable_cost,monthly_fixed_cost,sales_rhythm",
                        ecom,
                    )
                    cur.execute(
                        """
                        INSERT INTO economic_model (
                            application_id, client_segments, product_service, avg_price,
                            unit_variable_cost, monthly_fixed_cost, sales_rhythm
                        )
                        SELECT m.application_id, s.client_segments, s.product_service, s.avg_price,
                               s.unit_variable_cost, s.monthly_fixed_cost, s.sales_rhythm
                        FROM stg_ecom s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("economic_model", cur.rowcount)

                mkt = _exists("market.csv")
                if mkt:
                    cur.execute(
                        """
                        CREATE TEMP TABLE stg_mkt (
                            app_ref VARCHAR(20), high_season VARCHAR(40), low_season VARCHAR(40),
                            daily_volume NUMERIC, competitor_count INT, single_outlet_dependency BOOLEAN, proof_level CHAR(2)
                        )
                        """
                    )
                    copy_csv(
                        cur,
                        "stg_mkt",
                        "app_ref,high_season,low_season,daily_volume,competitor_count,single_outlet_dependency,proof_level",
                        mkt,
                    )
                    cur.execute(
                        """
                        INSERT INTO market (
                            application_id, high_season, low_season, daily_volume,
                            competitor_count, single_outlet_dependency, proof_level
                        )
                        SELECT m.application_id, s.high_season, s.low_season, s.daily_volume,
                               s.competitor_count, s.single_outlet_dependency, s.proof_level
                        FROM stg_mkt s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("market", cur.rowcount)

                docs = _exists("supporting_document.csv")
                if docs:
                    cur.execute(
                        "CREATE TEMP TABLE stg_doc (app_ref VARCHAR(20), document_type VARCHAR(30), file_path VARCHAR(255), ocr_quality VARCHAR(20))"
                    )
                    copy_csv(cur, "stg_doc", "app_ref,document_type,file_path,ocr_quality", docs)
                    cur.execute(
                        """
                        INSERT INTO supporting_document (application_id, document_type, file_path, ocr_quality, status)
                        SELECT m.application_id, s.document_type, s.file_path, s.ocr_quality, 'recu'
                        FROM stg_doc s JOIN map_app m ON m.app_ref = s.app_ref
                        """
                    )
                    print("supporting_document", cur.rowcount)

            _load_member_join(
                cur,
                "stg_fu",
                """
                CREATE TEMP TABLE stg_fu (
                    external_code VARCHAR(40), visit_code VARCHAR(4), visit_on DATE, days_late INT, signal VARCHAR(80)
                )
                """,
                "external_code,visit_code,visit_on,days_late,signal",
                "portfolio_followup.csv",
                """
                INSERT INTO portfolio_followup (member_id, visit_code, visit_on, days_late, signal)
                SELECT m.id, s.visit_code, s.visit_on, s.days_late, NULLIF(s.signal, '')
                FROM stg_fu s JOIN member m ON m.external_code = s.external_code
                """,
                "portfolio_followup",
            )

            _load_member_join(
                cur,
                "stg_rec",
                """
                CREATE TEMP TABLE stg_rec (
                    external_code VARCHAR(40), level INT, action VARCHAR(120), owner_name VARCHAR(80), opened_on DATE
                )
                """,
                "external_code,level,action,owner_name,opened_on",
                "recovery_case.csv",
                """
                INSERT INTO recovery_case (member_id, level, action, owner_name, opened_on)
                SELECT m.id, s.level, s.action, s.owner_name, s.opened_on
                FROM stg_rec s JOIN member m ON m.external_code = s.external_code
                """,
                "recovery_case",
            )

            _load_member_join(
                cur,
                "stg_loan",
                """
                CREATE TEMP TABLE stg_loan (
                    external_code VARCHAR(40), principal NUMERIC, outstanding NUMERIC, days_late INT, status VARCHAR(20),
                    disbursed_on DATE, due_on DATE, observed_on DATE
                )
                """,
                "external_code,principal,outstanding,days_late,status,disbursed_on,due_on,observed_on",
                "outstanding_loan.csv",
                """
                INSERT INTO outstanding_loan (member_id, principal, outstanding, days_late, status, disbursed_on, due_on, observed_on)
                SELECT m.id, s.principal, s.outstanding, s.days_late, s.status, s.disbursed_on, s.due_on, s.observed_on
                FROM stg_loan s JOIN member m ON m.external_code = s.external_code
                """,
                "outstanding_loan",
            )

            for table in (
                "member",
                "account",
                "account_movement",
                "credit_application",
                "income_expense",
                "monthly_cashflow",
            ):
                cur.execute(f"ANALYZE {table}")
            cur.execute("EXPLAIN (FORMAT TEXT) SELECT id FROM member WHERE external_code = 'VOL-0000042'")
            print("--- EXPLAIN member ---")
            print("\n".join(r[0] for r in cur.fetchall()))
            _mark_loaded(cur)
        conn.commit()
    print("Charge OK (membres, comptes, historiques, demandes + collecte, BIC, M6/M7).")


if __name__ == "__main__":
    main()
