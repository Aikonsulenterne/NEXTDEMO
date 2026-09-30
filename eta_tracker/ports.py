"""Coordinates for ports that MSC data names without coordinates (CMA data carries its own)."""

PORTS: dict[str, tuple[str, float, float]] = {
    "BJCOO": ("COTONOU", 6.35, 2.43),
    "CMDLA": ("DOUALA", 4.05, 9.70),
    "CMKBI": ("KRIBI", 2.95, 9.92),
    "CNMWN": ("MAWAN", 22.47, 113.87),
    "CNNGB": ("NINGBO", 29.87, 121.55),
    "CNSHA": ("SHANGHAI", 31.23, 121.47),
    "CNSHK": ("SHEKOU", 22.46, 113.88),
    "CIABJ": ("ABIDJAN", 5.28, -4.01),
    "GHTEM": ("TEMA", 5.61, -0.02),
    "INNSA": ("NHAVA SHEVA", 18.89, 73.06),
    "KEMBA": ("MOMBASA", -4.05, 39.67),
    "KRPUS": ("BUSAN", 35.10, 129.04),
    "MYPKG": ("PORT KLANG", 2.95, 101.31),
    "MZMPM": ("MAPUTO", -25.97, 32.57),
    "SGSIN": ("SINGAPORE", 1.27, 103.79),
    "SNDKR": ("DAKAR", 14.71, -17.46),
    "TGLFW": ("LOME", 6.13, 1.28),
    "ZAPLZ": ("PORT ELIZABETH", -33.96, 25.62),
    "ZAZBA": ("COEGA", -33.80, 25.68),
}
