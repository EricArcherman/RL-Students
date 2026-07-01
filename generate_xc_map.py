#!/usr/bin/env python3
"""Generate XC team map: address hotspots + run locations."""

import json
import time
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from scipy.ndimage import gaussian_filter
from shapely.geometry import Point

CACHE_PATH = Path(__file__).parent / "geocode_cache.json"
OUTPUT_PATH = Path(__file__).parent / "xc_team_map.png"

ROSTER = [
    ("Eric Archerman", "3 Whitehouse Lane, Weston, MA 02493"),
    ("Toby Harrison", "8 Manet Circle, Chestnut Hill, MA 02467"),
    ("Ameer Hasan", "30 Hannah Niles Way, Braintree, MA 02184"),
    ("James Kerr", "8 Chickering Road, Norwood, MA 02062"),
    ("Temi Martins-Dosumu", "1841 Washington Street, Boston, MA 02118"),
    ("Paul Tompros", "65 Pearl Street, Charlestown, MA 02129"),
    ("Riley Alqueza", "149 Melrose Avenue, Needham, MA 02492"),
    ("Romeo Borgida", "2 Marshall Place, Charlestown, MA 02129"),
    ("Sid Chopra", "454 York Street, Canton, MA 02021"),
    ("Andrew Heavey", "4 Plimpton Road, Foxboro, MA 02035"),
    ("Nayan Patel", "85 Chestnut Street, Weston, MA 02493"),
    ("Ben Romano", "165 Milton Avenue, Hyde Park, MA 02136"),
    ("Kolby Sahin", "80 Burr Drive, Needham, MA 02492"),
    ("Julian Vidal", "65 E India Row, Boston, MA 02110"),
    ("Alan Archerman", "3 Whitehouse Lane, Weston, MA 02493"),
    ("Alex Archerman", "3 Whitehouse Lane, Weston, MA 02493"),
    ("Rowan Bush", "43 Trapelo Street, Brighton, MA 02135"),
    ("Andrew Kramer", "4 Commonwealth Park, Wellesley, MA 02481"),
    ("Guled Rashid", "4 Bradlee Park, Hyde Park, MA 02136"),
    ("Kevin Song", "141 Thatcher Street, Westwood, MA 02090"),
    ("Charles Wang", "10 Longfellow Road, Groton, MA 01450"),
    ("Sorin Brosseau", "135 W Newton Street, Boston, MA 02118"),
    ("James Butler", "111 Perham Street, West Roxbury, MA 02132"),
    ("Julian Chin", "66 Potomac Street, West Roxbury, MA 02132"),
    ("James Ding", "33 R Cedar Street, Wellesley, MA 02481"),
    ("Marcus Farzaneh-Far", "43 Druce Street, Brookline, MA 02445"),
    ("Caiden Ghostlaw", "16 Dover Drive, Walpole, MA 02081"),
    ("Liam Kelly", "25 Hobson Street, Brighton, MA 02135"),
    ("Kabir Kumar", "390 Commonwealth Avenue, Boston, MA 02215"),
    ("Charley Malley", "21 Landseer Street, West Roxbury, MA 02132"),
    ("Theo Mashikian", "36 Lime Street, Boston, MA 02108"),
    ("Holton Pingree", "261 Shawmut Avenue, Boston, MA 02118"),
    ("Dylan Zhang", "6 Shelley Road, Wellesley, MA 02481"),
    ("Jude Dunn", "22 Howard Street, Norwood, MA 02062"),
    ("Tanoshi Inomata", "255 Kelton Street, Allston, MA 02134"),
    ("Griffin Lee", "251 Commonwealth Avenue, Boston, MA 02116"),
    ("Drew MacIsaac", "18 Fairview Road, Canton, MA 02021"),
    ("Santiago Nelson", "52 Chellman Street, West Roxbury, MA 02132"),
    ("Kazuki Tokuda", "45 Birch Street, Westwood, MA 02090"),
    ("Aveer Singh", "225 Pond Street, Westwood, MA 02090"),
    ("Luben Stolarov", "15 Alaric Street, West Roxbury, MA 02132"),
    ("Henry White", "3 Alameda Road, West Roxbury, MA 02132"),
]

