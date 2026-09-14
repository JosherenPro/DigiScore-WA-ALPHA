from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class Agency(Base):
    __tablename__ = "agency"
    id = mapped_column(Integer, primary_key=True)
    code = mapped_column(String)
    name = mapped_column(String)
    city = mapped_column(String)
    topology = mapped_column(String)


class FinancialInstitution(Base):
    __tablename__ = "financial_institution"
    id = mapped_column(Integer, primary_key=True)
    code = mapped_column(String)
    name = mapped_column(String)
    city = mapped_column(String)
    kind = mapped_column(String)


class CreditProduct(Base):
    __tablename__ = "credit_product"
    id = mapped_column(Integer, primary_key=True)
    code = mapped_column(String)
    label = mapped_column(String)
    max_amount = mapped_column(Numeric)
    guarantor_threshold = mapped_column(Numeric)
    min_guarantors = mapped_column(Integer)
    is_exceptional = mapped_column(Boolean)
    indicative_rate = mapped_column(Numeric)


class AppUser(Base):
    __tablename__ = "app_user"
    id = mapped_column(Integer, primary_key=True)
    login = mapped_column(String)
    full_name = mapped_column(String)
    role = mapped_column(String)
    agency_id = mapped_column(Integer)
    password_hash = mapped_column(String)


class Member(Base):
    __tablename__ = "member"
    id = mapped_column(Integer, primary_key=True)
    external_code = mapped_column(String)
    last_name = mapped_column(String)
    first_name = mapped_column(String)
    phone = mapped_column(String)
    address = mapped_column(String)
    area = mapped_column(String)
    agency_id = mapped_column(Integer)
    joined_on = mapped_column(Date)
    status = mapped_column(String)
    occupation = mapped_column(String)
    marital_status = mapped_column(String)
    gender = mapped_column(String)


class Account(Base):
    __tablename__ = "account"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer, ForeignKey("member.id"))
    account_no = mapped_column(String)
    account_type = mapped_column(String)
    opened_on = mapped_column(Date)
    status = mapped_column(String)
    current_balance = mapped_column(Numeric)


class AccountMovement(Base):
    __tablename__ = "account_movement"
    id = mapped_column(Integer, primary_key=True)
    account_id = mapped_column(Integer)
    moved_on = mapped_column(Date)
    movement_type = mapped_column(String)
    amount = mapped_column(Numeric)
    label = mapped_column(String)


class SavingsSnapshot(Base):
    __tablename__ = "savings_snapshot"
    id = mapped_column(Integer, primary_key=True)
    account_id = mapped_column(Integer)
    as_of = mapped_column(Date)
    avg_balance_3m = mapped_column(Numeric)
    avg_balance_6m = mapped_column(Numeric)
    avg_balance_12m = mapped_column(Numeric)


class PastCredit(Base):
    __tablename__ = "past_credit"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    institution_id = mapped_column(Integer)
    amount = mapped_column(Numeric)
    term_months = mapped_column(Integer)
    granted_on = mapped_column(Date)
    closed_on = mapped_column(Date)
    status = mapped_column(String)
    late_count = mapped_column(Integer)
    max_days_late = mapped_column(Integer)
    source = mapped_column(String)


class Incident(Base):
    __tablename__ = "incident"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    incident_type = mapped_column(String)
    occurred_on = mapped_column(Date)
    severity = mapped_column(String)
    detail = mapped_column(Text)


class MemberGuarantee(Base):
    __tablename__ = "member_guarantee"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    kind = mapped_column(String)
    value_amount = mapped_column(Numeric)


class ExternalAccount(Base):
    __tablename__ = "external_account"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    institution_id = mapped_column(Integer)
    account_no_mask = mapped_column(String)
    opened_on = mapped_column(Date)
    status = mapped_column(String)
    current_balance = mapped_column(Numeric)


