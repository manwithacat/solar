"""Utility functions for solar PV economics calculations."""

from constants import (
    REGION_CAPACITY_FACTOR,
    ORIENTATION_FACTOR,
    MONTHLY_FRACTIONS,
    HOURS_PER_YEAR
)


def calculate_generation(kWp: float, location: str, orientation: str) -> dict:
    """Calculate theoretical and realistic annual generation."""
    # Theoretical (peak) output - running at full power all year
    e_theoretical = kWp * HOURS_PER_YEAR

    # Weather-adjusted output
    cf_effective = REGION_CAPACITY_FACTOR[location] * ORIENTATION_FACTOR[orientation]
    e_realistic = kWp * HOURS_PER_YEAR * cf_effective
    kwh_per_kwp = e_realistic / kWp if kWp > 0 else 0

    return {
        "theoretical": e_theoretical,
        "realistic": e_realistic,
        "capacity_factor": cf_effective,
        "kwh_per_kwp": kwh_per_kwp
    }


def calculate_monthly_generation(e_realistic: float) -> list:
    """Distribute annual generation across months."""
    return [e_realistic * frac for frac in MONTHLY_FRACTIONS]


def calculate_monthly_consumption(d_annual: float) -> list:
    """Distribute annual consumption evenly across months."""
    return [d_annual / 12] * 12


def calculate_self_consumption(
    e_realistic: float,
    d_annual: float,
    daytime_share: float,
    battery_kwh: float
) -> dict:
    """Calculate self-consumption with and without battery."""

    # Direct self-consumption (no battery)
    d_day = d_annual * daytime_share
    f_direct = min(0.8 * d_day / e_realistic, 0.8) if e_realistic > 0 else 0
    e_self_direct = e_realistic * f_direct
    e_export_no_batt = max(0, e_realistic - e_self_direct)
    grid_import_no_batt = max(0, d_annual - e_self_direct)

    # Battery model (heuristic, 1 cycle/day max)
    e_surplus_daily = max(0, (e_realistic - e_self_direct) / 365)
    b_daily_max = battery_kwh
    e_batt_daily = min(e_surplus_daily, b_daily_max)
    e_batt_annual = e_batt_daily * 365

    d_remaining = max(0, d_annual - e_self_direct)
    e_self_batt = min(e_batt_annual, d_remaining)

    e_export_batt = max(0, e_realistic - e_self_direct - e_self_batt)
    grid_import_with_batt = max(0, d_annual - e_self_direct - e_self_batt)

    return {
        "e_self_direct": e_self_direct,
        "e_export_no_batt": e_export_no_batt,
        "grid_import_no_batt": grid_import_no_batt,
        "e_self_batt": e_self_batt,
        "e_export_batt": e_export_batt,
        "grid_import_with_batt": grid_import_with_batt
    }


def calculate_annual_financials(
    d_annual: float,
    grid_import: float,
    e_export: float,
    grid_price_p: float,
    seg_price_p: float
) -> dict:
    """Calculate year 1 financials."""
    p_grid = grid_price_p / 100
    p_export = seg_price_p / 100

    cost_baseline = d_annual * p_grid
    cost_with_pv = grid_import * p_grid
    income_export = e_export * p_export
    net_saving = (cost_baseline - cost_with_pv) + income_export

    return {
        "cost_baseline": cost_baseline,
        "cost_with_pv": cost_with_pv,
        "income_export": income_export,
        "net_saving": net_saving
    }


def calculate_loan_payment(principal: float, annual_rate: float, term_years: int) -> float:
    """Calculate annual loan payment using amortization formula."""
    if annual_rate == 0:
        return principal / term_years if term_years > 0 else 0
    r = annual_rate / 100
    return principal * (r * (1 + r) ** term_years) / ((1 + r) ** term_years - 1)


def calculate_multi_year_cashflow(
    pv_cost: float,
    battery_cost: float,
    d_annual: float,
    self_consumption: dict,
    grid_price_p: float,
    seg_price_p: float,
    annual_growth: float,
    years: int,
    discount_rate: float,
    include_battery: bool,
    finance_mode: bool = False,
    loan_term: int = 10,
    loan_rate: float = 5.0
) -> dict:
    """Calculate multi-year cashflow projection.

    Args:
        finance_mode: If True, spread install cost over loan term with interest
        loan_term: Number of years for loan repayment
        loan_rate: Annual interest rate for loan (%)
    """

    if include_battery:
        grid_import = self_consumption["grid_import_with_batt"]
        e_export = self_consumption["e_export_batt"]
        install_cost = pv_cost + battery_cost
    else:
        grid_import = self_consumption["grid_import_no_batt"]
        e_export = self_consumption["e_export_no_batt"]
        install_cost = pv_cost

    p_export = seg_price_p / 100

    # Calculate annual loan payment if financing
    annual_loan_payment = 0
    total_interest = 0
    if finance_mode and install_cost > 0:
        annual_loan_payment = calculate_loan_payment(install_cost, loan_rate, loan_term)
        total_interest = (annual_loan_payment * loan_term) - install_cost

    annual_savings = []
    annual_net_benefit = []  # Savings minus loan payment
    cumulative_cashflow = []
    discounted_cashflow = []

    # For purchase: upfront cost; for finance: no upfront cost
    if finance_mode:
        cum_cf = 0
    else:
        cum_cf = -install_cost

    for t in range(1, years + 1):
        # Grid price escalates each year
        p_grid_t = (grid_price_p / 100) * ((1 + annual_growth / 100) ** t)

        cost_baseline_t = d_annual * p_grid_t
        cost_with_pv_t = grid_import * p_grid_t
        income_export_t = e_export * p_export
        net_saving_t = (cost_baseline_t - cost_with_pv_t) + income_export_t

        annual_savings.append(net_saving_t)

        # Subtract loan payment if within loan term
        if finance_mode and t <= loan_term:
            net_benefit_t = net_saving_t - annual_loan_payment
        else:
            net_benefit_t = net_saving_t

        annual_net_benefit.append(net_benefit_t)
        cum_cf += net_benefit_t
        cumulative_cashflow.append(cum_cf)

        # Discounted cashflow for NPV
        discounted_cf = net_benefit_t / ((1 + discount_rate / 100) ** t)
        discounted_cashflow.append(discounted_cf)

    # Calculate payback period
    payback = None
    for i, cf in enumerate(cumulative_cashflow):
        if cf >= 0:
            payback = i + 1
            break

    # Calculate NPV (no upfront cost for financed, payments are in cashflow)
    npv = sum(discounted_cashflow)

    return {
        "install_cost": install_cost,
        "annual_savings": annual_savings,
        "annual_net_benefit": annual_net_benefit,
        "cumulative_cashflow": cumulative_cashflow,
        "payback_years": payback,
        "npv": npv,
        "annual_loan_payment": annual_loan_payment,
        "total_interest": total_interest,
        "loan_term": loan_term if finance_mode else 0
    }
