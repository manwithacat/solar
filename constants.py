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

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HOURS_PER_YEAR = 8760
