# Generated from: dijkstra_gps_routing (2).ipynb
# Converted at: 2026-04-08T02:29:47.969Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import heapq
import random
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from copy import deepcopy
from collections import Counter

# ── Load & clean data ──
df = pd.read_csv("bookings.csv",
                 usecols=["Pickup Location", "Drop Location", "Ride Distance"])
df = df.dropna()

# Median aggregation: one representative distance per unique route
agg = df.groupby(
    ["Pickup Location", "Drop Location"]
)["Ride Distance"].median().reset_index()

print(f"Raw rows      : {len(df)}")
print(f"Unique routes : {len(agg)}")

# ── GPS coordinates for all 176 Delhi/NCR cities ──
CITY_COORDS = {
    "AIIMS": (28.5672, 77.2100), "Adarsh Nagar": (28.7167, 77.1833),
    "Akshardham": (28.6127, 77.2773), "Ambience Mall": (28.5014, 77.0890),
    "Anand Vihar": (28.6469, 77.3152), "Anand Vihar ISBT": (28.6469, 77.3152),
    "Ardee City": (28.4089, 77.0420), "Arjangarh": (28.4604, 77.1020),
    "Ashok Park Main": (28.6667, 77.1500), "Ashok Vihar": (28.6950, 77.1817),
    "Ashram": (28.5745, 77.2511), "Aya Nagar": (28.4800, 77.1200),
    "Azadpur": (28.7167, 77.1833), "Badarpur": (28.5027, 77.2955),
    "Badshahpur": (28.3900, 77.0350), "Bahadurgarh": (28.6921, 76.9246),
    "Barakhamba Road": (28.6289, 77.2228), "Basai Dhankot": (28.5050, 76.9980),
    "Bhikaji Cama Place": (28.5692, 77.1878), "Bhiwadi": (28.2050, 76.8600),
    "Botanical Garden": (28.5680, 77.3410), "Central Secretariat": (28.6143, 77.2010),
    "Chanakyapuri": (28.5983, 77.1873), "Chandni Chowk": (28.6506, 77.2303),
    "Chhatarpur": (28.5005, 77.1600), "Chirag Delhi": (28.5355, 77.2073),
    "Civil Lines Gurgaon": (28.4595, 77.0266), "Connaught Place": (28.6330, 77.2194),
    "Cyber Hub": (28.4950, 77.0880), "DLF City Court": (28.4750, 77.0920),
    "DLF Phase 3": (28.4920, 77.0868), "Delhi Gate": (28.6412, 77.2390),
    "Dilshad Garden": (28.6720, 77.3210), "Dwarka Mor": (28.5990, 77.0590),
    "Dwarka Sector 21": (28.5530, 77.0580), "Faridabad Sector 15": (28.3970, 77.3150),
    "GTB Nagar": (28.7000, 77.2050), "Ghaziabad": (28.6692, 77.4538),
    "Ghitorni": (28.4920, 77.1370), "Ghitorni Village": (28.4900, 77.1350),
    "Golf Course Road": (28.4580, 77.1030), "Govindpuri": (28.5318, 77.2548),
    "Greater Kailash": (28.5385, 77.2333), "Greater Noida": (28.4744, 77.5040),
    "Green Park": (28.5590, 77.2063), "Gurgaon Railway Station": (28.4527, 77.0185),
    "Gurgaon Sector 29": (28.4635, 77.0654), "Gurgaon Sector 56": (28.4220, 77.0950),
    "Gwal Pahari": (28.4450, 77.1200), "Hauz Khas": (28.5494, 77.2001),
    "Hauz Rani": (28.5384, 77.2001), "Hero Honda Chowk": (28.4617, 76.9950),
    "Huda City Centre": (28.4595, 77.0720), "IFFCO Chowk": (28.4722, 77.0731),
    "IGI Airport": (28.5562, 77.0999), "IGNOU Road": (28.5280, 77.2560),
    "IIT Delhi": (28.5459, 77.1926), "IMT Manesar": (28.3590, 76.9380),
    "INA Market": (28.5749, 77.2088), "ITO": (28.6279, 77.2437),
    "Inderlok": (28.6717, 77.1650), "India Gate": (28.6129, 77.2295),
    "Indirapuram": (28.6411, 77.3646), "Indraprastha": (28.6313, 77.2638),
    "Jahangirpuri": (28.7330, 77.1640), "Jama Masjid": (28.6507, 77.2334),
    "Janakpuri": (28.6271, 77.0836), "Jasola": (28.5454, 77.2854),
    "Jhilmil": (28.6628, 77.3072), "Jor Bagh": (28.5909, 77.2097),
    "Kadarpur": (28.4450, 77.0600), "Kalkaji": (28.5315, 77.2567),
    "Kanhaiya Nagar": (28.6883, 77.1533), "Karkarduma": (28.6519, 77.3008),
    "Karol Bagh": (28.6514, 77.1908), "Kashmere Gate": (28.6667, 77.2282),
    "Kashmere Gate ISBT": (28.6680, 77.2285), "Kaushambi": (28.6415, 77.3380),
    "Keshav Puram": (28.6900, 77.1650), "Khan Market": (28.6003, 77.2260),
    "Khandsa": (28.4180, 77.0520), "Kherki Daula Toll": (28.4120, 77.0028),
    "Kirti Nagar": (28.6524, 77.1479), "Lajpat Nagar": (28.5672, 77.2434),
    "Lal Quila": (28.6562, 77.2410), "Laxmi Nagar": (28.6330, 77.2790),
    "Lok Kalyan Marg": (28.5990, 77.1980), "MG Road": (28.4800, 77.0870),
    "Madipur": (28.6644, 77.1322), "Maidan Garhi": (28.5060, 77.1710),
    "Malviya Nagar": (28.5327, 77.2048), "Mandi House": (28.6267, 77.2332),
    "Manesar": (28.3580, 76.9380), "Mansarovar Park": (28.6697, 77.2960),
    "Mayur Vihar": (28.6085, 77.2953), "Meerut": (28.9845, 77.7064),
    "Mehrauli": (28.5244, 77.1855), "Model Town": (28.7135, 77.1942),
    "Moolchand": (28.5688, 77.2369), "Moti Nagar": (28.6570, 77.1530),
    "Mundka": (28.6763, 77.0377), "Munirka": (28.5566, 77.1709),
    "Narsinghpur": (28.4110, 77.0330), "Nawada": (28.6145, 77.0785),
    "Nehru Place": (28.5491, 77.2518), "Netaji Subhash Place": (28.6978, 77.1543),
    "New Colony": (28.4730, 77.0640), "New Delhi Railway Station": (28.6431, 77.2197),
    "Nirman Vihar": (28.6388, 77.2921), "Noida Extension": (28.6292, 77.4380),
    "Noida Film City": (28.5744, 77.3520), "Noida Sector 18": (28.5693, 77.3210),
    "Noida Sector 62": (28.6273, 77.3754), "Okhla": (28.5350, 77.2720),
    "Old Gurgaon": (28.4527, 77.0185), "Paharganj": (28.6455, 77.2121),
    "Palam Vihar": (28.5350, 77.0240), "Panchsheel Park": (28.5440, 77.2133),
    "Panipat": (29.3909, 76.9635), "Paschim Vihar": (28.6680, 77.1020),
    "Pataudi Chowk": (28.3210, 76.7970), "Patel Chowk": (28.6225, 77.2088),
    "Peeragarhi": (28.6730, 77.0820), "Pitampura": (28.6990, 77.1330),
    "Pragati Maidan": (28.6205, 77.2460), "Preet Vihar": (28.6437, 77.2970),
    "Pulbangash": (28.6667, 77.2100), "Punjabi Bagh": (28.6683, 77.1318),
    "Qutub Minar": (28.5244, 77.1855), "RK Puram": (28.5650, 77.1850),
    "Raj Nagar Extension": (28.6770, 77.4230), "Rajiv Chowk": (28.6330, 77.2194),
    "Rajiv Nagar": (28.7000, 77.4200), "Rajouri Garden": (28.6488, 77.1218),
    "Ramesh Nagar": (28.6492, 77.1445), "Rithala": (28.7218, 77.1073),
    "Rohini": (28.7200, 77.1200), "Rohini East": (28.7155, 77.1333),
    "Rohini West": (28.7095, 77.1145), "Sadar Bazar Gurgaon": (28.4527, 77.0185),
    "Saidulajab": (28.5010, 77.1840), "Saket": (28.5245, 77.2152),
    "Saket A Block": (28.5245, 77.2152), "Samaypur Badli": (28.7460, 77.1340),
    "Sarai Kale Khan": (28.5822, 77.2601), "Sarojini Nagar": (28.5757, 77.1952),
    "Satguru Ram Singh Marg": (28.6380, 77.1670), "Seelampur": (28.6671, 77.2810),
    "Shahdara": (28.6692, 77.2901), "Shastri Nagar": (28.6700, 77.1900),
    "Shastri Park": (28.6657, 77.2630), "Shivaji Park": (28.6490, 77.1530),
    "Sikanderpur": (28.4820, 77.0890), "Sohna Road": (28.4160, 77.0420),
    "Sonipat": (28.9931, 77.0151), "South Extension": (28.5713, 77.2213),
    "Subhash Chowk": (28.6860, 77.4240), "Subhash Nagar": (28.6388, 77.1240),
    "Sultanpur": (28.4955, 77.1580), "Sushant Lok": (28.4730, 77.0860),
    "Tagore Garden": (28.6421, 77.1170), "Tilak Nagar": (28.6367, 77.1002),
    "Tis Hazari": (28.6672, 77.2172), "Tughlakabad": (28.5050, 77.2780),
    "Udyog Bhawan": (28.6090, 77.2048), "Udyog Vihar": (28.5050, 77.0870),
    "Udyog Vihar Phase 4": (28.5070, 77.0900), "Uttam Nagar": (28.6224, 77.0590),
    "Vaishali": (28.6445, 77.3380), "Vasant Kunj": (28.5225, 77.1580),
    "Vatika Chowk": (28.4120, 77.0580), "Vidhan Sabha": (28.6517, 77.2344),
    "Vinobapuri": (28.5742, 77.2524), "Vishwavidyalaya": (28.6897, 77.2135),
    "Welcome": (28.6748, 77.2927), "Yamuna Bank": (28.6227, 77.2903),
}