class ExternalAccountMovement(Base):
    __tablename__ = "external_account_movement"
    id = mapped_column(Integer, primary_key=True)
    account_id = mapped_column(Integer)
    moved_on = mapped_column(Date)
    movement_type = mapped_column(String)
    amount = mapped_column(Numeric)
    label = mapped_column(String)


class ExternalSavingsSnapshot(Base):
    __tablename__ = "external_savings_snapshot"
    id = mapped_column(Integer, primary_key=True)
    account_id = mapped_column(Integer)
    as_of = mapped_column(Date)
    avg_balance_3m = mapped_column(Numeric)
    avg_balance_6m = mapped_column(Numeric)
    avg_balance_12m = mapped_column(Numeric)


class BicConsent(Base):
    __tablename__ = "bic_consent"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    signed_on = mapped_column(Date)
    status = mapped_column(String)
    scan_path = mapped_column(String)


class BicReport(Base):
    __tablename__ = "bic_report"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    application_id = mapped_column(Integer)
    external_credit_count = mapped_column(Integer)
    bic_incident_count = mapped_column(Integer)
    indebtedness_summary = mapped_column(Text)
    source = mapped_column(String)


class CreditApplication(Base):
    __tablename__ = "credit_application"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    product_id = mapped_column(Integer)
    agent_id = mapped_column(Integer)
    purpose = mapped_column(String)
    requested_amount = mapped_column(Numeric)
    term_months = mapped_column(Integer)
    status = mapped_column(String)
    tax_status = mapped_column(String)
    has_external_credits = mapped_column(Boolean)
    external_proofs_ok = mapped_column(Boolean)
    esg_exclusion = mapped_column(Boolean)
    applied_at = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    agency_id = mapped_column(Integer)


class IncomeExpense(Base):
    __tablename__ = "income_expense"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    revenue = mapped_column(Numeric)
    cogs = mapped_column(Numeric)
    operating_costs = mapped_column(Numeric)
    financial_income = mapped_column(Numeric)
    personal_income = mapped_column(Numeric)
    family_cost = mapped_column(Numeric)
    existing_debt_service = mapped_column(Numeric)
    equity = mapped_column(Numeric)
    total_debt = mapped_column(Numeric)
    total_assets = mapped_column(Numeric)
    current_assets = mapped_column(Numeric)
    current_liabilities = mapped_column(Numeric)
    avg_inventory = mapped_column(Numeric)
    net_income = mapped_column(Numeric)
    income_proof_level = mapped_column(String)
    expense_proof_level = mapped_column(String)


class Wealth(Base):
    __tablename__ = "wealth"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    productive_assets = mapped_column(Numeric)
    non_productive_assets = mapped_column(Numeric)
    formal_liabilities = mapped_column(Numeric)
    informal_liabilities = mapped_column(Numeric)
    signal_revenue_erosion = mapped_column(Boolean)
    signal_margin = mapped_column(Boolean)
    signal_receivables = mapped_column(Boolean)
    signal_payables = mapped_column(Boolean)
    signal_net_worth = mapped_column(Boolean)


class MonthlyCashflow(Base):
    __tablename__ = "monthly_cashflow"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    month_no = mapped_column(Integer)
    period_month = mapped_column(Date)
    inflow = mapped_column(Numeric)
    outflow = mapped_column(Numeric)


class Household(Base):
    __tablename__ = "household"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    household_size = mapped_column(Integer)
    housing = mapped_column(String)
    dependents = mapped_column(Integer)


class EconomicModel(Base):
    __tablename__ = "economic_model"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    client_segments = mapped_column(String)
    product_service = mapped_column(String)
    avg_price = mapped_column(Numeric)
    unit_variable_cost = mapped_column(Numeric)
    monthly_fixed_cost = mapped_column(Numeric)
    sales_rhythm = mapped_column(String)


class Market(Base):
    __tablename__ = "market"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    high_season = mapped_column(String)
    low_season = mapped_column(String)
    daily_volume = mapped_column(Numeric)
    competitor_count = mapped_column(Integer)
    single_outlet_dependency = mapped_column(Boolean)
    proof_level = mapped_column(String)


