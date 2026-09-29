from .base import Carrier, PageCapture
from .cma import CmaCarrier
from .msc import MscCarrier

CARRIERS: dict[str, Carrier] = {"CMA": CmaCarrier(), "CMA CGM": CmaCarrier(), "MSC": MscCarrier()}


def get_carrier(code: str) -> Carrier | None:
    return CARRIERS.get(code.strip().upper())


__all__ = ["CARRIERS", "Carrier", "PageCapture", "get_carrier"]