print(f"GPS coords loaded: {len(CITY_COORDS)} cities")

# ── Haversine: real-world km between two GPS points ──
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


cities      = sorted(set(df["Pickup Location"]).union(set(df["Drop Location"])))
city_to_idx = {city: i for i, city in enumerate(cities)}
idx_to_city = {i: city for city, i in city_to_idx.items()}
n           = len(cities)

# ── Step 1: Fill matrix from booking data (median distances) ──
distance_matrix = np.full((n, n), np.inf)
np.fill_diagonal(distance_matrix, 0)
for _, row in agg.iterrows():
    i = city_to_idx[row["Pickup Location"]]
    j = city_to_idx[row["Drop Location"]]
    distance_matrix[i, j] = row["Ride Distance"]
    distance_matrix[j, i] = row["Ride Distance"]

# ── Step 2: Connect nearby cities using GPS (proximity threshold = 8 km) ──
# Any two cities within 8 km of each other get connected.
# Distance used = Haversine GPS distance (realistic road proxy).
# This fills the gaps where no direct booking exists between close cities.
PROXIMITY_KM = 8
gps_edges_added = 0

for i, city_a in enumerate(cities):
    for j, city_b in enumerate(cities):
        if i >= j:
            continue
        if city_a not in CITY_COORDS or city_b not in CITY_COORDS:
            continue
        lat1, lon1 = CITY_COORDS[city_a]
        lat2, lon2 = CITY_COORDS[city_b]
        gps_dist = haversine(lat1, lon1, lat2, lon2)
        # Only add if no booking-data edge exists yet AND cities are nearby
        if distance_matrix[i, j] == np.inf and gps_dist <= PROXIMITY_KM:
            distance_matrix[i, j] = gps_dist
            distance_matrix[j, i] = gps_dist
            gps_edges_added += 1

