"""PDF Quotation Generator for Solar Installation."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime

from constants import HEATING_TYPES
from utils import (
    calculate_generation,
    calculate_monthly_consumption,
    calculate_self_consumption,
    calculate_annual_financials,
    calculate_multi_year_cashflow,
    calculate_ev_consumption,
    adjust_consumption_for_heating
)


def generate_quotation_pdf(
    customer_name: str,
    customer_address: str,
    # System config
    location: str,
    orientation: str,
    kwp: float,
    battery_kwh: float,
    # Costs
    pv_cost: float,
    battery_cost: float,
    # Pricing
    grid_price_p: float,
    seg_price_p: float,
    annual_growth: float,
    # Demand
    heating_type: str,
    d_annual_base: float,
    daytime_share: float,
    # EV
    has_ev: bool,
    daily_miles: float = 30,
    home_charging_pct: float = 0.8,
    # Finance
    finance_mode: bool = False,
    deposit_pct: float = 25,
    loan_term: int = 10,
    loan_rate: float = 5.0,
    # Analysis
    years: int = 25,
    discount_rate: float = 3.0,
    # Branding
    company_name: str = "SolarTech Solutions",
    quote_ref: str = None
) -> bytes:
    """Generate a customer quotation PDF.

    Returns PDF as bytes.
    """

    # --- Calculations ---
    d_annual = adjust_consumption_for_heating(d_annual_base, heating_type)

    if has_ev:
        ev_consumption = calculate_ev_consumption(daily_miles, home_charging_pct)
        ev_annual_kwh = ev_consumption["annual_kwh"]
    else:
        ev_annual_kwh = 0

    generation = calculate_generation(kwp, location, orientation)

    self_consumption = calculate_self_consumption(
        generation["realistic"], d_annual, daytime_share, battery_kwh,
        ev_annual_kwh=ev_annual_kwh
    )

    total_demand = self_consumption["total_demand"]

    financials = calculate_annual_financials(
        total_demand,
        self_consumption["grid_import_with_batt"] if battery_kwh > 0 else self_consumption["grid_import_no_batt"],
        self_consumption["e_export_batt"] if battery_kwh > 0 else self_consumption["e_export_no_batt"],
        grid_price_p,
        seg_price_p
    )

    cashflow = calculate_multi_year_cashflow(
        pv_cost, battery_cost, total_demand, self_consumption,
        grid_price_p, seg_price_p, annual_growth, years, discount_rate,
        include_battery=(battery_kwh > 0),
        finance_mode=finance_mode,
        loan_term=loan_term,
        loan_rate=loan_rate,
        deposit_pct=deposit_pct
    )

    # --- PDF Generation ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name='CompanyName',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E86AB'),
        spaceAfter=5*mm
    ))
    styles.add(ParagraphStyle(
        name='QuoteTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        alignment=TA_CENTER,
        spaceBefore=5*mm,
        spaceAfter=10*mm
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E86AB'),
        spaceBefore=8*mm,
        spaceAfter=4*mm
    ))
    styles.add(ParagraphStyle(
        name='BodyTextRight',
        parent=styles['Normal'],
        alignment=TA_RIGHT
    ))
    styles.add(ParagraphStyle(
        name='Highlight',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2E86AB'),
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    ))

    elements = []

    # --- Header ---
    if quote_ref is None:
        quote_ref = f"Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    header_data = [
        [Paragraph(f"<b>{company_name}</b>", styles['CompanyName']),
         Paragraph(f"Quote Ref: {quote_ref}<br/>Date: {datetime.now().strftime('%d %B %Y')}", styles['BodyTextRight'])]
    ]
    header_table = Table(header_data, colWidths=[100*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))

    # --- Customer Details ---
    elements.append(Paragraph("Customer Quotation", styles['QuoteTitle']))

    customer_data = [
        ["Customer:", customer_name],
        ["Address:", customer_address],
    ]
    customer_table = Table(customer_data, colWidths=[30*mm, 140*mm])
    customer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(customer_table)

    # --- System Specification ---
    elements.append(Paragraph("System Specification", styles['SectionHeader']))

    system_data = [
        ["Solar Panel Capacity:", f"{kwp} kWp"],
        ["Battery Storage:", f"{battery_kwh} kWh" if battery_kwh > 0 else "Not included"],
        ["Location:", location],
        ["Roof Orientation:", orientation],
        ["Expected Annual Generation:", f"{generation['realistic']:,.0f} kWh"],
        ["Capacity Factor:", f"{generation['capacity_factor']:.1%}"],
    ]
    system_table = Table(system_data, colWidths=[60*mm, 110*mm])
    system_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(system_table)

    # --- Your Energy Profile ---
    elements.append(Paragraph("Your Energy Profile", styles['SectionHeader']))

    profile_data = [
        ["Heating Type:", heating_type],
        ["Base Electricity Usage:", f"{d_annual_base:,.0f} kWh/year"],
        ["Total Household Consumption:", f"{d_annual:,.0f} kWh/year"],
    ]
    if has_ev:
        profile_data.extend([
            ["EV Daily Mileage:", f"{daily_miles} miles"],
            ["EV Charging (Home):", f"{ev_annual_kwh:,.0f} kWh/year"],
            ["Total Demand (incl. EV):", f"{total_demand:,.0f} kWh/year"],
        ])

    profile_table = Table(profile_data, colWidths=[60*mm, 110*mm])
    profile_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(profile_table)

    # --- Pricing ---
    elements.append(Paragraph("Investment", styles['SectionHeader']))

    total_cost = pv_cost + (battery_cost if battery_kwh > 0 else 0)

    pricing_data = [
        ["Solar PV System:", f"£{pv_cost:,.0f}"],
    ]
    if battery_kwh > 0:
        pricing_data.append(["Battery Storage:", f"£{battery_cost:,.0f}"])
    pricing_data.append(["", ""])
    pricing_data.append(["Total System Cost:", f"£{total_cost:,.0f}"])

    pricing_table = Table(pricing_data, colWidths=[60*mm, 110*mm])
    pricing_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -2), 0.25, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(pricing_table)

    # --- Payment Option ---
    elements.append(Paragraph("Payment Option", styles['SectionHeader']))

    if finance_mode:
        payment_data = [
            ["Payment Method:", "Finance"],
            ["Deposit:", f"£{cashflow['deposit_amount']:,.0f} ({deposit_pct}%)"],
            ["Loan Amount:", f"£{cashflow['loan_amount']:,.0f}"],
            ["Loan Term:", f"{loan_term} years"],
            ["Interest Rate:", f"{loan_rate}% APR"],
            ["Monthly Payment:", f"£{cashflow['annual_loan_payment']/12:,.0f}"],
            ["Annual Payment:", f"£{cashflow['annual_loan_payment']:,.0f}"],
            ["Total Interest:", f"£{cashflow['total_interest']:,.0f}"],
            ["Total Cost of Finance:", f"£{cashflow['deposit_amount'] + cashflow['loan_amount'] + cashflow['total_interest']:,.0f}"],
        ]
    else:
        payment_data = [
            ["Payment Method:", "Upfront Purchase"],
            ["Amount Due:", f"£{total_cost:,.0f}"],
        ]

    payment_table = Table(payment_data, colWidths=[60*mm, 110*mm])
    payment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(payment_table)

    # --- Savings Summary ---
    elements.append(Paragraph("Projected Savings", styles['SectionHeader']))

    savings_data = [
        ["Year 1 Savings:", f"£{financials['net_saving']:,.0f}"],
        ["Year 1 Export Income:", f"£{financials['income_export']:,.0f}"],
        ["Payback Period:", f"{cashflow['payback_years']} years" if cashflow['payback_years'] else f">{years} years"],
        [f"NPV ({years} years @ {discount_rate}%):", f"£{cashflow['npv']:,.0f}"],
    ]

    # Add cumulative savings at key milestones
    for milestone in [10, 15, 25]:
        if milestone <= years:
            cum_saving = cashflow['cumulative_cashflow'][milestone-1]
            savings_data.append([f"Cumulative Benefit (Year {milestone}):", f"£{cum_saving:,.0f}"])

    savings_table = Table(savings_data, colWidths=[60*mm, 110*mm])
    savings_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f5e9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#4CAF50')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#4CAF50')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(savings_table)

    # --- EV Benefits (if applicable) ---
    if has_ev and battery_kwh > 0:
        elements.append(Paragraph("EV Charging Benefits", styles['SectionHeader']))

        ev_solar_pct = (self_consumption['ev_from_solar'] / ev_annual_kwh * 100) if ev_annual_kwh > 0 else 0
        ev_grid_cost = self_consumption['ev_from_grid'] * (grid_price_p / 100)
        ev_solar_saving = self_consumption['ev_from_solar'] * (grid_price_p / 100)

        ev_data = [
            ["EV Charging from Solar/Battery:", f"{self_consumption['ev_from_solar']:,.0f} kWh ({ev_solar_pct:.0f}%)"],
            ["EV Charging from Grid:", f"{self_consumption['ev_from_grid']:,.0f} kWh"],
            ["Annual EV Fuel Saving:", f"£{ev_solar_saving:,.0f}"],
        ]

        ev_table = Table(ev_data, colWidths=[60*mm, 110*mm])
        ev_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e3f2fd')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#2196F3')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#2196F3')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ev_table)

    # --- Assumptions ---
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("Assumptions & Notes", styles['SectionHeader']))

    assumptions_text = f"""
    <font size=9>
    This quotation is based on the following assumptions:<br/>
    - Electricity price: {grid_price_p}p/kWh with {annual_growth}% annual increase<br/>
    - Export tariff (SEG): {seg_price_p}p/kWh<br/>
    - Daytime usage: {daytime_share*100:.0f}% of consumption during daylight hours<br/>
    - Analysis period: {years} years<br/>
    <br/>
    Actual savings will depend on your usage patterns, weather conditions, and future energy prices.
    This quotation is valid for 30 days from the date shown above.
    </font>
    """
    elements.append(Paragraph(assumptions_text, styles['Normal']))

    # --- Footer ---
    elements.append(Spacer(1, 15*mm))
    elements.append(Paragraph(
        f"{company_name} | Quotation generated on {datetime.now().strftime('%d/%m/%Y at %H:%M')}",
        styles['Footer']
    ))

    # Build PDF
    doc.build(elements)

    return buffer.getvalue()


def generate_sample_quotations():
    """Generate 4 sample quotation PDFs for different scenarios."""

    # Common parameters
    common_params = {
        "customer_name": "Mr & Mrs Smith",
        "customer_address": "123 Solar Street, Sunnyville, SN1 2AB",
        "location": "South England",
        "orientation": "Ideal (South)",
        "kwp": 4.0,
        "battery_kwh": 5.0,
        "pv_cost": 6000,
        "battery_cost": 4000,
        "grid_price_p": 28,
        "seg_price_p": 15,
        "annual_growth": 3.0,
        "heating_type": "Gas/Oil boiler",
        "d_annual_base": 3500,
        "daytime_share": 0.4,
        "years": 25,
        "discount_rate": 3.0,
        "company_name": "SolarTech Solutions"
    }

    scenarios = [
        {
            "name": "purchase_no_ev",
            "title": "Purchase - No EV",
            "finance_mode": False,
            "has_ev": False,
        },
        {
            "name": "purchase_with_ev",
            "title": "Purchase - With EV",
            "finance_mode": False,
            "has_ev": True,
            "daily_miles": 30,
            "home_charging_pct": 0.8,
        },
        {
            "name": "finance_no_ev",
            "title": "Finance - No EV",
            "finance_mode": True,
            "deposit_pct": 25,
            "loan_term": 10,
            "loan_rate": 5.0,
            "has_ev": False,
        },
        {
            "name": "finance_with_ev",
            "title": "Finance - With EV",
            "finance_mode": True,
            "deposit_pct": 25,
            "loan_term": 10,
            "loan_rate": 5.0,
            "has_ev": True,
            "daily_miles": 30,
            "home_charging_pct": 0.8,
        },
    ]

    generated_files = []

    for scenario in scenarios:
        params = {**common_params, **scenario}
        params.pop("name")
        params.pop("title")

        pdf_bytes = generate_quotation_pdf(**params)

        filename = f"quotation_{scenario['name']}.pdf"
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)

        generated_files.append(filename)
        print(f"Generated: {filename}")

    return generated_files


if __name__ == "__main__":
    generate_sample_quotations()
