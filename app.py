"""Solar Economics Streamlit Dashboard.

An interactive dashboard for modelling the economic benefits of
residential solar PV + battery installation in the UK.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from constants import MONTH_NAMES
from utils import (
    calculate_generation,
    calculate_monthly_generation,
    calculate_monthly_consumption,
    calculate_self_consumption,
    calculate_annual_financials,
    calculate_multi_year_cashflow
)

st.set_page_config(
    page_title="UK Solar Economics Calculator",
    page_icon="☀️",
    layout="wide"
)

st.title("☀️ UK Solar Economics Calculator")
st.markdown("""
This dashboard models the realistic economic benefits of a residential solar PV + battery
installation in the UK. It contrasts **peak (kWp) output assumptions** with
**weather-based capacity-factor-adjusted energy generation**.
""")

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

st.sidebar.header("Demand Inputs")

d_annual = st.sidebar.slider(
    "Annual household electricity usage (kWh)",
    min_value=1500, max_value=8000, value=3500, step=100
)

daytime_share = st.sidebar.slider(
    "Daytime usage share (%)",
    min_value=20, max_value=70, value=40, step=5
) / 100

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
monthly_cons = calculate_monthly_consumption(d_annual)

self_consumption = calculate_self_consumption(
    generation["realistic"], d_annual, daytime_share, battery_kwh
)

financials_no_batt = calculate_annual_financials(
    d_annual,
    self_consumption["grid_import_no_batt"],
    self_consumption["e_export_no_batt"],
    grid_price_p,
    seg_price_p
)

financials_batt = calculate_annual_financials(
    d_annual,
    self_consumption["grid_import_with_batt"],
    self_consumption["e_export_batt"],
    grid_price_p,
    seg_price_p
)

cashflow_no_batt = calculate_multi_year_cashflow(
    pv_cost, battery_cost, d_annual, self_consumption,
    grid_price_p, seg_price_p, annual_growth, years, discount_rate,
    include_battery=False
)

cashflow_batt = calculate_multi_year_cashflow(
    pv_cost, battery_cost, d_annual, self_consumption,
    grid_price_p, seg_price_p, annual_growth, years, discount_rate,
    include_battery=True
)

# --- Summary Cards ---
st.header("📊 Summary")

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

# --- Explanatory Text ---
st.info("""
💡 **Understanding the Numbers:**
- *Peak (kWp) is the size of the engine; UK weather determines how often it runs at full power.*
- *UK capacity factors typically 10–13% → realistic generation far below theoretical maximum.*
- *Battery increases self-consumption; SEG pays less than grid electricity costs, so using your own power is more valuable than exporting.*
""")

# --- Charts ---
st.header("📈 Charts")

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
        "Category": ["Self-Consumed (Direct)", "Battery Discharge", "Export", "Grid Import"],
        "kWh": [
            self_consumption["e_self_direct"],
            self_consumption["e_self_batt"],
            self_consumption["e_export_batt"],
            self_consumption["grid_import_with_batt"]
        ]
    }
else:
    energy_data = {
        "Category": ["Self-Consumed (Direct)", "Battery Discharge", "Export", "Grid Import"],
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
fig4.update_layout(
    xaxis_title="Year",
    yaxis_title="Cumulative Cashflow (£)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=400
)
st.plotly_chart(fig4, use_container_width=True)

# --- Detailed Comparison Table ---
st.header("📋 Detailed Comparison")

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