print(f"Cities            : {n}")
print(f"Booking edges     : {len(agg)}")
print(f"GPS edges added   : {gps_edges_added}")
print(f"Total connections : {len(agg) + gps_edges_added}")
print(f"\nPatel Chowk -> AIIMS distance : {distance_matrix[city_to_idx["Patel Chowk"], city_to_idx["AIIMS"]]:.2f} km")

# Dijkstra needs no hyperparameters.
print("Dijkstra Algorithm — no hyperparameters needed.")

def dijkstra(start_city, goal_city):
    """
    Dijkstra's Algorithm on the GPS-enhanced distance matrix.
    Now finds TRUE multi-hop shortest paths through intermediate cities.
    """
    start = city_to_idx[start_city]
    goal  = city_to_idx[goal_city]

    dist = {i: np.inf for i in range(n)}
    dist[start] = 0
    prev = {i: None for i in range(n)}
    heap = [(0, start)]
    visited = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == goal:
            break
        for v in range(n):
            if distance_matrix[u, v] != np.inf and v not in visited:
                nd = d + distance_matrix[u, v]
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    if not path or path[0] != start:
        return [], np.inf
    return [idx_to_city[i] for i in path], dist[goal]


def get_optimal_path(start_city, goal_city):
    return dijkstra(start_city, goal_city)


