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
# 1. OPTIMIZED DATA LOADING (Prevents Timeouts)
# =========================
@st.cache_data
def load_fast_data():
    # Only load 3 columns to save 80% memory and time
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna()
    
    # CRITICAL: Reduce 150,000 rows down to unique routes (~4k rows)
    # This makes the graph building instant
    df_unique = df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].min().reset_index()
    
    # Create Fast Lookup Dictionary
    dist_lookup = {(row[0], row[1]): row[2] for row in df_unique.itertuples(index=False)}
    cities = sorted(list(set(df_unique['Pickup Location']).union(set(df_unique['Drop Location']))))
    
    return dist_lookup, cities, df_unique

# These run once and stay in memory
dist_lookup, cities, df_unique = load_fast_data()

# =========================
# 2. CACHED GRAPH (Built only once)
# =========================
@st.cache_resource
def build_permanent_graph(_df_unique):
    G = nx.Graph()
    for row in _df_unique.itertuples(index=False):
        G.add_edge(row[0], row[1], weight=row[2])
    return G

G_base = build_permanent_graph(df_unique)

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

# Multipliers for calculation (Path finding stays fast because we don't copy the graph)
condition_map = {
    "Normal/Clear": {"color": "black", "mult": 1.0},
    "Heavy Traffic": {"color": "orange", "mult": 1.3},
    "Rainy/Weather": {"color": "blue", "mult": 1.15},
    "Road Blockage": {"color": "red", "mult": 1.8}
}

# =========================
# 4. INSTANT CALCULATION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination", cities, index=1)

if st.button("Calculate Optimized Route"):
    try:
        # Run Dijkstra on the pre-built, small graph
        path = nx.shortest_path(G_base, source=start_node, target=end_node, weight='weight')
        
        # Total Distance Lookup
        base_total = dist_lookup.get((start_node, end_node)) or dist_lookup.get((end_node, start_node))
        
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
