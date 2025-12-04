"""Utility functions for solar PV economics calculations."""

from constants import (
    REGION_CAPACITY_FACTOR,
    ORIENTATION_FACTOR,
    MONTHLY_FRACTIONS,
    HEATING_TYPES,
    CONSUMPTION_PROFILE_GAS,
    EV_EFFICIENCY_KWH_PER_MILE,
    DAYS_PER_YEAR,
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


def calculate_monthly_consumption(
    d_annual: float,
    heating_type: str = "Gas/Oil boiler"
) -> list:
    """Distribute annual consumption across months based on heating type."""
    profile = HEATING_TYPES.get(heating_type, {}).get("profile", CONSUMPTION_PROFILE_GAS)
    return [d_annual * frac for frac in profile]


def calculate_ev_consumption(
    daily_miles: float,
    home_charging_share: float = 0.8
) -> dict:
    """Calculate annual EV charging demand.

    Args:
        daily_miles: Average daily miles driven
        home_charging_share: Fraction of charging done at home (0-1)

    Returns:
        Dict with annual_kwh and daily_kwh for home charging
    """
    daily_kwh_total = daily_miles * EV_EFFICIENCY_KWH_PER_MILE
    daily_kwh_home = daily_kwh_total * home_charging_share
    annual_kwh = daily_kwh_home * DAYS_PER_YEAR

    return {
        "daily_kwh_total": daily_kwh_total,
        "daily_kwh_home": daily_kwh_home,
        "annual_kwh": annual_kwh
    }


def adjust_consumption_for_heating(
    base_usage: float,
    heating_type: str
) -> float:
    """Adjust base electricity usage based on heating type.

    For electric heating, total consumption increases significantly.
    """
    multiplier = HEATING_TYPES.get(heating_type, {}).get("base_usage_multiplier", 1.0)
    return base_usage * multiplier


def calculate_self_consumption(
    e_realistic: float,
    d_annual: float,
    daytime_share: float,
    battery_kwh: float,
    ev_annual_kwh: float = 0,
    ev_solar_share: float = 0.3
) -> dict:
    """Calculate self-consumption with and without battery.

    Args:
        e_realistic: Annual solar generation (kWh)
        d_annual: Annual household consumption (kWh)
        daytime_share: Fraction of consumption during daylight hours
        battery_kwh: Usable battery capacity (kWh)
        ev_annual_kwh: Annual EV charging demand at home (kWh)
        ev_solar_share: Fraction of EV charging that can use solar/battery
                        (depends on charging timing - daytime/evening)
    """
    # Total demand including EV
    total_demand = d_annual + ev_annual_kwh

    # Direct self-consumption (no battery) - household only
    d_day = d_annual * daytime_share
    f_direct = min(0.8 * d_day / e_realistic, 0.8) if e_realistic > 0 else 0
    e_self_direct = e_realistic * f_direct
    e_export_no_batt = max(0, e_realistic - e_self_direct)
    grid_import_no_batt = max(0, total_demand - e_self_direct)

    # Battery model (heuristic, 1 cycle/day max for home battery)
    e_surplus_daily = max(0, (e_realistic - e_self_direct) / DAYS_PER_YEAR)
    b_daily_max = battery_kwh
    e_batt_daily = min(e_surplus_daily, b_daily_max)
    e_batt_annual = e_batt_daily * DAYS_PER_YEAR

    # Battery first serves remaining household demand
    d_remaining_household = max(0, d_annual - e_self_direct)
    e_batt_to_house = min(e_batt_annual, d_remaining_household)

    # Remaining battery capacity can charge EV (if charging in evening)
    e_batt_remaining = e_batt_annual - e_batt_to_house
    ev_from_battery = min(e_batt_remaining, ev_annual_kwh * ev_solar_share)

    # Some EV charging can also happen directly during daytime
    ev_direct_solar = min(
        max(0, e_realistic - e_self_direct - e_batt_annual) * 0.3,  # 30% of remaining export
        ev_annual_kwh * 0.2  # Up to 20% of EV demand if charging during day
    )

    # Total self-consumption with battery
    e_self_batt = e_batt_to_house + ev_from_battery + ev_direct_solar
    total_solar_to_ev = ev_from_battery + ev_direct_solar

    e_export_batt = max(0, e_realistic - e_self_direct - e_self_batt)
    grid_import_with_batt = max(0, total_demand - e_self_direct - e_self_batt)

    # EV-specific metrics
    ev_grid_import = max(0, ev_annual_kwh - total_solar_to_ev)

    return {
        "e_self_direct": e_self_direct,
        "e_export_no_batt": e_export_no_batt,
        "grid_import_no_batt": grid_import_no_batt,
        "e_self_batt": e_self_batt,
        "e_export_batt": e_export_batt,
        "grid_import_with_batt": grid_import_with_batt,
        "ev_annual_kwh": ev_annual_kwh,
        "ev_from_solar": total_solar_to_ev,
        "ev_from_grid": ev_grid_import,
        "total_demand": total_demand
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
    loan_rate: float = 5.0,
    deposit_pct: float = 0,
    lease_mode: bool = False,
    lease_term: int = 10,
    monthly_lease: float = 0
) -> dict:
    """Calculate multi-year cashflow projection.

    Args:
        finance_mode: If True, spread install cost over loan term with interest
        loan_term: Number of years for loan repayment
        loan_rate: Annual interest rate for loan (%)
        deposit_pct: Deposit percentage (0-100) paid upfront when financing
        lease_mode: If True, use fixed monthly lease payments (no ownership)
        lease_term: Number of years for lease
        monthly_lease: Monthly lease payment in pounds
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

    # Calculate deposit and loan amount (for loan mode)
    deposit_amount = install_cost * (deposit_pct / 100) if finance_mode else 0
    loan_amount = install_cost - deposit_amount if finance_mode else 0

    # Calculate annual payments based on mode
    annual_loan_payment = 0
    annual_lease_payment = 0
    total_interest = 0
    total_lease_cost = 0

    if finance_mode and loan_amount > 0:
        annual_loan_payment = calculate_loan_payment(loan_amount, loan_rate, loan_term)
        total_interest = (annual_loan_payment * loan_term) - loan_amount
    elif lease_mode and monthly_lease > 0:
        annual_lease_payment = monthly_lease * 12
        total_lease_cost = annual_lease_payment * lease_term

    annual_savings = []
    annual_net_benefit = []  # Savings minus loan/lease payment
    cumulative_cashflow = []
    discounted_cashflow = []

    # Starting cashflow position
    if finance_mode:
        cum_cf = -deposit_amount  # Only deposit upfront for loan
    elif lease_mode:
        cum_cf = 0  # No upfront cost for lease
    else:
        cum_cf = -install_cost  # Full cost upfront for purchase

    for t in range(1, years + 1):
        # Grid price escalates each year
        p_grid_t = (grid_price_p / 100) * ((1 + annual_growth / 100) ** t)

        cost_baseline_t = d_annual * p_grid_t
        cost_with_pv_t = grid_import * p_grid_t
        income_export_t = e_export * p_export
        net_saving_t = (cost_baseline_t - cost_with_pv_t) + income_export_t

        annual_savings.append(net_saving_t)

        # Subtract loan/lease payment if within term
        if finance_mode and t <= loan_term:
            net_benefit_t = net_saving_t - annual_loan_payment
        elif lease_mode and t <= lease_term:
            net_benefit_t = net_saving_t - annual_lease_payment
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

    # Calculate NPV
    if finance_mode:
        npv = -deposit_amount + sum(discounted_cashflow)
    elif lease_mode:
        npv = sum(discounted_cashflow)  # No upfront cost
    else:
        npv = sum(discounted_cashflow)

    return {
        "install_cost": install_cost,
        "annual_savings": annual_savings,
        "annual_net_benefit": annual_net_benefit,
        "cumulative_cashflow": cumulative_cashflow,
        "payback_years": payback,
        "npv": npv,
        "annual_loan_payment": annual_loan_payment,
        "annual_lease_payment": annual_lease_payment,
        "total_interest": total_interest,
        "total_lease_cost": total_lease_cost,
        "loan_term": loan_term if finance_mode else 0,
        "lease_term": lease_term if lease_mode else 0,
        "deposit_amount": deposit_amount,
        "loan_amount": loan_amount
    }
