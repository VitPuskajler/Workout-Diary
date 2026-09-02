"""Weight unit conversion between pounds and kilograms."""

KG_PER_LB = 0.45359237


def lbs_to_kg(pounds):
    """Convert a weight in pounds to kilograms."""
    return pounds * KG_PER_LB


def kg_to_lbs(kilograms):
    """Convert a weight in kilograms to pounds."""
    return kilograms / KG_PER_LB
