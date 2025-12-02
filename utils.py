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
    include_battery: bool
) -> dict:
    """Calculate multi-year cashflow projection."""

    if include_battery:
        grid_import = self_consumption["grid_import_with_batt"]
        e_export = self_consumption["e_export_batt"]
        install_cost = pv_cost + battery_cost
    else:
        grid_import = self_consumption["grid_import_no_batt"]
        e_export = self_consumption["e_export_no_batt"]
        install_cost = pv_cost

    p_export = seg_price_p / 100

    annual_savings = []
    cumulative_cashflow = []
    discounted_cashflow = []
    cum_cf = -install_cost

    for t in range(1, years + 1):
        # Grid price escalates each year
        p_grid_t = (grid_price_p / 100) * ((1 + annual_growth / 100) ** t)

        cost_baseline_t = d_annual * p_grid_t
        cost_with_pv_t = grid_import * p_grid_t
        income_export_t = e_export * p_export
        net_saving_t = (cost_baseline_t - cost_with_pv_t) + income_export_t

        annual_savings.append(net_saving_t)
        cum_cf += net_saving_t
        cumulative_cashflow.append(cum_cf)

        # Discounted cashflow for NPV
        discounted_cf = net_saving_t / ((1 + discount_rate / 100) ** t)
        discounted_cashflow.append(discounted_cf)

    # Calculate payback period
    payback = None
    for i, cf in enumerate(cumulative_cashflow):
        if cf >= 0:
            payback = i + 1
            break

    # Calculate NPV
    npv = -install_cost + sum(discounted_cashflow)

    return {
        "install_cost": install_cost,
        "annual_savings": annual_savings,
        "cumulative_cashflow": cumulative_cashflow,
        "payback_years": payback,
        "npv": npv
    }