print("dijkstra() ready.")

# get_optimal_path() calls dijkstra() — already defined in Cell 3.
print("Ready.")

path, dist = get_optimal_path("Vidhan Sabha", "Anand Vihar")
print("Optimal Path  :", " -> ".join(path))
print("Total Distance:", round(dist, 2), "km")

path, dist = get_optimal_path("Seelampur", "Civil Lines Gurgaon")
print("Optimal Path  :", " -> ".join(path))
print("Total Distance:", round(dist, 2), "km")

path, dist = get_optimal_path("Patel Chowk", "AIIMS")
print("Optimal Path  :", " -> ".join(path))
print("Total Distance:", round(dist, 2), "km")

import networkx as nx
import matplotlib.pyplot as plt


def visualize_network_with_path(optimal_path, total_distance, start_city, goal_city):
    G = nx.Graph()
    for city in cities:
        G.add_node(city)
    for _, row in agg.iterrows():
        G.add_edge(row["Pickup Location"], row["Drop Location"],
                   weight=row["Ride Distance"])

    # Use real GPS coordinates as node positions
    pos = {}
    for city in cities:
        if city in CITY_COORDS:
            lat, lon = CITY_COORDS[city]
            pos[city] = (lon, lat)  # (x=longitude, y=latitude)
        else:
            pos[city] = (77.2, 28.6)  # fallback centre

    plt.figure(figsize=(16, 12))
    ax = plt.gca()
    ax.set_facecolor("#1a1a2e")
    plt.gcf().patch.set_facecolor("#1a1a2e")

    nx.draw_networkx_nodes(G, pos, node_size=30, node_color="#4a90d9",
                           alpha=0.7, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=optimal_path, node_size=120,
                           node_color="#66BB6A", edgecolors="white",
                           linewidths=1.2, ax=ax)
    nx.draw_networkx_edges(G, pos, width=0.4, alpha=0.2,
                           edge_color="#aaaaaa", ax=ax)
    path_edges = list(zip(optimal_path, optimal_path[1:]))
    nx.draw_networkx_edges(G, pos, edgelist=path_edges,
                           width=4, edge_color="#FF6B6B", ax=ax)

    # Only label path nodes to keep it readable
    path_labels = {city: city for city in optimal_path}
    nx.draw_networkx_labels(G, pos, labels=path_labels,
                            font_size=8, font_color="white",
                            font_weight="bold", ax=ax)

    plt.title(
        f"Dijkstra Shortest Path: {start_city}  →  {goal_city}\n"
        f"Via: {" → ".join(optimal_path)}  |  {round(total_distance, 2)} km",
        fontsize=13, fontweight="bold", color="white", pad=12
    )
    plt.axis("off")
    plt.tight_layout()
    plt.show()

