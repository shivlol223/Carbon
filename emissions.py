"""Educational carbon-equivalent calculations used by Campus Eco-Tracker.

Factors are illustrative placeholders inspired by the supplied AAT report. They
are not official or location-specific greenhouse-gas inventory factors.
"""
EMISSION_FACTORS = {
    "Electricity": {"factor": 0.85, "unit": "kWh", "description": "kg CO₂e per kWh"},
    "Water": {"factor": 0.001, "unit": "litres", "description": "kg CO₂e per litre"},
    "Waste": {"factor": 0.57, "unit": "kg", "description": "kg CO₂e per kg of waste"},
    "Transport": {"factor": 0.12, "unit": "km", "description": "kg CO₂e per km"},
}


def calculate_emissions(utility_type: str, value: float) -> float:
    """Return estimated kg CO₂e for a supported positive consumption amount."""
    if utility_type not in EMISSION_FACTORS:
        raise ValueError("Unsupported utility type")
    if value <= 0:
        raise ValueError("Consumption must be greater than zero")
    return round(value * EMISSION_FACTORS[utility_type]["factor"], 3)