RUN_LOCATIONS = [
    ("RL Home Course", "101 St Theresa Avenue, West Roxbury, MA 02132", "#E63946"),
    ("Arnold Arboretum", "125 Arborway, Jamaica Plain, MA 02130", "#2A9D8F"),
    ("Cutler Park", "Kendrick Pond, Needham, MA 02492", "#457B9D"),
    ("Weston Reservoir", "117 Ash Street, Weston, MA 02493", "#48CAE4"),
    ("Powisset Farm", "37 Powisset Street, Dover, MA 02030", "#E9C46A"),
    ("Blue Hills", "Houghton's Pond, Milton, MA 02186", "#588157"),
    ("Chestnut Hill Reservoir", "Cleveland Circle, Boston, MA 02135", "#9B5DE5"),
    ("Charles River (Herter Park)", "Herter Park, Brighton, MA 02134", "#F4A261"),
]

# Greater Boston focus; Groton is shown off-map in legend only
MAP_BOUNDS = {"west": -71.38, "east": -70.97, "south": 42.07, "north": 42.42}

# Fallback coordinates when Nominatim can't resolve an address
MANUAL_COORDS = {
    "8 Manet Circle, Chestnut Hill, MA 02467": [42.3306, -71.1520],
    "Kendrick Pond, Needham, MA 02492": [42.2749, -71.2189],
    "117 Ash Street, Weston, MA 02493": [42.3458, -71.2955],
    "37 Powisset Street, Dover, MA 02030": [42.2435, -71.2785],
    "Houghton's Pond, Milton, MA 02186": [42.2080, -71.1018],
    "Herter Park, Brighton, MA 02134": [42.3660, -71.1570],
}


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def geocode_all() -> dict[str, tuple[float, float]]:
    cache = load_cache()
    geolocator = Nominatim(user_agent="rl-xc-map-generator")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

    all_addresses = {addr for _, addr in ROSTER}
    all_addresses.update(addr for _, addr, _ in RUN_LOCATIONS)

    for address in sorted(all_addresses):
        if address in cache:
            continue
        if address in MANUAL_COORDS:
            cache[address] = MANUAL_COORDS[address]
            save_cache(cache)
            continue
        print(f"Geocoding: {address}")
        result = geocode(address + ", USA")
        if result:
            cache[address] = [result.latitude, result.longitude]
        elif address in MANUAL_COORDS:
            cache[address] = MANUAL_COORDS[address]
        else:
            print(f"  WARNING: could not geocode {address}")
        save_cache(cache)

    for address, coords in MANUAL_COORDS.items():
        cache.setdefault(address, coords)

    return cache


def build_heatmap(ax, lons, lats, bounds):
    grid_size = 200
    lon_grid = np.linspace(bounds["west"], bounds["east"], grid_size)
    lat_grid = np.linspace(bounds["south"], bounds["north"], grid_size)
    heat = np.zeros((grid_size, grid_size))

    sigma = 0.012  # degrees, ~1 km
    for lon, lat in zip(lons, lats):
        if not (bounds["south"] <= lat <= bounds["north"] and bounds["west"] <= lon <= bounds["east"]):
            continue
        ix = int((lon - bounds["west"]) / (bounds["east"] - bounds["west"]) * (grid_size - 1))
        iy = int((lat - bounds["south"]) / (bounds["north"] - bounds["south"]) * (grid_size - 1))
        heat[iy, ix] += 1

    heat = gaussian_filter(heat, sigma=8)
    if heat.max() > 0:
        heat = heat / heat.max()

    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    cmap = LinearSegmentedColormap.from_list(
        "hotspots", ["#ffffff00", "#fee5d980", "#fcae9180", "#fb6a4a99", "#de2d26b3", "#a50f15cc"]
    )
    ax.contourf(lon_mesh, lat_mesh, heat, levels=20, cmap=cmap, alpha=0.5, zorder=2)


