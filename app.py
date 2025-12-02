"""Solar Economics Streamlit Dashboard.

An interactive dashboard for modelling the economic benefits of
residential solar PV + battery installation in the UK.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from constants import MONTH_NAMES, HEATING_TYPES
from utils import (
    calculate_generation,
    calculate_monthly_generation,
    calculate_monthly_consumption,
    calculate_self_consumption,
    calculate_annual_financials,
    calculate_multi_year_cashflow,
    calculate_ev_consumption,
    adjust_consumption_for_heating
)
from quotation import generate_quotation_pdf

st.set_page_config(
    page_title="UK Solar Economics Calculator",
    page_icon="☀️",
    layout="wide"
)

st.title("☀️ UK Solar Economics Calculator")

tab_calculator, tab_battery, tab_quotation, tab_assumptions = st.tabs(["Calculator", "Why Battery?", "Generate Quotation", "Assumptions & Sources"])

with tab_assumptions:
    st.header("Default Values & Sources")
    st.markdown("""
    This page explains the default values used in the calculator and their sources.
    All values can be adjusted using the sidebar controls.
    """)

    st.subheader("Electricity Prices")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Grid price** | 28p/kWh | Based on Ofgem Q4 2024 price cap of ~24p/kWh for electricity, plus typical standing charges. Many variable tariffs range 22-35p/kWh. |
    | **SEG export tariff** | 15p/kWh | Competitive SEG rates in late 2024 range from 4-15p/kWh. Octopus, EDF, and others offer rates at the higher end for fixed-term deals. |
    | **Annual price growth** | 3% | Conservative estimate based on historical trends. UK electricity prices have risen faster historically, but future growth is uncertain. |
    """)

    st.subheader("System Costs")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **PV install cost** | £6,000 | For a typical 4kWp system. UK prices range £4,000-8,000 for 3-5kWp systems (2024 pricing, post-VAT exemption). |
    | **Battery install cost** | £4,000 | For a 5kWh usable capacity battery. Prices range £2,500-6,000 depending on brand and capacity. |
    """)

    st.subheader("System Sizing")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Solar capacity** | 4 kWp | Common residential size for a 3-bed semi. Typical UK installs range 3-6 kWp. |
    | **Battery size** | 5 kWh | Matches typical evening usage for a medium household. Popular sizes are 5-10 kWh. |
    """)

    st.subheader("Household Consumption")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Annual usage** | 3,500 kWh | Ofgem's Typical Domestic Consumption Value (TDCV) for medium electricity use. Range: 1,800 (low) to 4,300+ (high). |
    | **Daytime share** | 40% | Assumes some home working or daytime occupancy. Range: 20% (out all day) to 60%+ (home-based). |
    """)

    st.subheader("Capacity Factors")
    st.markdown("""
    | Region | Capacity Factor | Rationale |
    |--------|-----------------|-----------|
    | **South England** | 13% | Higher solar irradiance in the south. Annual generation ~950-1,100 kWh/kWp. |
    | **Midlands** | 12% | Moderate irradiance. Annual generation ~900-1,000 kWh/kWp. |
    | **North/Scotland** | 11% | Lower irradiance but longer summer days partially compensate. ~850-950 kWh/kWp. |

    These capacity factors are based on MCS and Energy Saving Trust data for UK installations.
    """)

    st.subheader("Orientation Factors")
    st.markdown("""
    | Orientation | Factor | Rationale |
    |-------------|--------|-----------|
    | **South** | 100% | Optimal for UK latitude (~51-56°N). Maximum solar capture. |
    | **SE/SW** | 90% | ~10% reduction from ideal. Still excellent performance. |
    | **E/W** | 80% | Split east-west can work well for morning/evening generation. |
    | **North/shaded** | 60% | Significantly reduced output. Generally not recommended. |
    """)

    st.subheader("Financial Parameters")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Time horizon** | 25 years | Typical solar panel warranty period. Panels often last 30+ years with gradual degradation. |
    | **Discount rate** | 3% | Represents opportunity cost of capital. Range: 0% (pure payback) to 5-7% (commercial hurdle rate). |
    """)

    st.subheader("Financing Options")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Deposit** | 25% | Typical deposit for solar finance. Range: 0-50% depending on lender and credit. |
    | **Loan term** | 10 years | Common term for home improvement loans. Range: 5-20 years available from most lenders. |
    | **Interest rate** | 5% | Typical unsecured personal loan rate (2024). Secured loans may be lower (3-4%), credit cards higher (15-25%). |

    **Note:** When financing, the cumulative cashflow chart shows net benefit after loan payments.
    During the loan term, annual savings are reduced by loan payments. After the loan is paid off,
    full savings are retained.
    """)

    st.subheader("Heating Types")
    st.markdown("""
    | Heating Type | Consumption Multiplier | Monthly Profile |
    |--------------|----------------------|-----------------|
    | **Gas/Oil boiler** | 1.0x | Relatively flat (slight winter increase for lighting) |
    | **Heat pump** | 1.5x | Winter-weighted. Heat pumps are efficient (COP 3-4) but still add ~50% to electricity use. |
    | **Electric resistive** | 2.5x | Winter-weighted. Storage heaters/direct electric significantly increase consumption. |

    Electric heating creates a mismatch: highest consumption in winter when solar generation is lowest.
    This affects payback calculations significantly.
    """)

    st.subheader("EV Charging")
    st.markdown("""
    | Parameter | Default | Rationale |
    |-----------|---------|-----------|
    | **Daily miles** | 30 | UK average is ~20-25 miles/day. 30 is slightly above average for commuters. |
    | **Home charging share** | 80% | Most EV owners charge primarily at home. Range: 50-100% depending on workplace/public charging access. |
    | **Efficiency** | 0.3 kWh/mile | Typical for modern EVs. Range: 0.25 (efficient) to 0.4 (larger vehicles, cold weather). |

    **EV + Battery synergy:** A home battery can store daytime solar for evening EV charging,
    significantly increasing solar self-consumption. Without a battery, most EV charging
    (typically done overnight) must come from the grid.
    """)

    st.subheader("Sources")
    st.markdown("""
    - [Ofgem Price Cap](https://www.ofgem.gov.uk/energy-price-cap) - Quarterly electricity price updates
    - [Energy Saving Trust](https://energysavingtrust.org.uk/advice/solar-panels/) - Solar PV guidance
    - [MCS](https://mcscertified.com/) - Microgeneration Certification Scheme data
    - [Solar Energy UK](https://solarenergyuk.org/) - Industry statistics
    - [Octopus Energy SEG](https://octopus.energy/outgoing/) - Example export tariff rates
    """)

with tab_battery:
    st.header("Do I Need a Battery?")

    st.markdown("""
    A home battery stores excess solar energy generated during the day for use in the evening
    and overnight. But is it worth the extra investment? Let's break it down.
    """)

    st.subheader("The Core Economics")

    st.markdown("""
    The financial case for a battery depends on the **spread** between what you pay for grid
    electricity and what you earn from exporting:
    """)

    col_price1, col_price2, col_price3 = st.columns(3)
    with col_price1:
        st.metric("Grid Price", "28p/kWh", help="What you pay to import electricity")
    with col_price2:
        st.metric("Export Tariff (SEG)", "15p/kWh", help="What you earn selling to grid")
    with col_price3:
        st.metric("Value of Storage", "13p/kWh", help="Benefit per kWh stored vs exported")

    st.markdown("""
    **Without a battery:** Excess daytime solar is exported at 15p/kWh.

    **With a battery:** That same energy is stored and used later, avoiding a 28p/kWh grid purchase.

    **Net benefit per kWh shifted:** 28p - 15p = **13p/kWh**
    """)

    st.subheader("Battery Payback vs Lifespan")

    st.warning("""
    **Important reality check:** Most home batteries have a warranty of **10 years** and an effective
    lifespan of **10-15 years**. If payback exceeds this, the pure financial case is weak.
    """)

    st.markdown("""
    A typical 5kWh battery costs around **£4,000**. Let's calculate the payback and compare to lifespan:
    """)

    # Interactive battery ROI calculator
    st.markdown("#### Try your own numbers:")
    col_batt1, col_batt2 = st.columns(2)
    with col_batt1:
        batt_cost_calc = st.number_input("Battery cost (£)", value=4000, step=500)
        batt_capacity_calc = st.number_input("Battery capacity (kWh)", value=5.0, step=0.5)
    with col_batt2:
        grid_price_calc = st.number_input("Grid price (p/kWh)", value=28, step=1)
        export_price_calc = st.number_input("Export price (p/kWh)", value=15, step=1)

    # Assume 1 cycle per day, 90% usable on average
    daily_cycles = 1.0
    usable_factor = 0.9
    days_per_year = 365

    annual_kwh_shifted = batt_capacity_calc * daily_cycles * usable_factor * days_per_year
    value_per_kwh = (grid_price_calc - export_price_calc) / 100
    annual_battery_benefit = annual_kwh_shifted * value_per_kwh
    battery_payback = batt_cost_calc / annual_battery_benefit if annual_battery_benefit > 0 else float('inf')

    # Typical battery lifespan
    battery_warranty = 10
    battery_lifespan = 12  # Realistic expectation

    col_result1, col_result2, col_result3, col_result4 = st.columns(4)
    with col_result1:
        st.metric("Annual kWh Shifted", f"{annual_kwh_shifted:,.0f}")
    with col_result2:
        st.metric("Annual Battery Benefit", f"£{annual_battery_benefit:,.0f}")
    with col_result3:
        if battery_payback < 100:
            st.metric("Battery Payback", f"{battery_payback:.1f} years")
        else:
            st.metric("Battery Payback", "Not viable")
    with col_result4:
        if battery_payback < battery_warranty:
            st.metric("Payback vs Warranty", f"✅ {battery_warranty - battery_payback:.1f}y margin")
        elif battery_payback < battery_lifespan:
            st.metric("Payback vs Lifespan", f"⚠️ {battery_lifespan - battery_payback:.1f}y margin")
        else:
            st.metric("Payback vs Lifespan", f"❌ Exceeds lifespan")

    # Calculate lifetime return
    lifetime_benefit = annual_battery_benefit * battery_lifespan
    lifetime_roi = ((lifetime_benefit - batt_cost_calc) / batt_cost_calc * 100) if batt_cost_calc > 0 else 0

    st.info(f"""
    **Calculation:** {batt_capacity_calc} kWh × {daily_cycles} cycle/day × {usable_factor:.0%} usable × 365 days
    = **{annual_kwh_shifted:,.0f} kWh/year** shifted from export to self-use.

    At {grid_price_calc - export_price_calc}p/kWh benefit = **£{annual_battery_benefit:,.0f}/year** savings.

    £{batt_cost_calc:,} ÷ £{annual_battery_benefit:,.0f} = **{battery_payback:.1f} year payback** on battery alone.
    """)

    # Lifetime analysis
    if battery_payback >= battery_lifespan:
        st.error(f"""
        **Lifetime Analysis:** With a {battery_lifespan}-year lifespan, you'd recover only
        **£{lifetime_benefit:,.0f}** of the **£{batt_cost_calc:,}** battery cost — a **net loss of £{batt_cost_calc - lifetime_benefit:,.0f}**.

        The battery does not pay for itself on pure economics at these prices.
        """)
    elif battery_payback >= battery_warranty:
        st.warning(f"""
        **Lifetime Analysis:** Payback of {battery_payback:.1f} years exceeds the {battery_warranty}-year warranty.
        Over a {battery_lifespan}-year lifespan, total benefit = **£{lifetime_benefit:,.0f}** vs **£{batt_cost_calc:,}** cost.

        Net lifetime gain: **£{lifetime_benefit - batt_cost_calc:,.0f}** ({lifetime_roi:.0f}% return) — marginal.
        """)
    else:
        st.success(f"""
        **Lifetime Analysis:** Payback within warranty period.
        Over a {battery_lifespan}-year lifespan, total benefit = **£{lifetime_benefit:,.0f}** vs **£{batt_cost_calc:,}** cost.

        Net lifetime gain: **£{lifetime_benefit - batt_cost_calc:,.0f}** ({lifetime_roi:.0f}% return).
        """)

    st.subheader("When Does a Battery Make Sense?")

    st.markdown("""
    #### Good candidates for a battery:

    | Scenario | Why it helps |
    |----------|--------------|
    | **High grid prices** | Greater spread between buy/sell prices |
    | **Low export tariffs** | Less value lost by not exporting |
    | **Evening/night usage** | More demand when solar isn't generating |
    | **EV charging overnight** | Battery can supply EV from stored solar |
    | **Time-of-use tariffs** | Charge from grid cheap, discharge at peak |
    | **Future-proofing** | Export rates may fall, grid prices may rise |

    #### Battery may NOT be worth it if:

    | Scenario | Why |
    |----------|-----|
    | **High export tariff** | You earn nearly as much exporting as you'd save |
    | **Mostly daytime usage** | You already use most solar directly |
    | **Small solar system** | Not enough excess to fill the battery |
    | **Short ownership period** | Not enough time to recoup battery cost |
    """)

    st.subheader("Beyond Simple Payback")

    st.markdown("""
    The payback calculation above is simplified. Real-world factors include:

    **Positive factors:**
    - Grid prices are rising (~3-5% annually) → battery value increases over time
    - Battery provides backup during power cuts (if configured)
    - Some tariffs pay more for export at peak times
    - Reduced reliance on grid = energy security

    **Negative factors:**
    - Battery degrades over time (typically 70-80% capacity after 10 years)
    - Not every day has enough sun to fully charge the battery
    - Winter generation may not fill the battery
    - Opportunity cost of capital (money could be invested elsewhere)
    """)

    st.subheader("The Honest Verdict")

    st.markdown("""
    **The uncomfortable truth (at 2024 UK prices):**

    - A typical battery payback of **15-20 years** often **exceeds the 10-15 year lifespan**
    - At default prices (28p grid, 15p export), batteries struggle to make pure financial sense
    - The economics only work with **higher grid prices** or **lower export rates**
    """)

    st.markdown("""
    **When a battery IS financially justified:**

    | Scenario | Required spread | Typical payback |
    |----------|-----------------|-----------------|
    | Grid 35p, Export 5p | 30p/kWh | ~8 years ✅ |
    | Grid 40p, Export 10p | 30p/kWh | ~8 years ✅ |
    | Time-of-use tariff | Variable | Can be <5 years ✅ |

    **When a battery is NOT financially justified:**

    | Scenario | Spread | Typical payback |
    |----------|--------|-----------------|
    | Grid 28p, Export 15p | 13p/kWh | ~15 years ❌ |
    | Grid 24p, Export 15p | 9p/kWh | ~22 years ❌ |
    """)

    st.markdown("""
    **Our honest recommendation:**

    - **Pure ROI focus?** Skip the battery at current prices — solar panels alone have much better returns
    - **Want energy independence?** Battery adds resilience and future-proofs against rising prices
    - **Have/planning an EV?** Battery synergy improves the case, but still check the numbers
    - **On a time-of-use tariff?** Batteries can arbitrage cheap overnight rates — worth modelling

    Use the Calculator tab to model your specific situation. Pay attention to whether the battery
    adds positive value over the system's realistic lifetime.
    """)

with tab_calculator:
    st.markdown("""
    This dashboard models the realistic economic benefits of a residential solar PV + battery
    installation in the UK. It contrasts **peak (kWp) output assumptions** with
    **weather-based capacity-factor-adjusted energy generation**.
    """)

    # --- Payment Method Selection ---
    payment_method = st.radio(
        "Payment Method",
        ["Purchase (upfront)", "Finance (loan)"],
        index=1,  # Default to Finance
        horizontal=True
    )
    finance_mode = payment_method == "Finance (loan)"

    # --- Sidebar Inputs ---
    st.sidebar.header("System & Weather Inputs")

    location = st.sidebar.selectbox(
        "Location",
        ["South England", "Midlands", "North/Scotland"]
    )

    orientation = st.sidebar.selectbox(
        "Roof Orientation",
        ["Ideal (South)", "OK (SE/SW)", "Suboptimal (E/W)", "Poor (North/shaded)"]
    )

    kwp = st.sidebar.slider(
        "Solar Peak Capacity (kWp)",
        min_value=1.0, max_value=10.0, value=4.0, step=0.5
    )

    battery_kwh = st.sidebar.slider(
        "Battery Size (kWh usable)",
        min_value=0, max_value=20, value=5, step=1
    )

    st.sidebar.header("Financial Inputs")

    pv_cost = st.sidebar.slider(
        "Install cost (PV) £",
        min_value=3000, max_value=20000, value=6000, step=500
    )

    battery_cost = st.sidebar.slider(
        "Battery install cost £",
        min_value=0, max_value=15000, value=4000, step=500
    )

    grid_price_p = st.sidebar.slider(
        "Grid price (p/kWh)",
        min_value=15, max_value=45, value=28, step=1
    )

    seg_price_p = st.sidebar.slider(
        "Export tariff SEG (p/kWh)",
        min_value=2, max_value=25, value=15, step=1
    )

    annual_growth = st.sidebar.slider(
        "Annual grid price growth (%)",
        min_value=0.0, max_value=8.0, value=3.0, step=0.5
    )

    # Financing options (only shown when finance mode selected)
    if finance_mode:
        st.sidebar.header("Financing Options")

        deposit_pct = st.sidebar.slider(
            "Deposit (%)",
            min_value=0, max_value=50, value=25, step=5
        )

        loan_term = st.sidebar.slider(
            "Loan term (years)",
            min_value=5, max_value=20, value=10, step=1
        )

        loan_rate = st.sidebar.slider(
            "Loan interest rate (%)",
            min_value=0.0, max_value=15.0, value=5.0, step=0.5
        )
    else:
        deposit_pct = 0
        loan_term = 10
        loan_rate = 5.0

    st.sidebar.header("Demand Inputs")

    heating_type = st.sidebar.selectbox(
        "Heating Type",
        list(HEATING_TYPES.keys()),
        help="Electric heating significantly increases electricity consumption"
    )

    d_annual_base = st.sidebar.slider(
        "Base electricity usage (kWh/year)",
        min_value=1500, max_value=8000, value=3500, step=100,
        help="Excluding heating. For electric heating, total will be adjusted."
    )

    # Adjust for heating type
    d_annual = adjust_consumption_for_heating(d_annual_base, heating_type)

    daytime_share = st.sidebar.slider(
        "Daytime usage share (%)",
        min_value=20, max_value=70, value=40, step=5
    ) / 100

    # EV charging options
    st.sidebar.header("EV Charging (Optional)")

    has_ev = st.sidebar.checkbox("Include EV charging", value=False)

    if has_ev:
        daily_miles = st.sidebar.slider(
            "Average daily miles",
            min_value=10, max_value=100, value=30, step=5
        )
        home_charging_pct = st.sidebar.slider(
            "Home charging share (%)",
            min_value=50, max_value=100, value=80, step=5,
            help="Percentage of charging done at home vs workplace/public"
        ) / 100
        ev_consumption = calculate_ev_consumption(daily_miles, home_charging_pct)
        ev_annual_kwh = ev_consumption["annual_kwh"]
    else:
        daily_miles = 0
        ev_annual_kwh = 0

    years = st.sidebar.slider(
        "Time horizon (years)",
        min_value=10, max_value=30, value=25, step=1
    )

    discount_rate = st.sidebar.slider(
        "Discount rate (%)",
        min_value=0.0, max_value=8.0, value=3.0, step=0.5
    )

    # --- Calculations ---
    generation = calculate_generation(kwp, location, orientation)
    monthly_gen = calculate_monthly_generation(generation["realistic"])
    monthly_cons = calculate_monthly_consumption(d_annual, heating_type)

    self_consumption = calculate_self_consumption(
        generation["realistic"], d_annual, daytime_share, battery_kwh,
        ev_annual_kwh=ev_annual_kwh
    )

    total_demand = self_consumption["total_demand"]

    financials_no_batt = calculate_annual_financials(
        total_demand,
        self_consumption["grid_import_no_batt"],
        self_consumption["e_export_no_batt"],
        grid_price_p,
        seg_price_p
    )

    financials_batt = calculate_annual_financials(
        total_demand,
        self_consumption["grid_import_with_batt"],
        self_consumption["e_export_batt"],
        grid_price_p,
        seg_price_p
    )

    cashflow_no_batt = calculate_multi_year_cashflow(
        pv_cost, battery_cost, total_demand, self_consumption,
        grid_price_p, seg_price_p, annual_growth, years, discount_rate,
        include_battery=False,
        finance_mode=finance_mode,
        loan_term=loan_term,
        loan_rate=loan_rate,
        deposit_pct=deposit_pct
    )

    cashflow_batt = calculate_multi_year_cashflow(
        pv_cost, battery_cost, total_demand, self_consumption,
        grid_price_p, seg_price_p, annual_growth, years, discount_rate,
        include_battery=True,
        finance_mode=finance_mode,
        loan_term=loan_term,
        loan_rate=loan_rate,
        deposit_pct=deposit_pct
    )

    # --- Summary Cards ---
    st.header("Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Realistic Annual Generation", f"{generation['realistic']:,.0f} kWh")
        st.metric("Theoretical Maximum", f"{generation['theoretical']:,.0f} kWh")
    with col2:
        st.metric("Effective Capacity Factor", f"{generation['capacity_factor']:.1%}")
        st.metric("kWh per kWp", f"{generation['kwh_per_kwp']:,.0f}")
    with col3:
        if battery_kwh > 0:
            st.metric("Annual Export Income", f"£{financials_batt['income_export']:,.0f}")
            st.metric("Annual Net Savings", f"£{financials_batt['net_saving']:,.0f}")
        else:
            st.metric("Annual Export Income", f"£{financials_no_batt['income_export']:,.0f}")
            st.metric("Annual Net Savings", f"£{financials_no_batt['net_saving']:,.0f}")

    col4, col5, col6 = st.columns(3)
    with col4:
        payback = cashflow_batt['payback_years'] if battery_kwh > 0 else cashflow_no_batt['payback_years']
        if payback:
            st.metric("Payback Period", f"{payback} years")
        else:
            st.metric("Payback Period", f">{years} years")
    with col5:
        npv = cashflow_batt['npv'] if battery_kwh > 0 else cashflow_no_batt['npv']
        st.metric("NPV", f"£{npv:,.0f}")
    with col6:
        total_cost = pv_cost + (battery_cost if battery_kwh > 0 else 0)
        st.metric("Total Install Cost", f"£{total_cost:,.0f}")

    # Show consumption breakdown if electric heating or EV
    if heating_type != "Gas/Oil boiler" or has_ev:
        st.subheader("Consumption Breakdown")
        col_cons1, col_cons2, col_cons3 = st.columns(3)
        with col_cons1:
            st.metric("Base Electricity", f"{d_annual_base:,.0f} kWh")
        with col_cons2:
            if heating_type != "Gas/Oil boiler":
                st.metric(f"With {heating_type}", f"{d_annual:,.0f} kWh")
            else:
                st.metric("Household Total", f"{d_annual:,.0f} kWh")
        with col_cons3:
            if has_ev:
                st.metric("EV Charging", f"{ev_annual_kwh:,.0f} kWh/year")
                st.caption(f"({daily_miles} miles/day)")

    # Show EV solar charging if applicable
    if has_ev and battery_kwh > 0:
        st.subheader("EV Charging from Solar")
        col_ev1, col_ev2, col_ev3 = st.columns(3)
        with col_ev1:
            st.metric("EV from Solar/Battery", f"{self_consumption['ev_from_solar']:,.0f} kWh")
        with col_ev2:
            st.metric("EV from Grid", f"{self_consumption['ev_from_grid']:,.0f} kWh")
        with col_ev3:
            ev_solar_pct = (self_consumption['ev_from_solar'] / ev_annual_kwh * 100) if ev_annual_kwh > 0 else 0
            st.metric("Solar EV Charging %", f"{ev_solar_pct:.0f}%")

    # Show financing details if in finance mode
    if finance_mode:
        cashflow = cashflow_batt if battery_kwh > 0 else cashflow_no_batt
        st.subheader("Financing Details")
        col_fin1, col_fin2, col_fin3, col_fin4, col_fin5 = st.columns(5)
        with col_fin1:
            st.metric("Deposit", f"£{cashflow['deposit_amount']:,.0f}")
        with col_fin2:
            st.metric("Loan Amount", f"£{cashflow['loan_amount']:,.0f}")
        with col_fin3:
            st.metric("Annual Payment", f"£{cashflow['annual_loan_payment']:,.0f}")
        with col_fin4:
            st.metric("Loan Term", f"{loan_term} years @ {loan_rate}%")
        with col_fin5:
            st.metric("Total Interest", f"£{cashflow['total_interest']:,.0f}")

    # --- Explanatory Text ---
    st.info("""
    **Understanding the Numbers:**
    - *Peak (kWp) is the size of the engine; UK weather determines how often it runs at full power.*
    - *UK capacity factors typically 10-13% -> realistic generation far below theoretical maximum.*
    - *Battery increases self-consumption; SEG pays less than grid electricity costs, so using your own power is more valuable than exporting.*
    """)

    # --- Charts ---
    st.header("Charts")

    # Chart 1: Theoretical vs Realistic Generation
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Theoretical vs Realistic Generation")
        fig1 = go.Figure(data=[
            go.Bar(
                x=["Theoretical Max", "Realistic (Weather-Adjusted)"],
                y=[generation["theoretical"], generation["realistic"]],
                marker_color=["#FF6B6B", "#4ECDC4"]
            )
        ])
        fig1.update_layout(
            yaxis_title="kWh/year",
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Monthly Generation vs Consumption
    with col_chart2:
        st.subheader("Monthly Generation vs Consumption")
        df_monthly = pd.DataFrame({
            "Month": MONTH_NAMES,
            "Generation": monthly_gen,
            "Consumption": monthly_cons
        })
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_monthly["Month"], y=df_monthly["Generation"],
            name="Solar Generation", line=dict(color="#FFD93D", width=3)
        ))
        fig2.add_trace(go.Scatter(
            x=df_monthly["Month"], y=df_monthly["Consumption"],
            name="Consumption", line=dict(color="#6BCB77", width=3)
        ))
        fig2.update_layout(
            yaxis_title="kWh",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Energy Flow
    st.subheader("Annual Energy Flow")

    if battery_kwh > 0:
        energy_data = {
            "Category": ["Immediate Use", "Stored Use", "Export", "Grid Supply"],
            "kWh": [
                self_consumption["e_self_direct"],
                self_consumption["e_self_batt"],
                self_consumption["e_export_batt"],
                self_consumption["grid_import_with_batt"]
            ]
        }
    else:
        energy_data = {
            "Category": ["Immediate Use", "Stored Use", "Export", "Grid Supply"],
            "kWh": [
                self_consumption["e_self_direct"],
                0,
                self_consumption["e_export_no_batt"],
                self_consumption["grid_import_no_batt"]
            ]
        }

    df_energy = pd.DataFrame(energy_data)
    fig3 = px.bar(
        df_energy,
        x="Category",
        y="kWh",
        color="Category",
        color_discrete_sequence=["#4ECDC4", "#9B59B6", "#FFD93D", "#E74C3C"]
    )
    fig3.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig3, use_container_width=True)

    # Chart 4: Cumulative Cashflow
    if finance_mode:
        st.subheader("Cumulative Cashflow Over Time (with Loan Payments)")
    else:
        st.subheader("Cumulative Cashflow Over Time")

    years_list = list(range(1, years + 1))
    df_cashflow = pd.DataFrame({
        "Year": years_list,
        "PV Only": cashflow_no_batt["cumulative_cashflow"],
        "PV + Battery": cashflow_batt["cumulative_cashflow"]
    })

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df_cashflow["Year"], y=df_cashflow["PV Only"],
        name="PV Only", line=dict(color="#3498DB", width=3)
    ))
    fig4.add_trace(go.Scatter(
        x=df_cashflow["Year"], y=df_cashflow["PV + Battery"],
        name="PV + Battery", line=dict(color="#9B59B6", width=3)
    ))
    fig4.add_hline(y=0, line_dash="dash", line_color="gray")

    # Add vertical line at end of loan term if financing
    if finance_mode:
        fig4.add_vline(
            x=loan_term, line_dash="dot", line_color="orange",
            annotation_text="Loan paid off",
            annotation_position="top right"
        )

    fig4.update_layout(
        xaxis_title="Year",
        yaxis_title="Cumulative Cashflow (£)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400
    )
    st.plotly_chart(fig4, use_container_width=True)

    # --- Detailed Comparison Table ---
    st.header("Detailed Comparison")

    comparison_data = {
        "Metric": [
            "Annual Generation (kWh)",
            "Self-Consumed Direct (kWh)",
            "Battery Self-Consumption (kWh)",
            "Export (kWh)",
            "Grid Import (kWh)",
            "Year 1 Export Income (£)",
            "Year 1 Net Savings (£)",
            "Total Install Cost (£)",
            "Payback Period (years)",
            f"NPV @ {discount_rate}% discount (£)"
        ],
        "PV Only": [
            f"{generation['realistic']:,.0f}",
            f"{self_consumption['e_self_direct']:,.0f}",
            "0",
            f"{self_consumption['e_export_no_batt']:,.0f}",
            f"{self_consumption['grid_import_no_batt']:,.0f}",
            f"£{financials_no_batt['income_export']:,.0f}",
            f"£{financials_no_batt['net_saving']:,.0f}",
            f"£{pv_cost:,}",
            f"{cashflow_no_batt['payback_years']}" if cashflow_no_batt['payback_years'] else f">{years}",
            f"£{cashflow_no_batt['npv']:,.0f}"
        ],
        "PV + Battery": [
            f"{generation['realistic']:,.0f}",
            f"{self_consumption['e_self_direct']:,.0f}",
            f"{self_consumption['e_self_batt']:,.0f}",
            f"{self_consumption['e_export_batt']:,.0f}",
            f"{self_consumption['grid_import_with_batt']:,.0f}",
            f"£{financials_batt['income_export']:,.0f}",
            f"£{financials_batt['net_saving']:,.0f}",
            f"£{pv_cost + battery_cost:,}",
            f"{cashflow_batt['payback_years']}" if cashflow_batt['payback_years'] else f">{years}",
            f"£{cashflow_batt['npv']:,.0f}"
        ]
    }

    df_comparison = pd.DataFrame(comparison_data)
    st.table(df_comparison)

    # Footer
    st.markdown("---")
    st.caption("This is an educational model, not a physically accurate irradiance simulation.")

with tab_quotation:
    st.header("Generate Customer Quotation")
    st.markdown("""
    Create a professional PDF quotation based on the current calculator settings.
    Fill in the customer details below and click Generate to download.
    """)

    st.subheader("Customer Details")
    col_cust1, col_cust2 = st.columns(2)
    with col_cust1:
        customer_name = st.text_input("Customer Name", value="Mr & Mrs Smith")
        company_name = st.text_input("Your Company Name", value="SolarTech Solutions")
    with col_cust2:
        customer_address = st.text_area("Customer Address", value="123 Solar Street\nSunnyville\nSN1 2AB", height=100)
        quote_ref = st.text_input("Quote Reference (optional)", value="", placeholder="Auto-generated if blank")

    st.subheader("Quotation Options")
    st.markdown("Select which quotations to generate:")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        gen_purchase = st.checkbox("Purchase (Upfront Payment)", value=True)
        gen_finance = st.checkbox("Finance (Loan)", value=True)
    with col_opt2:
        gen_no_ev = st.checkbox("Without EV", value=True)
        gen_with_ev = st.checkbox("With EV Charging", value=True)

    st.markdown("---")

    # Use current sidebar values for the quotation
    # These are defined in the calculator tab but accessible here
    try:
        current_settings = {
            "location": location,
            "orientation": orientation,
            "kwp": kwp,
            "battery_kwh": battery_kwh,
            "pv_cost": pv_cost,
            "battery_cost": battery_cost,
            "grid_price_p": grid_price_p,
            "seg_price_p": seg_price_p,
            "annual_growth": annual_growth,
            "heating_type": heating_type,
            "d_annual_base": d_annual_base,
            "daytime_share": daytime_share,
            "years": years,
            "discount_rate": discount_rate,
            "loan_term": loan_term,
            "loan_rate": loan_rate,
            "deposit_pct": deposit_pct,
            "daily_miles": daily_miles if has_ev else 30,
            "home_charging_pct": home_charging_pct if has_ev else 0.8,
        }

        st.subheader("Current System Configuration")
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            st.write(f"**Solar:** {kwp} kWp")
            st.write(f"**Battery:** {battery_kwh} kWh")
            st.write(f"**Location:** {location}")
        with col_cfg2:
            st.write(f"**PV Cost:** £{pv_cost:,}")
            st.write(f"**Battery Cost:** £{battery_cost:,}")
            st.write(f"**Total:** £{pv_cost + battery_cost:,}")
        with col_cfg3:
            st.write(f"**Heating:** {heating_type}")
            st.write(f"**Base Usage:** {d_annual_base:,} kWh")
            st.write(f"**Loan:** {loan_term}yr @ {loan_rate}%")

        st.markdown("---")

        if st.button("Generate Quotation PDFs", type="primary"):
            scenarios_to_generate = []

            if gen_purchase and gen_no_ev:
                scenarios_to_generate.append({
                    "name": "Purchase - No EV",
                    "filename": "quotation_purchase_no_ev.pdf",
                    "finance_mode": False,
                    "has_ev": False,
                })
            if gen_purchase and gen_with_ev:
                scenarios_to_generate.append({
                    "name": "Purchase - With EV",
                    "filename": "quotation_purchase_with_ev.pdf",
                    "finance_mode": False,
                    "has_ev": True,
                })
            if gen_finance and gen_no_ev:
                scenarios_to_generate.append({
                    "name": "Finance - No EV",
                    "filename": "quotation_finance_no_ev.pdf",
                    "finance_mode": True,
                    "has_ev": False,
                })
            if gen_finance and gen_with_ev:
                scenarios_to_generate.append({
                    "name": "Finance - With EV",
                    "filename": "quotation_finance_with_ev.pdf",
                    "finance_mode": True,
                    "has_ev": True,
                })

            if not scenarios_to_generate:
                st.warning("Please select at least one quotation option.")
            else:
                st.subheader("Generated Quotations")

                for scenario in scenarios_to_generate:
                    with st.spinner(f"Generating {scenario['name']}..."):
                        pdf_bytes = generate_quotation_pdf(
                            customer_name=customer_name,
                            customer_address=customer_address,
                            location=current_settings["location"],
                            orientation=current_settings["orientation"],
                            kwp=current_settings["kwp"],
                            battery_kwh=current_settings["battery_kwh"],
                            pv_cost=current_settings["pv_cost"],
                            battery_cost=current_settings["battery_cost"],
                            grid_price_p=current_settings["grid_price_p"],
                            seg_price_p=current_settings["seg_price_p"],
                            annual_growth=current_settings["annual_growth"],
                            heating_type=current_settings["heating_type"],
                            d_annual_base=current_settings["d_annual_base"],
                            daytime_share=current_settings["daytime_share"],
                            has_ev=scenario["has_ev"],
                            daily_miles=current_settings["daily_miles"],
                            home_charging_pct=current_settings["home_charging_pct"],
                            finance_mode=scenario["finance_mode"],
                            deposit_pct=current_settings["deposit_pct"],
                            loan_term=current_settings["loan_term"],
                            loan_rate=current_settings["loan_rate"],
                            years=current_settings["years"],
                            discount_rate=current_settings["discount_rate"],
                            company_name=company_name,
                            quote_ref=quote_ref if quote_ref else None
                        )

                        st.download_button(
                            label=f"Download: {scenario['name']}",
                            data=pdf_bytes,
                            file_name=scenario["filename"],
                            mime="application/pdf",
                            key=scenario["filename"]
                        )

                st.success(f"Generated {len(scenarios_to_generate)} quotation(s)!")

    except NameError:
        st.warning("Please configure your system in the Calculator tab first. The sidebar inputs need to be set before generating quotations.")
