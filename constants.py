"""Constants for solar PV economics calculations."""

REGION_CAPACITY_FACTOR = {
    "South England": 0.13,
    "Midlands": 0.12,
    "North/Scotland": 0.11
}

ORIENTATION_FACTOR = {
    "Ideal (South)": 1.00,
    "OK (SE/SW)": 0.90,
    "Suboptimal (E/W)": 0.80,
    "Poor (North/shaded)": 0.60
}

# Monthly distribution of annual solar generation (sums to 1.0)
MONTHLY_FRACTIONS = [0.03, 0.04, 0.07, 0.10, 0.12, 0.14,
                     0.14, 0.12, 0.10, 0.07, 0.04, 0.03]

# Monthly consumption profiles for different heating types
# Gas/oil heating: relatively flat profile (slight winter increase for lighting)
CONSUMPTION_PROFILE_GAS = [0.09, 0.085, 0.08, 0.075, 0.07, 0.07,
                           0.07, 0.07, 0.075, 0.08, 0.085, 0.09]

# Electric heating (heat pump or resistive): heavily winter-weighted
# Assumes ~60% of annual usage is heating, concentrated in Oct-Mar
CONSUMPTION_PROFILE_ELECTRIC = [0.14, 0.13, 0.11, 0.07, 0.05, 0.04,
                                 0.04, 0.04, 0.06, 0.09, 0.11, 0.12]

HEATING_TYPES = {
    "Gas/Oil boiler": {
        "profile": CONSUMPTION_PROFILE_GAS,
        "description": "Traditional gas or oil central heating"
    },
    "Heat pump": {
        "profile": CONSUMPTION_PROFILE_ELECTRIC,
        "base_usage_multiplier": 1.5,  # Heat pumps add ~50% to base electricity
        "description": "Air or ground source heat pump"
    },
    "Electric resistive": {
        "profile": CONSUMPTION_PROFILE_ELECTRIC,
        "base_usage_multiplier": 2.5,  # Resistive heating much less efficient
        "description": "Storage heaters or direct electric"
    }
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HOURS_PER_YEAR = 8760

# EV charging constants
EV_EFFICIENCY_KWH_PER_MILE = 0.3  # Typical EV uses ~0.3 kWh per mile
DAYS_PER_YEAR = 365