def main():
    coords = geocode_all()

    roster_points = []
    off_map = []
    for name, address in ROSTER:
        if address not in coords:
            continue
        lat, lon = coords[address]
        if MAP_BOUNDS["south"] <= lat <= MAP_BOUNDS["north"] and MAP_BOUNDS["west"] <= lon <= MAP_BOUNDS["east"]:
            roster_points.append((name, lon, lat))
        else:
            off_map.append(name)

    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
    ax.set_xlim(MAP_BOUNDS["west"], MAP_BOUNDS["east"])
    ax.set_ylim(MAP_BOUNDS["south"], MAP_BOUNDS["north"])
    ax.set_aspect("equal")

    # Basemap — Voyager has clearer roads/labels than Positron
    cx.add_basemap(
        ax,
        crs="EPSG:4326",
        source=cx.providers.CartoDB.Voyager,
        zoom=13,
        zorder=1,
        attribution_size=6,
    )

    # Hotspots from roster (exclude off-map for density)
    lons = [p[1] for p in roster_points]
    lats = [p[2] for p in roster_points]
    build_heatmap(ax, lons, lats, MAP_BOUNDS)

    # Subtle dot for each runner
    ax.scatter(lons, lats, s=24, c="#7f0000", alpha=0.4, edgecolors="none", zorder=3)

    # Run locations — offset labels to reduce overlap
    label_offsets = {
        "RL Home Course": (12, -22),
        "Arnold Arboretum": (12, 12),
        "Cutler Park": (-110, -14),
        "Weston Reservoir": (12, 14),
        "Powisset Farm": (-115, -16),
        "Blue Hills": (12, 14),
        "Chestnut Hill Reservoir": (12, 12),
        "Charles River (Herter Park)": (-140, 10),
    }
    run_markers = []
    for label, address, color in RUN_LOCATIONS:
        if address not in coords:
            continue
        lat, lon = coords[address]
        ax.scatter(
            [lon], [lat],
            s=450, c=color, marker="*", edgecolors="white", linewidths=1.8, zorder=5
        )
        ox, oy = label_offsets.get(label, (10, 10))
        ax.annotate(
            label,
            (lon, lat),
            xytext=(ox, oy),
            textcoords="offset points",
            fontsize=11,
            fontweight="bold",
            color="#1d3557",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=color, alpha=0.92, lw=2),
            arrowprops=dict(arrowstyle="-", color=color, lw=1.0, shrinkA=2, shrinkB=2),
            zorder=6,
        )
        run_markers.append(Patch(facecolor=color, edgecolor="white", label=label))

    # RL school marker emphasis
    rl_addr = RUN_LOCATIONS[0][1]
    if rl_addr in coords:
        lat, lon = coords[rl_addr]
        ax.scatter([lon], [lat], s=160, facecolors="none", edgecolors="#E63946", linewidths=2.5, zorder=4)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])

    legend_items = [
        Patch(facecolor="#fb6a4a", alpha=0.7, label="Runner address density"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#7f0000", markersize=9, alpha=0.5, label="Individual runner"),
    ] + run_markers
    if off_map:
        legend_items.append(
            Patch(facecolor="none", edgecolor="none", label=f"Off map: {', '.join(off_map)}")
        )

    ax.legend(
        handles=legend_items,
        loc="lower left",
        fontsize=11,
        framealpha=0.95,
        title="Legend",
        title_fontsize=13,
        markerscale=1.4,
        handlelength=1.6,
        borderpad=0.8,
        labelspacing=0.6,
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_PATH, bbox_inches="tight", facecolor="white", pad_inches=0.05)
    print(f"Saved map to {OUTPUT_PATH}")
    print(f"Plotted {len(roster_points)} runners on map; {len(off_map)} off-map")


if __name__ == "__main__":
    main()
