import pytest


@pytest.fixture
def constraints():
    """Minimal stand-in for the live constraints.json — only the keys the validator
    reads (seasonal_by_genre / seasonal_fit). Horror's data-best months mirror the
    real finding (ROI metric: Jan/Jul/Jun, not Halloween)."""
    return {
        "seasonal_by_genre": {
            "Horror": ["January", "July", "June"],
            "Thriller": ["July", "June", "December"],
        },
        "seasonal_fit": {"best_months_named": ["July", "June", "December"]},
    }
