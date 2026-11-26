from .base import FeatureCache, Strategy, Trade
from .late_day_momentum import LateDayMomentum
from .noise_area_momentum import NoiseAreaMomentum
from .vwap_reversion import VwapReversion

REGISTRY = {
    "S1": NoiseAreaMomentum,
    "S2": LateDayMomentum,
    "S3": VwapReversion,
}

__all__ = ["FeatureCache", "Strategy", "Trade", "NoiseAreaMomentum", "LateDayMomentum", "VwapReversion", "REGISTRY"]
