"""Pure deterministic feature engines.

Canonical hot-path engines live in ``prime/``; use ``features.prime_adapters`` when
importing CVD/footprint from legacy paths during consolidation.
"""

from .absorption import AbsorptionEngine
from .cvd import CVDEngine
from .delta import DeltaEngine
from .footprint import FootprintEngine
from .iceberg import IcebergDetector
from .l2_imbalance import OrderBookImbalanceEngine
from .large_prints import LargePrintDetector
from .microprice import microprice
from .spoofing import SpoofingDetector
from .trade_signing import TradeSigner, bvc_classify
from .vpin import VPINEngine
from .whale import WhalePressureEngine

__all__ = [
    "AbsorptionEngine",
    "CVDEngine",
    "DeltaEngine",
    "FootprintEngine",
    "IcebergDetector",
    "LargePrintDetector",
    "OrderBookImbalanceEngine",
    "SpoofingDetector",
    "TradeSigner",
    "VPINEngine",
    "WhalePressureEngine",
    "bvc_classify",
    "microprice",
]
