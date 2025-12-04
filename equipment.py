"""Equipment pricing and configuration module.

Provides equipment data and system configuration options
based on the product pricing snapshot.
"""

# Panel options (assuming ~460W Aiko panels)
PANEL_OPTIONS = {
    "6 x 460W Aiko panels (2.76 kWp)": {
        "count": 6,
        "watts_each": 460,
        "kwp": 2.76,
        "price": 3500,  # Estimated from package breakdown
        "description": "Entry-level system, suitable for smaller roofs"
    },
    "10 x 460W Aiko panels (4.6 kWp)": {
        "count": 10,
        "watts_each": 460,
        "kwp": 4.6,
        "price": 4500,  # Estimated from package breakdown
        "description": "Standard system, most popular choice"
    },
    "13 x 460W Aiko panels (5.98 kWp)": {
        "count": 13,
        "watts_each": 460,
        "kwp": 5.98,
        "price": 5500,  # Estimated from package breakdown
        "description": "Premium system, maximum generation"
    },
}

# Inverter options
INVERTER_OPTIONS = {
    "Sungrow 3.6 kW string inverter": {
        "type": "string",
        "power_kw": 3.6,
        "warranty_years": 10,
        "price": 800,
        "description": "10-year warranty, suits up to 10 panels",
        "max_panels": 10
    },
    "Sungrow 5 kW string inverter": {
        "type": "string",
        "power_kw": 5.0,
        "warranty_years": 10,
        "price": 950,
        "description": "10-year warranty, suits larger systems",
        "max_panels": 15
    },
    "Enphase micro-inverters (per panel)": {
        "type": "micro",
        "power_kw": 0.46,  # Per panel
        "warranty_years": 25,
        "price_per_panel": 180,
        "price": 0,  # Calculated based on panel count
        "description": "25-year warranty, panel-level optimisation",
        "max_panels": 20
    },
}

# Battery options
BATTERY_OPTIONS = {
    "No battery": {
        "capacity_kwh": 0,
        "price": 0,
        "warranty_years": 0,
        "description": "Export-only system",
        "includes_inverter": False
    },
    "2.6 kWh battery": {
        "capacity_kwh": 2.6,
        "price": 2400,  # Estimated component price
        "warranty_years": 10,
        "description": "Entry-level storage",
        "includes_inverter": False
    },
    "5.0 kWh Enphase battery": {
        "capacity_kwh": 5.0,
        "price": 3800,
        "warranty_years": 15,
        "description": "15-year warranty, premium option",
        "includes_inverter": False
    },
    "5.2 kWh battery": {
        "capacity_kwh": 5.2,
        "price": 3200,
        "warranty_years": 10,
        "description": "Standard home storage",
        "includes_inverter": False
    },
    "6.4 kWh Sungrow battery": {
        "capacity_kwh": 6.4,
        "price": 4315,
        "warranty_years": 10,
        "description": "Includes hybrid inverter, suits up to 10 panels",
        "includes_inverter": True
    },
    "9.5 kWh battery": {
        "capacity_kwh": 9.5,
        "price": 4800,
        "warranty_years": 10,
        "description": "Large capacity for higher usage",
        "includes_inverter": False
    },
    "9.6 kWh Sungrow battery": {
        "capacity_kwh": 9.6,
        "price": 5101,
        "warranty_years": 10,
        "description": "Includes hybrid inverter, suits up to 15 panels",
        "includes_inverter": True
    },
    "12.8 kWh Sungrow battery": {
        "capacity_kwh": 12.8,
        "price": 5886,
        "warranty_years": 10,
        "description": "Includes hybrid inverter, suits 15+ panels",
        "includes_inverter": True
    },
}

# EV Charger options
EV_CHARGER_OPTIONS = {
    "No EV charger": {
        "power_kw": 0,
        "price": 0,
        "phase": None,
        "description": "No charger included"
    },
    "Wallbox 7.4 kW (1-phase)": {
        "power_kw": 7.4,
        "price": 1945,
        "phase": 1,
        "description": "Entry-level home charger, ~5m cable"
    },
    "Wallbox 11 kW (3-phase)": {
        "power_kw": 11,
        "price": 2110,
        "phase": 3,
        "description": "Mid-range charger, requires 3-phase"
    },
    "Wallbox 22 kW (3-phase)": {
        "power_kw": 22,
        "price": 2148,
        "phase": 3,
        "description": "High-power charger, requires 3-phase"
    },
}