class Activity(Base):
    __tablename__ = "activity"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    activity_type = mapped_column(String)
    description = mapped_column(Text)
    seniority_months = mapped_column(Integer, default=12)
    location_area = mapped_column(String)
    is_seasonal = mapped_column(Boolean, default=False)
    proof_level = mapped_column(String, default="N1")


class ApplicationGuarantee(Base):
    __tablename__ = "application_guarantee"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    kind = mapped_column(String)
    value_amount = mapped_column(Numeric)


class GuarantorReview(Base):
    __tablename__ = "guarantor_review"
    id = mapped_column(Integer, primary_key=True)
    application_guarantor_id = mapped_column(Integer)
    eligible = mapped_column(Boolean)


class ApplicationGuarantor(Base):
    __tablename__ = "application_guarantor"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    guarantor_id = mapped_column(Integer)


class ScoreResult(Base):
    __tablename__ = "score_result"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    score_total = mapped_column(Numeric)
    thin_file = mapped_column(Boolean)
    eligible = mapped_column(Boolean)
    requested_amount = mapped_column(Numeric)
    eligible_amount = mapped_column(Numeric)
    suggested_max_amount = mapped_column(Numeric)
    message_code = mapped_column(String)
    message_text = mapped_column(Text)
    criteria = mapped_column(JSONB)
    knockouts = mapped_column(JSONB)
    explanation = mapped_column(JSONB)
    engine_version = mapped_column(String)
    created_at = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=func.now()
    )


class ScoreResultHistory(Base):
    __tablename__ = "score_result_history"
    history_id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    score_total = mapped_column(Numeric)
    thin_file = mapped_column(Boolean)
    eligible = mapped_column(Boolean)
    requested_amount = mapped_column(Numeric)
    eligible_amount = mapped_column(Numeric)
    suggested_max_amount = mapped_column(Numeric)
    message_code = mapped_column(String)
    message_text = mapped_column(Text)
    criteria = mapped_column(JSONB)
    knockouts = mapped_column(JSONB)
    explanation = mapped_column(JSONB)
    engine_version = mapped_column(String)
    scored_at = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=func.now()
    )


class Decision(Base):
    __tablename__ = "decision"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    level = mapped_column(String)
    opinion = mapped_column(String)
    reason = mapped_column(Text)
    is_override = mapped_column(Boolean)
    user_id = mapped_column(Integer)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    user_id = mapped_column(Integer)
    action = mapped_column(String)
    detail = mapped_column(Text)


class FinancialRatio(Base):
    __tablename__ = "financial_ratio"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    ebe = mapped_column(Numeric)
    caf = mapped_column(Numeric)
    rcsd = mapped_column(Numeric)
    gross_margin_pct = mapped_column(Numeric)
    net_margin_pct = mapped_column(Numeric)
    solvency = mapped_column(Numeric)
    inventory_days = mapped_column(Numeric)
    equity_ratio_pct = mapped_column(Numeric)
    working_capital_pct = mapped_column(Numeric)
    net_worth = mapped_column(Numeric)
    weak_ratio_count = mapped_column(Integer)
    stress_month = mapped_column(Integer)
    computed_at = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=func.now()
    )


class FinancialRatioHistory(Base):
    __tablename__ = "financial_ratio_history"
    history_id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    ebe = mapped_column(Numeric)
    caf = mapped_column(Numeric)
    rcsd = mapped_column(Numeric)
    gross_margin_pct = mapped_column(Numeric)
    net_margin_pct = mapped_column(Numeric)
    solvency = mapped_column(Numeric)
    inventory_days = mapped_column(Numeric)
    equity_ratio_pct = mapped_column(Numeric)
    working_capital_pct = mapped_column(Numeric)
    net_worth = mapped_column(Numeric)
    weak_ratio_count = mapped_column(Integer)
    stress_month = mapped_column(Integer)
    computed_at = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), server_default=func.now()
    )


