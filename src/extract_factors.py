"""
Extract equitable-distribution factors from divorce opinions.

Class-project scope:
- Single jurisdiction
- Small number of cases
- Exploratory, not predictive
"""
FACTOR_SCHEMA = [
    "duration_of_marriage",
    "earning_capacity",
    "contributions_to_marriage",
    "age_and_health",
    "misconduct"
]

def extract_factors(text: str) -> dict:
    """
    Returns a dictionary mapping factor names to booleans.
    """
    pass