# Pre-configured packages
PACKAGES = {
    "Package 1 – Entry (6 panels + 2.6 kWh)": {
        "panels": "6 x 460W Aiko panels (2.76 kWp)",
        "inverter": "Sungrow 3.6 kW string inverter",
        "battery": "2.6 kWh battery",
        "ev_charger": "No EV charger",
        "package_price": 6392,
        "description": "Entry-level solar + battery system"
    },
    "Package 2 – Standard (10 panels + 5.2 kWh)": {
        "panels": "10 x 460W Aiko panels (4.6 kWp)",
        "inverter": "Sungrow 3.6 kW string inverter",
        "battery": "5.2 kWh battery",
        "ev_charger": "No EV charger",
        "package_price": 6846,
        "description": "Most popular choice"
    },
    "Package 3 – Premium (13 panels + 9.5 kWh)": {
        "panels": "13 x 460W Aiko panels (5.98 kWp)",
        "inverter": "Sungrow 5 kW string inverter",
        "battery": "9.5 kWh battery",
        "ev_charger": "No EV charger",
        "package_price": 8420,
        "description": "Maximum generation and storage"
    },
    "Sungrow Package (10 panels + 6.4 kWh)": {
        "panels": "10 x 460W Aiko panels (4.6 kWp)",
        "inverter": "Sungrow 3.6 kW string inverter",
        "battery": "6.4 kWh Sungrow battery",
        "ev_charger": "No EV charger",
        "package_price": 7749,
        "description": "Sungrow hybrid system"
    },
    "Sungrow + EV Package": {
        "panels": "10 x 460W Aiko panels (4.6 kWp)",
        "inverter": "Sungrow 3.6 kW string inverter",
        "battery": "6.4 kWh Sungrow battery",
        "ev_charger": "Wallbox 7.4 kW (1-phase)",
        "package_price": 8699,
        "description": "Complete solar + battery + EV solution"
    },
    "Enphase Premium + EV Package": {
        "panels": "10 x 460W Aiko panels (4.6 kWp)",
        "inverter": "Enphase micro-inverters (per panel)",
        "battery": "5.0 kWh Enphase battery",
        "ev_charger": "Wallbox 7.4 kW (1-phase)",
        "package_price": 10399,
        "description": "Premium Enphase system with 25yr warranty"
    },
    "Custom Configuration": {
        "panels": None,
        "inverter": None,
        "battery": None,
        "ev_charger": None,
        "package_price": None,
        "description": "Build your own system"
    },
}

# Installation costs (labour, scaffolding, etc.)
INSTALLATION_COSTS = {
    "base": 1200,  # Base installation
    "per_panel": 50,  # Additional per panel
    "battery_install": 300,  # Battery installation
    "ev_charger_install": 0,  # Included in EV charger price
    "scaffolding": 400,  # Standard scaffolding
}


def calculate_component_total(panels_key, inverter_key, battery_key, ev_charger_key):
    """Calculate total cost from individual components."""
    total = 0
    breakdown = {}

    # Panels
    if panels_key and panels_key in PANEL_OPTIONS:
        panel_data = PANEL_OPTIONS[panels_key]
        breakdown["panels"] = panel_data["price"]
        total += panel_data["price"]
        panel_count = panel_data["count"]
    else:
        panel_count = 0
        breakdown["panels"] = 0

    # Inverter
    if inverter_key and inverter_key in INVERTER_OPTIONS:
        inv_data = INVERTER_OPTIONS[inverter_key]
        if inv_data["type"] == "micro":
            # Price per panel for micro-inverters
            inv_price = inv_data["price_per_panel"] * panel_count
        else:
            inv_price = inv_data["price"]
        breakdown["inverter"] = inv_price
        total += inv_price
    else:
        breakdown["inverter"] = 0

    # Battery
    if battery_key and battery_key in BATTERY_OPTIONS:
        batt_data = BATTERY_OPTIONS[battery_key]
        breakdown["battery"] = batt_data["price"]
        total += batt_data["price"]

        # If battery includes inverter, subtract standalone inverter cost
        if batt_data.get("includes_inverter") and breakdown["inverter"] > 0:
            # Hybrid battery includes inverter, so we don't double-count
            # But keep the display separate for transparency
            pass
    else:
        breakdown["battery"] = 0

    # EV Charger
    if ev_charger_key and ev_charger_key in EV_CHARGER_OPTIONS:
        ev_data = EV_CHARGER_OPTIONS[ev_charger_key]
        breakdown["ev_charger"] = ev_data["price"]
        total += ev_data["price"]
    else:
        breakdown["ev_charger"] = 0

    # Installation
    install_cost = INSTALLATION_COSTS["base"]
    install_cost += INSTALLATION_COSTS["per_panel"] * panel_count
    install_cost += INSTALLATION_COSTS["scaffolding"]
    if breakdown["battery"] > 0:
        install_cost += INSTALLATION_COSTS["battery_install"]

    breakdown["installation"] = install_cost
    total += install_cost

    breakdown["total"] = total

    return breakdown


