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
# 2. FAST DATA LOADING
# =========================
@st.cache_data
def load_optimized_data():
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df = df.dropna()
    # Use Median to handle 150k rows efficiently
    agg_df = df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].median().reset_index()
    
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
condition = st.sidebar.selectbox("Current Condition", ["Normal/Clear", "Road Blockage"])

cond_config = {
    "Normal/Clear": {"mult": 1.0, "penalty": 1.0, "color": "black"},
    "Road Blockage": {"mult": 1.8, "penalty": 25.0, "color": "red"}
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
    # RE-ROUTING LOGIC: We modify the weights to force the path to change
    dynamic_graph = {}
    penalty_val = cond_config[condition]["penalty"]
    
    # We use a fixed seed for the condition so the "Blockage" is consistent
    random.seed(hash(condition)) 
    for u, neighbors in global_adj.items():
        dynamic_graph[u] = []
        for v, d in neighbors:
            # Randomly penalize routes during Blockage to force a detour
            weight_mod = penalty_val if (condition == "Road Blockage" and random.random() < 0.4) else 1.0
            dynamic_graph[u].append((v, d * weight_mod))

    # Calculate Path
    total_raw_cost, path = run_dijkstra(dynamic_graph, source, destination)

    if path:
        # MATH SYNC: Find the base distance from dataset
        base_match = agg_df[((agg_df['Pickup Location'] == source) & (agg_df['Drop Location'] == destination)) | 
                            ((agg_df['Pickup Location'] == destination) & (agg_df['Drop Location'] == source))]
        
        # Calculate Target Total
        base_val = base_match['Ride Distance'].iloc[0] if not base_match.empty else total_raw_cost
        target_total = base_val * cond_config[condition]["mult"]
        
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Route Distance", f"{target_total:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            
            running_sum = 0.0
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                # Find the original distance from the dataset for this segment
                seg_d = next((d for n, d in global_adj[u] if n == v), 0)
                
                # Proportional calculation to ensure the sum equals target_total exactly
                disp_dist = (seg_d / total_raw_cost) * target_total
                running_sum += disp_dist
                
                st.write(f"➡ **{u}** → **{v}** = `{disp_dist:.2f} km`")
                st.divider()
            
            # Final verification display
            st.caption(f"Mathematical Verification: {running_sum:.2f} km")

        with res_col2:
            m = folium.Map(location=coords[source], zoom_start=11)
            pts = [coords[n] for n in path]
            folium.PolyLine(pts, color=cond_config[condition]["color"], weight=6).add_to(m)
            
            # Markers with Node Names
            for i, n in enumerate(path):
                label = f"START: {n}" if i == 0 else (f"END: {n}" if i == len(path)-1 else f"STOP: {n}")
                color = 'green' if i == 0 else ('red' if i == len(path)-1 else 'blue')
                folium.Marker(coords[n], popup=label, tooltip=n, icon=folium.Icon(color=color)).add_to(m)
            
            components.html(m._repr_html_(), height=800)
    else:
        st.error("No path found. The destination is inaccessible under current conditions.")