start_city = "Vidhan Sabha"
goal_city  = "Anand Vihar"
path, dist = get_optimal_path(start_city, goal_city)
print(f"Path     : {" -> ".join(path)}")
print(f"Distance : {round(dist,2)} km")
visualize_network_with_path(path, dist, start_city, goal_city)

start_city = "Seelampur"
goal_city  = "Civil Lines Gurgaon"
path, dist = get_optimal_path(start_city, goal_city)
print(f"Path     : {" -> ".join(path)}")
print(f"Distance : {round(dist,2)} km")
visualize_network_with_path(path, dist, start_city, goal_city)

start_city = "Patel Chowk"
goal_city  = "AIIMS"
path, dist = get_optimal_path(start_city, goal_city)
print(f"Path     : {" -> ".join(path)}")
print(f"Distance : {round(dist,2)} km")
visualize_network_with_path(path, dist, start_city, goal_city)

# =====================================================
#   CHANGE ONLY THESE TWO VALUES
# =====================================================
START_CITY = "Patel Chowk"   # <-- Change me!
GOAL_CITY  = "AIIMS"         # <-- Change me!

print("Available cities:")
print(", ".join(cities))
print(f"\nSelected:  {START_CITY}  ->  {GOAL_CITY}")

import matplotlib.patches as mpatches

random.seed(42)
np.random.seed(42)

assert START_CITY in city_to_idx, f"{START_CITY!r} not in dataset!"
assert GOAL_CITY  in city_to_idx, f"{GOAL_CITY!r} not in dataset!"
assert START_CITY != GOAL_CITY,   "Start and Goal must be different!"

# Base distance matrix already built in Cell 1 (GPS-enhanced)
base_dm = distance_matrix.copy()

# Dynamic event types (Heavy Crowd & Road Work removed)
EVENTS = {
    "CLEAR":    {"color": "#A8D5A2", "cost_mult": 1.0,    "label": "Clear Route"},
    "WEATHER":  {"color": "#6BAED6", "cost_mult": 1.5,    "label": "Bad Weather (+50%)"},
    "BLOCKAGE": {"color": "#CC0000", "cost_mult": np.inf, "label": "Route Blocked"},
}

def generate_events(data, blockage_prob=0.12, event_prob=0.30, seed=42):
    random.seed(seed); emap = {}
    for _, row in data.iterrows():
        r    = random.random()
        edge = (row["Pickup Location"], row["Drop Location"])
        if   r < blockage_prob:            emap[edge] = "BLOCKAGE"
        elif r < blockage_prob+event_prob: emap[edge] = "WEATHER"
        else:                              emap[edge] = "CLEAR"
    return emap

event_map  = generate_events(agg)
evt_counts = Counter(event_map.values())
print("Event counts:", dict(evt_counts))

# Build dynamic cost matrix
dyn_dm = base_dm.copy()
for (o, d), evt in event_map.items():
    if o in city_to_idx and d in city_to_idx:
        mult = EVENTS[evt]["cost_mult"]
        i, j = city_to_idx[o], city_to_idx[d]
        dyn_dm[i, j] = np.inf if mult == np.inf else base_dm[i, j] * mult
        dyn_dm[j, i] = np.inf if mult == np.inf else base_dm[j, i] * mult


# Dijkstra on dynamic matrix
def dijkstra_dynamic(sc, gc, dm):
    s, g  = city_to_idx[sc], city_to_idx[gc]
    dist  = {i: np.inf for i in range(n)}
    dist[s] = 0
    prev  = {i: None for i in range(n)}
    heap  = [(0, s)]
    visited = set()
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited: continue
        visited.add(u)
        if u == g: break
        for v in range(n):
            if dm[u, v] != np.inf and v not in visited:
                nd = d + dm[u, v]
                if nd < dist[v]:
                    dist[v] = nd; prev[v] = u
                    heapq.heappush(heap, (nd, v))
    path = []; node = g
    while node is not None: path.append(node); node = prev[node]
    path.reverse()
    if not path or path[0] != s: return [], 0.0
    return [idx_to_city[i] for i in path], dist[g]


