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
st.title("🚀 Dijkstra Smart Route Optimizer")

# =========================
# 1. LOAD DATA (Cached for Speed)
# =========================
@st.cache_data
def load_and_clean_data():
    # Loading the dataset from bookings.csv
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    # Dropping rows where distance is missing to ensure Dijkstra works correctly
    return df.dropna(subset=['Ride Distance'])

df = load_and_clean_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# 2. BUILD GRAPH (Cached Resource)
# =========================
@st.cache_resource
def build_base_graph(_df):
    G = nx.Graph()
    # Using itertuples for faster processing of large datasets
    for row in _df.itertuples():
        u, v, d = row[1], row[2], row[3] # Maps to Pickup, Drop, Distance
        if G.has_edge(u, v):
            # Keep only the shortest recorded distance for the base graph
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G

G_base = build_base_graph(df)

@st.cache_data
def get_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

# =========================
# 3. UI SIDEBAR
# =========================
st.sidebar.header("🛠 Route Environment")
condition = st.sidebar.selectbox(
    "Current Condition",
    ["Normal/Clear", "Heavy Traffic", "Rainy/Weather", "Road Blockage"]
)

# Environment multipliers to simulate Q-Learning path costs
condition_map = {
    "Normal/Clear": {"penalty": 1.0, "color": "black", "mult": 1.0},
    "Heavy Traffic": {"penalty": 5.0, "color": "orange", "mult": 1.3},
    "Rainy/Weather": {"penalty": 3.0, "color": "blue", "mult": 1.15},
    "Road Blockage": {"penalty": 25.0, "color": "red", "mult": 1.8}
}

# =========================
# 4. MAIN INTERFACE
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=1)

if st.button("Calculate Dijkstra Route"):
    
    # --- DIJKSTRA RE-ROUTING LOGIC ---
    temp_G = G_base.copy()
    penalty = condition_map[condition]["penalty"]
    
    # Apply environmental cost to edges to force Dijkstra to find a detour
    random.seed(hash(condition))
    for u, v in temp_G.edges():
        if random.random() < 0.4: # Affect 40% of the network
            temp_G[u][v]['weight'] *= penalty

    try:
        # EXECUTE DIJKSTRA ALGORITHM
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # Sync with Dataset Ground Truth
        direct_match = df[((df['Pickup Location'] == start_node) & (df['Drop Location'] == end_node)) | 
                          ((df['Pickup Location'] == end_node) & (df['Drop Location'] == start_node))]
        
        base_total = direct_match.iloc[0]['Ride Distance'] if not direct_match.empty else None
        
        # Calculate Segment Ratios for the newly found path
        raw_sum = 0.0
        raw_segments = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            d = G_base[u][v]['weight']
            raw_sum += d
            raw_segments.append({'u': u, 'v': v, 'base': d})

        if base_total is None: base_total = raw_sum
        dynamic_total = base_total * condition_map[condition]["mult"]
        
        # Display Final Calculation
        res1, res2 = st.columns([1, 2])
        with res1:
            st.metric("Total Route Distance", f"{dynamic_total:.2f} km")
            st.write("### 🧭 Step-by-Step Dijkstra Path")
            for seg in raw_segments:
                # Distribute total proportionally
                step_dist = (seg['base'] / raw_sum) * dynamic_total
                st.write(f"➡ **{seg['u']}** → **{seg['v']}** = `{step_dist:.2f} km`")
                st.divider()

        with res2:
            m = folium.Map(location=coords[start_node], zoom_start=11)
            
            # Draw Dijkstra Path
            pts = [coords[city] for city in path]
            folium.PolyLine(pts, color=condition_map[condition]["color"], weight=6).add_to(m)
            
            # Add Markers
            for i, city in enumerate(path):
                if i == 0:
                    folium.Marker(coords[city], icon=folium.Icon(color='green')).add_to(m)
                elif i == len(path)-1:
                    folium.Marker(coords[city], icon=folium.Icon(color='red')).add_to(m)
                else:
                    folium.Marker(coords[city], icon=folium.Icon(color='blue')).add_to(m)
            
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found under these severe conditions.")
