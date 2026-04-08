import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Instant Optimizer")
st.title("⚡ Ultra-Fast Route Optimizer")

# =========================
# 1. INSTANT DATA LOADING
# =========================
@st.cache_data
def load_optimized_data():
    # Load only necessary columns
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna()
    
    # Pre-aggregate to unique routes to shrink the graph size significantly
    agg_df = df.groupby(["Pickup Location", "Drop Location"])["Ride Distance"].min().reset_index()
    
    # Fast lookup dictionary
    dist_lookup = {(row[0], row[1]): row[2] for row in agg_df.itertuples(index=False)}
    cities = sorted(list(set(agg_df['Pickup Location']).union(set(agg_df['Drop Location']))))
    
    return dist_lookup, cities, agg_df

dist_lookup, cities, agg_df = load_optimized_data()

# =========================
# 2. PERMANENT GRAPH RESOURCE
# =========================
@st.cache_resource
def build_permanent_graph(_agg_df):
    G = nx.Graph()
    for row in _agg_df.itertuples(index=False):
        G.add_edge(row[0], row[1], weight=row[2])
    return G

G_base = build_permanent_graph(agg_df)

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
        # PATHFINDING: Directly on G_base (No more slow copying!)
        # We find the path first
        path = nx.shortest_path(G_base, source=start_node, target=end_node, weight='weight')
        
        # Calculate distance
        # Check both directions in the lookup
        base_total = dist_lookup.get((start_node, end_node)) or dist_lookup.get((end_node, start_node))
        
        raw_sum = 0.0
        steps = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            d = G_base[u][v]['weight']
            raw_sum += d
            steps.append({'u': u, 'v': v, 'base': d})

        # Apply multiplier
        if base_total is None: base_total = raw_sum
        dynamic_total = base_total * condition_map[condition]["mult"]

        # --- Display Results ---
        res1, res2 = st.columns([1, 2])
        with res1:
            st.metric("Total Route Distance", f"{dynamic_total:.2f} km")
            st.write("### 🧭 Path Segments")
            for s in steps:
                # Proportional calculation
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
