"""Where her paintings were made: a small gazetteer plus the layout of the sketchbook map.

Places are matched by name (English or German spelling). Unknown places are simply left off
the map; Johanna can ask for more to be added.
"""

import math
import unicodedata

# name -> (latitude, longitude)
CITIES = {
    "braunschweig": (52.27, 10.52), "brunswick": (52.27, 10.52), "berlin": (52.52, 13.40),
    "hamburg": (53.55, 9.99), "munich": (48.14, 11.58), "munchen": (48.14, 11.58),
    "cologne": (50.94, 6.96), "koln": (50.94, 6.96), "dresden": (51.05, 13.74),
    "leipzig": (51.34, 12.37), "frankfurt": (50.11, 8.68), "hannover": (52.37, 9.73),
    "hanover": (52.37, 9.73), "goslar": (51.91, 10.43), "wolfenbuttel": (52.16, 10.54),
    "lubeck": (53.87, 10.69), "bremen": (53.08, 8.80), "heidelberg": (49.40, 8.67),
    "nuremberg": (49.45, 11.08), "nurnberg": (49.45, 11.08), "rostock": (54.09, 12.14),
    "prague": (50.08, 14.44), "praha": (50.08, 14.44), "vienna": (48.21, 16.37), "wien": (48.21, 16.37),
    "budapest": (47.50, 19.04), "krakow": (50.06, 19.94), "cracow": (50.06, 19.94),
    "warsaw": (52.23, 21.01), "warszawa": (52.23, 21.01), "gdansk": (54.35, 18.65),
    "wroclaw": (51.11, 17.04), "bratislava": (48.15, 17.11), "ljubljana": (46.06, 14.51),
    "zagreb": (45.81, 15.98), "salzburg": (47.81, 13.05), "innsbruck": (47.27, 11.39),
    "hallstatt": (47.56, 13.65), "zurich": (47.38, 8.54), "lucerne": (47.05, 8.31),
    "luzern": (47.05, 8.31), "geneva": (46.20, 6.14), "bern": (46.95, 7.45),
    "lisbon": (38.72, -9.14), "lissabon": (38.72, -9.14), "porto": (41.15, -8.61),
    "madrid": (40.42, -3.70), "barcelona": (41.39, 2.17), "seville": (37.39, -5.98),
    "sevilla": (37.39, -5.98), "valencia": (39.47, -0.38), "granada": (37.18, -3.60),
    "palma": (39.57, 2.65), "mallorca": (39.62, 2.99), "pollenca": (39.88, 3.02),
    "menorca": (39.95, 4.11), "ibiza": (38.91, 1.43), "malaga": (36.72, -4.42),
    "paris": (48.86, 2.35), "lyon": (45.76, 4.84), "nice": (43.70, 7.27),
    "marseille": (43.30, 5.37), "bordeaux": (44.84, -0.58), "strasbourg": (48.57, 7.75),
    "amsterdam": (52.37, 4.90), "rotterdam": (51.92, 4.48), "brussels": (50.85, 4.35),
    "bruges": (51.21, 3.22), "brugge": (51.21, 3.22), "copenhagen": (55.68, 12.57),
    "kopenhagen": (55.68, 12.57), "stockholm": (59.33, 18.07), "oslo": (59.91, 10.75),
    "bergen": (60.39, 5.32), "helsinki": (60.17, 24.94), "tallinn": (59.44, 24.75),
    "riga": (56.95, 24.11), "vilnius": (54.69, 25.28), "reykjavik": (64.15, -21.94),
    "venice": (45.44, 12.32), "venedig": (45.44, 12.32), "venezia": (45.44, 12.32),
    "florence": (43.77, 11.26), "florenz": (43.77, 11.26), "firenze": (43.77, 11.26),
    "rome": (41.90, 12.50), "rom": (41.90, 12.50), "naples": (40.85, 14.27),
    "milan": (45.46, 9.19), "mailand": (45.46, 9.19), "lake garda": (45.62, 10.70),
    "gardasee": (45.62, 10.70), "garda": (45.58, 10.70), "lake como": (46.00, 9.26),
    "como": (45.81, 9.09), "verona": (45.44, 10.99), "siena": (43.32, 11.33),
    "cinque terre": (44.13, 9.71), "bologna": (44.49, 11.34), "sicily": (37.60, 14.02),
    "palermo": (38.12, 13.36), "dubrovnik": (42.65, 18.09), "split": (43.51, 16.44),
    "athens": (37.98, 23.73), "athen": (37.98, 23.73), "santorini": (36.39, 25.46),
    "istanbul": (41.01, 28.98), "edinburgh": (55.95, -3.19), "london": (51.51, -0.13),
    "dublin": (53.35, -6.26), "oxford": (51.75, -1.26), "cambridge": (52.21, 0.12),
    "marrakech": (31.63, -8.01), "cairo": (30.04, 31.24), "new york": (40.71, -74.01),
    "tokyo": (35.68, 139.69), "kyoto": (35.01, 135.77), "new delhi": (28.61, 77.21),
    "delhi": (28.61, 77.21), "mumbai": (19.08, 72.88), "goa": (15.30, 74.12),
    "jaipur": (26.91, 75.79), "bali": (-8.41, 115.19), "bangkok": (13.76, 100.50),
    "singapore": (1.35, 103.82), "sydney": (-33.87, 151.21), "cape town": (-33.92, 18.42),
}


def _norm(text):
    text = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in text if not unicodedata.combining(c)).replace("ß", "ss")


def locate(place):
    """(lat, lon) for a place name such as 'Kraków' or 'Lake Garda, Italy', else None."""
    key = _norm(place)
    if key in CITIES:
        return CITIES[key]
    first = key.split(",")[0].strip()
    if first in CITIES:
        return CITIES[first]
    for name, coords in CITIES.items():  # "Old town of Prague"
        if len(name) > 4 and name in key:
            return coords
    return None


def layout(points, width=1000.0, height=560.0, pad=0.12):
    """Place (lat, lon) points on a width x height sheet. Returns a list of (x, y) in the same order."""
    if not points:
        return []
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    mid_lat = sum(lats) / len(lats)
    k = math.cos(math.radians(mid_lat))
    dx = max((max(lons) - min(lons)) * k, 1e-6)
    dy = max(max(lats) - min(lats), 1e-6)
    inner_w, inner_h = width * (1 - 2 * pad), height * (1 - 2 * pad)
    scale = min(inner_w / dx, inner_h / dy)
    if len(points) == 1:
        return [(width / 2, height / 2)]
    cx = (max(lons) + min(lons)) / 2
    cy = (max(lats) + min(lats)) / 2
    out = []
    for lat, lon in points:
        out.append((width / 2 + (lon - cx) * k * scale, height / 2 - (lat - cy) * scale))
    return out
