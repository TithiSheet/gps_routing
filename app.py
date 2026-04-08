import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Instant Route Optimizer")
st.title("🚀 Lightning-Fast Dijkstra Optimizer")

# =========================
# 1. FAST DATA LOADING
# =========================
@st.cache_data
def load_optimized_data():
    # Load only necessary columns
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna()
    
    # Create a quick-lookup dictionary for 'Ride Distance'
    # This replaces the slow df[df['col'] == 'val'] search
    distance_lookup = {}
    for row in df.itertuples(index=False):
        key = tuple(sorted([row[0], row[1]]))
        if key not in distance_lookup or row[2] < distance_lookup[key]:
            distance_lookup[key] = row[2]
            
    cities = sorted(list(set(df['Pickup Location']).union(set(df['Drop Location']))))
    return distance_lookup, cities

dist_lookup, cities = load_optimized_data()

# =========================
# 2. CACHED GRAPH RESOURCE
# =========================
@st.cache_resource
def build_static_graph(lookup_dict):
    G = nx.Graph()
    for (u, v), dist in lookup_dict.items():
        G.add_edge(u, v, weight=dist)
    return G

G_base = build_static_graph(dist_lookup)

@st.cache_data
def get_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

# =========================
# 3. UI SIDEBAR
# =========================
st.sidebar.header("🛠 Environment")
condition = st.sidebar.selectbox(
    "Current Condition",
    ["Normal/Clear", "Heavy Traffic", "Rainy/Weather", "Road Blockage"]
)

condition_map = {
    "Normal/Clear": {"penalty": 1.0, "color": "black", "mult": 1.0},
    "Heavy Traffic": {"penalty": 5.0, "color": "orange", "mult": 1.3},
    "Rainy/Weather": {"penalty": 3.0, "color": "blue", "mult": 1.15},
    "Road Blockage": {"penalty": 25.0, "color": "red", "mult": 1.8}
}

# =========================
# 4. CALCULATION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination", cities, index=1)

if st.button("Calculate Optimized Route"):
    # Apply Dijkstra with dynamic penalties
    temp_G = G_base.copy()
    penalty = condition_map[condition]["penalty"]
    
    # Apply penalty to random edges for variety
    random.seed(hash(condition))
    for u, v in temp_G.edges():
        if random.random() < 0.2: # Only affect 20% for speed
            temp_G[u][v]['weight'] *= penalty

    try:
        # Run Dijkstra (Very fast on a cached graph)
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # Fast lookup for total distance
        lookup_key = tuple(sorted([start_node, end_node]))
        base_total = dist_lookup.get(lookup_key)
        
        raw_sum = 0.0
        steps = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            d = G_base[u][v]['weight']
            raw_sum += d
            steps.append({'u': u, 'v': v, 'base': d})

        if base_total is None: base_total = raw_sum
        dynamic_total = base_total * condition_map[condition]["mult"]

        # --- Display ---
        res1, res2 = st.columns([1, 2])
        with res1:
            st.metric("Total Route Distance", f"{dynamic_total:.2f} km")
            st.write("### 🧭 Path Segments")
            for s in steps:
                seg_dist = (s['base'] / raw_sum) * dynamic_total
                st.write(f"➡ **{s['u']}** → **{s['v']}** = `{seg_dist:.2f} km`")

        with res2:
            m = folium.Map(location=coords[start_node], zoom_start=11)
            pts = [coords[city] for city in path]
            folium.PolyLine(pts, color=condition_map[condition]["color"], weight=6).add_to(m)
            
            folium.Marker(coords[start_node], icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(coords[end_node], icon=folium.Icon(color='red')).add_to(m)
            for node in path[1:-1]:
                folium.Marker(coords[node], icon=folium.Icon(color='blue')).add_to(m)
            
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found.")
