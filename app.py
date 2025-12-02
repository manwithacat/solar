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

st.set_page_config(
    page_title="UK Solar Economics Calculator",
    page_icon="☀️",
    layout="wide"
)

st.title("☀️ UK Solar Economics Calculator")

tab_calculator, tab_assumptions = st.tabs(["Calculator", "Assumptions & Sources"])

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