path, dyn_cost = dijkstra_dynamic(START_CITY, GOAL_CITY, dyn_dm)

if len(path) > 1:
    km = sum(base_dm[city_to_idx[path[i]], city_to_idx[path[i+1]]]
             for i in range(len(path) - 1))
else:
    km = 0.0
    print("WARNING: No path found.")

print(f"\nDijkstra Path  : {" -> ".join(path)}")
print(f"Base Distance  : {km:.2f} km")
print(f"Dynamic Cost   : {dyn_cost:.2f} (includes weather multipliers)")

G = nx.Graph()
for city in cities: G.add_node(city)
for _, row in agg.iterrows():
    G.add_edge(row["Pickup Location"], row["Drop Location"],
               weight=row["Ride Distance"])

# Real GPS layout
pos = {city: (CITY_COORDS[city][1], CITY_COORDS[city][0])
       for city in cities if city in CITY_COORDS}

ped = list(zip(path, path[1:]))
fig, ax = plt.subplots(figsize=(18, 13))
fig.patch.set_facecolor("#0d0d1a"); ax.set_facecolor("#0d0d1a")

for u, v in G.edges():
    evt   = event_map.get((u, v), event_map.get((v, u), "CLEAR"))
    color = EVENTS[evt]["color"]
    width = 2.5 if evt == "BLOCKAGE" else 1.0
    style = "dashed" if evt == "BLOCKAGE" else "solid"
    nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], width=width,
                           edge_color=color, style=style, alpha=0.6, ax=ax)

nx.draw_networkx_edges(G, pos, edgelist=ped, width=6,
                       edge_color="#00FF7F", ax=ax)

nc = ["#00FF00" if c == START_CITY else
      "#FF3333" if c == GOAL_CITY  else
      "#00BFFF" if c in path       else "#2d2d50"
      for c in G.nodes()]
nx.draw_networkx_nodes(G, pos, node_color=nc, node_size=40,
                       ax=ax, edgecolors="white", linewidths=0.4)

# Label only path nodes
path_labels = {c: c for c in path}
nx.draw_networkx_labels(G, pos, labels=path_labels,
                        font_size=8, font_color="white",
                        font_weight="bold", ax=ax)

ax.set_title(
    f"DYNAMIC ENVIRONMENT (Dijkstra + GPS Layout)  |  {START_CITY}  ->  {GOAL_CITY}\n"
    f"Path: {" -> ".join(path)}  |  {km:.2f} km",
    fontsize=13, color="white", fontweight="bold", pad=14
)
ax.axis("off")
ax.legend(
    handles=[
        mpatches.Patch(color="#CC0000", label=f"Route Blocked  ({evt_counts.get("BLOCKAGE",0)}) - Impassable"),
        mpatches.Patch(color="#6BAED6", label=f"Bad Weather    ({evt_counts.get("WEATHER",0)}) - +50% cost"),
        mpatches.Patch(color="#A8D5A2", label=f"Clear Route    ({evt_counts.get("CLEAR",0)})"),
        mpatches.Patch(color="#00FF7F", label=f"Dijkstra Path  ({km:.2f} km)"),
        mpatches.Patch(color="#00FF00", label=f"Start: {START_CITY}"),
        mpatches.Patch(color="#FF3333", label=f"Goal:  {GOAL_CITY}"),
    ],
    loc="lower left", fontsize=10,
    facecolor="#1a1a3a", edgecolor="white", labelcolor="white"
)
plt.tight_layout()
plt.savefig(f"dynamic_gps_{START_CITY}_to_{GOAL_CITY}.png",
            dpi=150, bbox_inches="tight", facecolor="#0d0d1a")
plt.show()