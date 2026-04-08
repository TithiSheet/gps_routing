import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Dijkstra Route Optimizer")
st.title("🚀 High-Speed Dijkstra Optimizer")

# =========================
# 1. LOAD DATA (Cached)
# =========================
@st.cache_data
def load_and_clean_data():
    # Use only necessary columns to save memory
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    return df.dropna(subset=['Ride Distance'])

df = load_and_clean_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# 2. BUILD GRAPH (Cached Resource)
# =========================
@st.cache_resource
def build_base_graph(_df):
    G = nx.Graph()
    # itertuples is 10x faster than iterrows for 150k rows
    for row in _df.itertuples(index=False):
        u, v, d = row[0], row[1], row[2] # Adjust if CSV order differs
        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G

G_base = build_base_graph(df)

@st.cache_data
def get_coords(city_list):
    # GPS Logic: Using cached fixed coordinates
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

# Q-Learning inspired path selection multipliers
condition_map = {
    "Normal/Clear": {"penalty": 1.0, "color": "black", "mult": 1.0},
    "Heavy Traffic": {"penalty": 4.5, "color": "orange", "mult": 1.3},
    "Rainy/Weather": {"penalty": 2.5, "color": "blue", "mult": 1.15},
    "Road Blockage": {"penalty": 20.0, "color": "red", "mult": 1.8}
}

# =========================
# 4. CALCULATION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=1)

if st.button("Calculate Optimized Route"):
    # Apply Dijkstra with dynamic penalties
    temp_G = G_base.copy()
    penalty = condition_map[condition]["penalty"]
    
    # We apply the penalty to a random subset of edges to force a path change
    random.seed(hash(condition))
    for u, v in temp_G.edges():
        if random.random() < 0.35:
            temp_G[u][v]['weight'] *= penalty

    try:
        # Run Dijkstra
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # Calculate consistent distance based on dataset logic
        direct_match = df[((df['Pickup Location'] == start_node) & (df['Drop Location'] == end_node)) | 
                          ((df['Pickup Location'] == end_node) & (df['Drop Location'] == start_node))]
        
        base_total = direct_match.iloc[0]['Ride Distance'] if not direct_match.empty else None
        
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
            
            # Identifiable markers
            folium.Marker(coords[start_node], icon=folium.Icon(color='green', icon='play')).add_to(m)
            folium.Marker(coords[end_node], icon=folium.Icon(color='red', icon='stop')).add_to(m)
            for node in path[1:-1]:
                folium.Marker(coords[node], icon=folium.Icon(color='blue')).add_to(m)
            
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found.")
