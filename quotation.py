"""PDF Quotation Generator for Solar Installation."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Line, String, Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from io import BytesIO
from datetime import datetime

from constants import HEATING_TYPES, MONTHLY_FRACTIONS, MONTH_NAMES
from utils import (
    calculate_generation,
    calculate_monthly_consumption,
    calculate_self_consumption,
    calculate_annual_financials,
    calculate_multi_year_cashflow,
    calculate_ev_consumption,
    adjust_consumption_for_heating,
    calculate_monthly_generation
)


def create_cashflow_chart(cumulative_cashflow: list, payback_year: int, years: int, finance_mode: bool, loan_term: int = 0) -> Drawing:
    """Create a cumulative cashflow chart with break-even point highlighted."""

    drawing = Drawing(170*mm, 80*mm)

    # Chart area
    chart = LinePlot()
    chart.x = 15*mm
    chart.y = 15*mm
    chart.width = 145*mm
    chart.height = 55*mm

    # Prepare data - include year 0
    data = [[(0, cumulative_cashflow[0] if cumulative_cashflow else 0)]]
    for i, val in enumerate(cumulative_cashflow):
        data[0].append((i + 1, val))

    chart.data = data

    # Line styling
    chart.lines[0].strokeColor = colors.HexColor('#2E86AB')
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = makeMarker('Circle', size=3)

    # X axis
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = years
    chart.xValueAxis.valueStep = 5
    chart.xValueAxis.labels.fontSize = 8

    # Y axis
    min_val = min(cumulative_cashflow)
    max_val = max(cumulative_cashflow)
    chart.yValueAxis.valueMin = min_val - abs(min_val) * 0.1
    chart.yValueAxis.valueMax = max_val + abs(max_val) * 0.1
    chart.yValueAxis.labels.fontSize = 8
    chart.yValueAxis.labelTextFormat = '£%d'

    drawing.add(chart)

    # Add zero line
    zero_y = chart.y + chart.height * (0 - chart.yValueAxis.valueMin) / (chart.yValueAxis.valueMax - chart.yValueAxis.valueMin)
    if chart.y <= zero_y <= chart.y + chart.height:
        zero_line = Line(chart.x, zero_y, chart.x + chart.width, zero_y)
        zero_line.strokeColor = colors.grey
        zero_line.strokeDashArray = [3, 3]
        zero_line.strokeWidth = 1
        drawing.add(zero_line)

    # Highlight break-even point
    if payback_year and payback_year <= years:
        breakeven_x = chart.x + chart.width * (payback_year / years)
        breakeven_val = cumulative_cashflow[payback_year - 1]
        breakeven_y = chart.y + chart.height * (breakeven_val - chart.yValueAxis.valueMin) / (chart.yValueAxis.valueMax - chart.yValueAxis.valueMin)

        # Vertical line at break-even
        be_line = Line(breakeven_x, chart.y, breakeven_x, breakeven_y)
        be_line.strokeColor = colors.HexColor('#4CAF50')
        be_line.strokeWidth = 1.5
        be_line.strokeDashArray = [2, 2]
        drawing.add(be_line)

        # Break-even marker
        marker = Rect(breakeven_x - 3, breakeven_y - 3, 6, 6)
        marker.fillColor = colors.HexColor('#4CAF50')
        marker.strokeColor = colors.white
        drawing.add(marker)

        # Break-even label
        be_label = String(breakeven_x + 3, breakeven_y + 5, f'Break-even: Year {payback_year}')
        be_label.fontSize = 8
        be_label.fillColor = colors.HexColor('#4CAF50')
        be_label.fontName = 'Helvetica-Bold'
        drawing.add(be_label)

    # Add loan payoff marker if financed
    if finance_mode and loan_term and loan_term < years:
        loan_x = chart.x + chart.width * (loan_term / years)
        loan_line = Line(loan_x, chart.y, loan_x, chart.y + chart.height)
        loan_line.strokeColor = colors.HexColor('#FF9800')
        loan_line.strokeWidth = 1
        loan_line.strokeDashArray = [4, 2]
        drawing.add(loan_line)

        loan_label = String(loan_x + 2, chart.y + chart.height - 10, f'Loan paid off')
        loan_label.fontSize = 7
        loan_label.fillColor = colors.HexColor('#FF9800')
        drawing.add(loan_label)

    # Title
    title = String(chart.x + chart.width / 2, chart.y + chart.height + 8*mm, 'Cumulative Savings Over Time')
    title.fontSize = 10
    title.fontName = 'Helvetica-Bold'
    title.textAnchor = 'middle'
    drawing.add(title)

    # X axis label
    x_label = String(chart.x + chart.width / 2, 3*mm, 'Year')
    x_label.fontSize = 8
    x_label.textAnchor = 'middle'
    drawing.add(x_label)

    return drawing


def create_energy_flow_chart(self_consumption: dict, battery_kwh: float) -> Drawing:
    """Create an energy flow bar chart."""

    drawing = Drawing(170*mm, 70*mm)

    chart = VerticalBarChart()
    chart.x = 20*mm
    chart.y = 12*mm
    chart.width = 130*mm
    chart.height = 45*mm

    if battery_kwh > 0:
        data = [[
            self_consumption["e_self_direct"],
            self_consumption["e_self_batt"],
            self_consumption["e_export_batt"],
            self_consumption["grid_import_with_batt"]
        ]]
        categories = ['Immediate\nUse', 'Stored\nUse', 'Export', 'Grid\nSupply']
    else:
        data = [[
            self_consumption["e_self_direct"],
            0,
            self_consumption["e_export_no_batt"],
            self_consumption["grid_import_no_batt"]
        ]]
        categories = ['Immediate\nUse', 'Stored\nUse', 'Export', 'Grid\nSupply']

    chart.data = data
    chart.categoryAxis.categoryNames = categories
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.dy = -5

    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labelTextFormat = '%d kWh'

    # Bar colors
    chart.bars[0].fillColor = colors.HexColor('#4ECDC4')
    chart.bars.symbol = None

    # Individual bar colors
    bar_colors = ['#4ECDC4', '#9B59B6', '#FFD93D', '#E74C3C']
    for i, color in enumerate(bar_colors):
        chart.bars[(0, i)].fillColor = colors.HexColor(color)

    drawing.add(chart)

    # Title
    title = String(chart.x + chart.width / 2, chart.y + chart.height + 8*mm, 'Annual Energy Flow')
    title.fontSize = 10
    title.fontName = 'Helvetica-Bold'
    title.textAnchor = 'middle'
    drawing.add(title)

    return drawing


def create_monthly_chart(generation: float, consumption_profile: list, d_annual: float) -> Drawing:
    """Create monthly generation vs consumption chart."""

    drawing = Drawing(170*mm, 70*mm)

    chart = LinePlot()
    chart.x = 15*mm
    chart.y = 12*mm
    chart.width = 145*mm
    chart.height = 45*mm

    # Monthly generation
    monthly_gen = [generation * frac for frac in MONTHLY_FRACTIONS]
    # Monthly consumption
    monthly_cons = [d_annual * frac for frac in consumption_profile]

    gen_data = [(i, val) for i, val in enumerate(monthly_gen)]
    cons_data = [(i, val) for i, val in enumerate(monthly_cons)]

    chart.data = [gen_data, cons_data]

    # Line styling
    chart.lines[0].strokeColor = colors.HexColor('#FFD93D')
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = makeMarker('Circle', size=3)
    chart.lines[0].symbol.fillColor = colors.HexColor('#FFD93D')

    chart.lines[1].strokeColor = colors.HexColor('#6BCB77')
    chart.lines[1].strokeWidth = 2
    chart.lines[1].symbol = makeMarker('Square', size=3)
    chart.lines[1].symbol.fillColor = colors.HexColor('#6BCB77')

    # X axis - months
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = 11
    chart.xValueAxis.valueStep = 1
    chart.xValueAxis.labels.fontSize = 7
    chart.xValueAxis.labelTextFormat = lambda x: MONTH_NAMES[int(x)] if 0 <= x < 12 else ''

    # Y axis
    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.labels.fontSize = 8
    chart.yValueAxis.labelTextFormat = '%d'

    drawing.add(chart)

    # Title
    title = String(chart.x + chart.width / 2, chart.y + chart.height + 8*mm, 'Monthly Generation vs Consumption (kWh)')
    title.fontSize = 10
    title.fontName = 'Helvetica-Bold'
    title.textAnchor = 'middle'
    drawing.add(title)

    # Legend
    legend_y = 3*mm
    # Generation legend
    gen_marker = Rect(chart.x + 30*mm, legend_y, 8, 8)
    gen_marker.fillColor = colors.HexColor('#FFD93D')
    drawing.add(gen_marker)
    gen_label = String(chart.x + 40*mm, legend_y + 1, 'Solar Generation')
    gen_label.fontSize = 7
    drawing.add(gen_label)

    # Consumption legend
    cons_marker = Rect(chart.x + 80*mm, legend_y, 8, 8)
    cons_marker.fillColor = colors.HexColor('#6BCB77')
    drawing.add(cons_marker)
    cons_label = String(chart.x + 90*mm, legend_y + 1, 'Consumption')
    cons_label.fontSize = 7
    drawing.add(cons_label)

    return drawing


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
            ["Total Cost of Finance:", f"£{cashflow['loan_amount'] + cashflow['total_interest']:,.0f}"],
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

    # --- Page Break for Charts ---
    elements.append(PageBreak())

    # --- Charts Section ---
    elements.append(Paragraph("Financial Projections", styles['SectionHeader']))

    # Cumulative Cashflow Chart with break-even highlight
    cashflow_chart = create_cashflow_chart(
        cashflow['cumulative_cashflow'],
        cashflow['payback_years'],
        years,
        finance_mode,
        loan_term if finance_mode else 0
    )
    elements.append(cashflow_chart)
    elements.append(Spacer(1, 5*mm))

    # Break-even callout box
    if cashflow['payback_years']:
        be_text = f"""
        <b>Break-even Analysis:</b> Your system pays for itself in <b>Year {cashflow['payback_years']}</b>.
        After this point, all savings go directly into your pocket. Over {years} years,
        your total benefit is projected to be <b>£{cashflow['cumulative_cashflow'][-1]:,.0f}</b>.
        """
    else:
        be_text = f"""
        <b>Break-even Analysis:</b> Based on current assumptions, payback extends beyond {years} years.
        Consider adjusting system size or financing options.
        """
    elements.append(Paragraph(be_text, styles['Normal']))
    elements.append(Spacer(1, 8*mm))

    # Energy Flow Chart
    elements.append(Paragraph("Energy Distribution", styles['SectionHeader']))
    energy_chart = create_energy_flow_chart(self_consumption, battery_kwh)
    elements.append(energy_chart)
    elements.append(Spacer(1, 5*mm))

    # Energy flow explanation
    if battery_kwh > 0:
        immediate = self_consumption["e_self_direct"]
        stored = self_consumption["e_self_batt"]
        total_self = immediate + stored
        self_consumption_pct = (total_self / generation['realistic'] * 100) if generation['realistic'] > 0 else 0
        energy_text = f"""
        <b>Self-Consumption:</b> {self_consumption_pct:.0f}% of your solar generation is used on-site
        ({immediate:,.0f} kWh immediate + {stored:,.0f} kWh from battery storage).
        The battery significantly increases your self-consumption, reducing grid dependency.
        """
    else:
        immediate = self_consumption["e_self_direct"]
        self_consumption_pct = (immediate / generation['realistic'] * 100) if generation['realistic'] > 0 else 0
        energy_text = f"""
        <b>Self-Consumption:</b> {self_consumption_pct:.0f}% of your solar generation is used directly.
        Adding battery storage would increase self-consumption and reduce grid imports.
        """
    elements.append(Paragraph(energy_text, styles['Normal']))
    elements.append(Spacer(1, 8*mm))

    # Monthly Generation vs Consumption Chart
    elements.append(Paragraph("Seasonal Performance", styles['SectionHeader']))
    consumption_profile = HEATING_TYPES.get(heating_type, {}).get("profile", MONTHLY_FRACTIONS)
    monthly_chart = create_monthly_chart(generation['realistic'], consumption_profile, d_annual)
    elements.append(monthly_chart)
    elements.append(Spacer(1, 5*mm))

    # Seasonal explanation
    if heating_type != "Gas/Oil boiler":
        seasonal_text = f"""
        <b>Seasonal Note:</b> With {heating_type.lower()}, your electricity consumption peaks in winter
        when solar generation is lowest. The battery helps bridge this gap, but some grid import
        is unavoidable during darker months. Summer generates significant surplus for export.
        """
    else:
        seasonal_text = """
        <b>Seasonal Note:</b> Solar generation peaks in summer (May-August) when it can exceed
        your consumption. The surplus is either stored in your battery or exported for income.
        Winter generation is lower but still contributes to your energy needs.
        """
    elements.append(Paragraph(seasonal_text, styles['Normal']))

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
