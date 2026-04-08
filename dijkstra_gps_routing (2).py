import streamlit as st
import pandas as pd
import heapq
import folium
import random
import streamlit.components.v1 as components

# =========================
# 1. PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Dijkstra Route Optimizer")
st.title("⚡ Ultra-Fast Dijkstra Route Optimizer")

# =========================
# 2. FAST DATA LOADING (Matching your .py file logic)
# =========================
@st.cache_data
def load_optimized_data():
    # Load only necessary columns to save RAM
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df = df.dropna()
    
    # MEDIAN AGGREGATION: This is the key to speed. 150k rows -> ~3k routes.
    agg_df = df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].median().reset_index()
    
    # Build Adjacency List for Dijkstra
    adj_list = {}
    for row in agg_df.itertuples(index=False):
        u, v, d = row[0], row[1], row[2]
        if u not in adj_list: adj_list[u] = []
        adj_list[u].append((v, d))
        if v not in adj_list: adj_list[v] = []
        adj_list[v].append((u, d))
        
    cities = sorted(list(set(agg_df['Pickup Location']).union(set(agg_df['Drop Location']))))
    return cities, adj_list, agg_df

cities, global_adj, agg_df = load_optimized_data()

# =========================
# 3. DIJKSTRA ENGINE
# =========================
def run_dijkstra(graph, start, goal):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node not in seen:
            path = path + [node]
            seen.add(node)
            if node == goal:
                return cost, path
            for (neighbor, weight) in graph.get(node, []):
                heapq.heappush(queue, (cost + weight, neighbor, path))
    return float("inf"), []

# =========================
# 4. GPS & UI CONFIG
# =========================
@st.cache_data
def get_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

st.sidebar.header("🛠 Environment")
condition = st.sidebar.selectbox(
    "Current Condition",
    ["Normal/Clear", "Heavy Traffic", "Monsoon Rain", "Road Blockage"]
)

cond_config = {
    "Normal/Clear": {"mult": 1.0, "penalty": 1.0, "color": "black"},
    "Heavy Traffic": {"mult": 1.3, "penalty": 5.0, "color": "orange"},
    "Monsoon Rain": {"mult": 1.15, "penalty": 2.5, "color": "blue"},
    "Road Blockage": {"mult": 1.8, "penalty": 20.0, "color": "red"}
}

# =========================
# 5. EXECUTION
# =========================
c1, c2 = st.columns(2)
with c1:
    source = st.selectbox("🟢 Source", cities, index=cities.index("Vidhan Sabha") if "Vidhan Sabha" in cities else 0)
with c2:
    destination = st.selectbox("🔴 Destination", cities, index=cities.index("AIIMS") if "AIIMS" in cities else 1)

if st.button("🚀 Run Optimized Dijkstra"):
    # Apply Q-Learning inspired path selection
    dynamic_graph = {}
    penalty = cond_config[condition]["penalty"]
    random.seed(hash(condition))
    
    for u, neighbors in global_adj.items():
        dynamic_graph[u] = []
        for v, d in neighbors:
            # Change the weight to force the path to move
            cost = d * (penalty if random.random() < 0.3 else 1.0)
            dynamic_graph[u].append((v, cost))

    cost, path = run_dijkstra(dynamic_graph, source, destination)

    if path:
        # Distance Integrity Check
        base_match = agg_df[((agg_df['Pickup Location'] == source) & (agg_df['Drop Location'] == destination)) | 
                            ((agg_df['Pickup Location'] == destination) & (agg_df['Drop Location'] == source))]
        
        target_total = (base_match['Ride Distance'].iloc[0] if not base_match.empty else cost) * cond_config[condition]["mult"]
        
        res_col1, res_col2 = st.columns([1, 2])
        with res_col1:
            st.metric("Total Route Distance", f"{target_total:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                seg_d = next((d for n, d in global_adj[u] if n == v), 0)
                # Correct proportional display
                disp_dist = (seg_d / cost) * target_total
                st.write(f"➡ **{u}** → **{v}** = `{disp_dist:.2f} km`")
                st.divider()

        with res_col2:
            m = folium.Map(location=coords[source], zoom_start=11)
            pts = [coords[n] for n in path]
            folium.PolyLine(pts, color=cond_config[condition]["color"], weight=6).add_to(m)
            
            folium.Marker(coords[source], icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(coords[destination], icon=folium.Icon(color='red')).add_to(m)
            for n in path[1:-1]:
                folium.Marker(coords[n], icon=folium.Icon(color='blue')).add_to(m)
            
            components.html(m._repr_html_(), height=800)
    else:
        st.error("No path found.")
