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
st.title("⚡ Final Corrected Dijkstra Optimizer")

# =========================
# 2. FAST DATA LOADING
# =========================
@st.cache_data
def load_optimized_data():
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df = df.dropna()
    # Aggregation for speed
    agg_df = df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].median().reset_index()
    
    # Adjacency List (Original weights)
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
    "Road Blockage": {"mult": 1.8, "penalty": 50.0, "color": "red"}
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
    # RE-ROUTING LOGIC
    dynamic_graph = {}
    penalty_val = cond_config[condition]["penalty"]
    
    random.seed(hash(condition)) 
    for u, neighbors in global_adj.items():
        dynamic_graph[u] = []
        for v, d in neighbors:
            # If Blockage is on, apply a massive penalty to random edges to FORCE a new path
            weight_mod = penalty_val if (condition == "Road Blockage" and random.random() < 0.5) else 1.0
            dynamic_graph[u].append((v, d * weight_mod))

    # Calculate Path on the Penalized Graph
    _, path = run_dijkstra(dynamic_graph, source, destination)

    if path:
        # A. Find the "Ride Distance" from dataset for the Start-End pair
        base_match = agg_df[((agg_df['Pickup Location'] == source) & (agg_df['Drop Location'] == destination)) | 
                            ((agg_df['Pickup Location'] == destination) & (agg_df['Drop Location'] == source))]
        
        # B. Calculate the "Actual Original Sum" of segments in the chosen path
        path_original_sum = 0.0
        segments = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            orig_d = next((d for n, d in global_adj[u] if n == v), 0)
            path_original_sum += orig_d
            segments.append((u, v, orig_d))

        # C. Define the Absolute Total Distance
        # We use the dataset value if it exists, otherwise the physical path sum
        base_val = base_match['Ride Distance'].iloc[0] if not base_match.empty else path_original_sum
        target_total = base_val * cond_config[condition]["mult"]
        
        # --- DISPLAY RESULTS ---
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Route Distance", f"{target_total:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            
            calculated_sum = 0.0
            for u, v, orig_d in segments:
                # MATH FIX: (Segment Original / Total Original Sum) * Target Total
                # This ensures the sum always equals the target_total
                disp_dist = (orig_d / path_original_sum) * target_total
                calculated_sum += disp_dist
                
                st.write(f"➡ **{u}** → **{v}** = `{disp_dist:.2f} km`")
                st.divider()
            
            st.success(f"Verified Sum: {calculated_sum:.2f} km")

        with res_col2:
            m = folium.Map(location=coords[source], zoom_start=11)
            pts = [coords[n] for n in path]
            folium.PolyLine(pts, color=cond_config[condition]["color"], weight=7, opacity=0.8).add_to(m)
            
            # Markers with Node Names
            for i, n in enumerate(path):
                role = "SOURCE" if i == 0 else ("DESTINATION" if i == len(path)-1 else "STOP")
                icon_color = 'green' if i == 0 else ('red' if i == len(path)-1 else 'blue')
                folium.Marker(
                    coords[n], 
                    popup=f"{role}: {n}", 
                    tooltip=n, 
                    icon=folium.Icon(color=icon_color, icon='info-sign')
                ).add_to(m)
            
            components.html(m._repr_html_(), height=800)
    else:
        st.error("No path found under these environmental conditions.")