def get_system_specs(panels_key, inverter_key, battery_key, ev_charger_key):
    """Get system specifications from component selections."""
    specs = {
        "kwp": 0,
        "panel_count": 0,
        "battery_kwh": 0,
        "inverter_type": None,
        "inverter_warranty": 0,
        "battery_warranty": 0,
        "ev_charger_kw": 0,
        "has_ev": False,
    }

    if panels_key and panels_key in PANEL_OPTIONS:
        panel_data = PANEL_OPTIONS[panels_key]
        specs["kwp"] = panel_data["kwp"]
        specs["panel_count"] = panel_data["count"]

    if inverter_key and inverter_key in INVERTER_OPTIONS:
        inv_data = INVERTER_OPTIONS[inverter_key]
        specs["inverter_type"] = inv_data["type"]
        specs["inverter_warranty"] = inv_data["warranty_years"]

    if battery_key and battery_key in BATTERY_OPTIONS:
        batt_data = BATTERY_OPTIONS[battery_key]
        specs["battery_kwh"] = batt_data["capacity_kwh"]
        specs["battery_warranty"] = batt_data["warranty_years"]

    if ev_charger_key and ev_charger_key in EV_CHARGER_OPTIONS:
        ev_data = EV_CHARGER_OPTIONS[ev_charger_key]
        specs["ev_charger_kw"] = ev_data["power_kw"]
        specs["has_ev"] = ev_data["power_kw"] > 0

    return specs


def validate_system(panels_key, inverter_key, battery_key):
    """Check if the system configuration is valid."""
    warnings = []
    errors = []

    if not panels_key or panels_key not in PANEL_OPTIONS:
        errors.append("Please select solar panels")
        return errors, warnings

    panel_data = PANEL_OPTIONS[panels_key]
    panel_count = panel_data["count"]

    # Check inverter compatibility
    if inverter_key and inverter_key in INVERTER_OPTIONS:
        inv_data = INVERTER_OPTIONS[inverter_key]
        if inv_data.get("max_panels") and panel_count > inv_data["max_panels"]:
            warnings.append(
                f"Inverter may be undersized for {panel_count} panels "
                f"(recommended max: {inv_data['max_panels']})"
            )

    # Check if battery includes inverter
    if battery_key and battery_key in BATTERY_OPTIONS:
        batt_data = BATTERY_OPTIONS[battery_key]
        if batt_data.get("includes_inverter"):
            if inverter_key and "Sungrow" not in inverter_key:
                warnings.append(
                    "This battery includes a hybrid inverter. "
                    "You may not need a separate inverter."
                )

    # Must have either standalone inverter or battery with inverter
    has_inverter = False
    if inverter_key and inverter_key in INVERTER_OPTIONS:
        has_inverter = True
    if battery_key and battery_key in BATTERY_OPTIONS:
        if BATTERY_OPTIONS[battery_key].get("includes_inverter"):
            has_inverter = True

    if not has_inverter:
        errors.append("System requires an inverter (standalone or included with battery)")

    return errors, warnings


def get_package_components(package_key):
    """Get component keys for a pre-configured package."""
    if package_key not in PACKAGES:
        return None

    pkg = PACKAGES[package_key]
    return {
        "panels": pkg["panels"],
        "inverter": pkg["inverter"],
        "battery": pkg["battery"],
        "ev_charger": pkg["ev_charger"],
        "package_price": pkg["package_price"],
    }