class AmortizationLine(Base):
    __tablename__ = "amortization_line"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    installment_no = mapped_column(Integer)
    installment_amount = mapped_column(Numeric)
    principal = mapped_column(Numeric)
    interest_amount = mapped_column(Numeric)
    insurance_amount = mapped_column(Numeric)
    remaining_principal = mapped_column(Numeric)
    due_on = mapped_column(Date)


class ParIndicator(Base):
    __tablename__ = "par_indicator"
    id = mapped_column(Integer, primary_key=True)
    agency_id = mapped_column(Integer)
    as_of = mapped_column(Date)
    par1_pct = mapped_column(Numeric)
    par30_pct = mapped_column(Numeric)
    par90_pct = mapped_column(Numeric)
    encours_brut = mapped_column(Numeric)
    restructured_amount = mapped_column(Numeric)
    computed_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class OutstandingLoan(Base):
    __tablename__ = "outstanding_loan"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    application_id = mapped_column(Integer)
    principal = mapped_column(Numeric)
    outstanding = mapped_column(Numeric)
    days_late = mapped_column(Integer)
    status = mapped_column(String)
    disbursed_on = mapped_column(Date)
    due_on = mapped_column(Date)
    observed_on = mapped_column(Date)
    restructured = mapped_column(Boolean)


class LoanPayment(Base):
    __tablename__ = "loan_payment"
    id = mapped_column(Integer, primary_key=True)
    outstanding_loan_id = mapped_column(Integer)
    paid_on = mapped_column(Date)
    amount = mapped_column(Numeric)
    kind = mapped_column(String)
    external_ref = mapped_column(String)


class PortfolioFollowup(Base):
    __tablename__ = "portfolio_followup"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    visit_code = mapped_column(String)
    visit_on = mapped_column(Date)
    officer_id = mapped_column(Integer)
    days_late = mapped_column(Integer)
    signal = mapped_column(String)
    signal_code = mapped_column(String)
    visit_status = mapped_column(String)
    next_on = mapped_column(Date)
    action_taken = mapped_column(String)


class RecoveryCase(Base):
    __tablename__ = "recovery_case"
    id = mapped_column(Integer, primary_key=True)
    member_id = mapped_column(Integer)
    level = mapped_column(Integer)
    action = mapped_column(String)
    owner_name = mapped_column(String)
    opened_on = mapped_column(Date)
    next_on = mapped_column(Date)
    priority = mapped_column(String)
    status = mapped_column(String)
    recovered_amount = mapped_column(Numeric)
    last_action_on = mapped_column(Date)
    closed_on = mapped_column(Date)


class RecoveryAction(Base):
    __tablename__ = "recovery_action"
    id = mapped_column(Integer, primary_key=True)
    case_id = mapped_column(Integer)
    action_on = mapped_column(Date)
    action_type = mapped_column(String)
    note = mapped_column(Text)
    promise_on = mapped_column(Date)
    promise_kept = mapped_column(Boolean)
    amount_recovered = mapped_column(Numeric)


class ResilienceSimulation(Base):
    __tablename__ = "resilience_simulation"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    scenario = mapped_column(String)
    requested_amount = mapped_column(Numeric)
    term_months = mapped_column(Integer)
    horizon_months = mapped_column(Integer)
    iterations = mapped_column(Integer)
    random_seed = mapped_column(Integer)
    model_version = mapped_column(String)
    incident_probability = mapped_column(Numeric)
    critical_month = mapped_column(Integer)
    result_json = mapped_column(JSONB)
    created_by = mapped_column(Integer)
    created_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class SupportingDocument(Base):
    __tablename__ = "supporting_document"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(Integer)
    document_type = mapped_column(String)
    file_path = mapped_column(String)
    ocr_quality = mapped_column(String)
    status = mapped_column(String)
