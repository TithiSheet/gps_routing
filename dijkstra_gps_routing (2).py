import streamlit as st
import pandas as pd
import heapq
import folium
import random
import time  # New import for dynamic seeding
import streamlit.components.v1 as components

# =========================
# 1. PAGE CONFIG & STYLING
# =========================
st.set_page_config(layout="wide", page_title="Dijkstra Route Optimizer")

# Custom CSS for larger fonts and buttons
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-size: 19px !important; /* Larger global font */
    }
    .stButton>button {
        width: 100% !important;
        height: 60px !important; /* Larger button */
        font-size: 24px !important;
        font-weight: bold !important;
        background-color: #007BFF !important;
        color: white !important;
        border-radius: 10px !important;
    }
    .stSelectbox label {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚗 Smart Route Optimizer")

# =========================
# 2. FAST DATA LOADING
# =========================
@st.cache_data
def load_optimized_data():
    df = pd.read_csv("bookings.csv", usecols=["Pickup Location", "Drop Location", "Ride Distance"], encoding="latin1")
    df = df.dropna()
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

st.sidebar.header("🛠 Environment Settings")
condition = st.sidebar.selectbox("Current Condition", ["Normal/Clear", "Road Blockage"])

cond_config = {
    "Normal/Clear": {"mult": 1.0, "penalty": 1.0, "color": "black"},
    "Road Blockage": {"mult": 1.8, "penalty": 100.0, "color": "red"}
}

route_color = cond_config[condition]["color"]

# =========================
# 5. EXECUTION
# =========================
c1, c2 = st.columns(2)
with c1:
    source = st.selectbox("🟢 Source Location", cities, index=cities.index("Vidhan Sabha") if "Vidhan Sabha" in cities else 0)
with c2:
    destination = st.selectbox("🔴 Destination Location", cities, index=cities.index("AIIMS") if "AIIMS" in cities else 1)

if st.button("🔍 SEARCH OPTIMIZED ROUTE"):
    # RE-ROUTING LOGIC
    dynamic_graph = {}
    penalty_val = cond_config[condition]["penalty"]
    
    # CHANGE: Use current time as seed so blockages shift every time you click
    random.seed(time.time()) 
    
    for u, neighbors in global_adj.items():
        dynamic_graph[u] = []
        for v, d in neighbors:
            # Randomly apply penalties to different edges to ensure path variety
            weight_mod = penalty_val if (condition == "Road Blockage" and random.random() < 0.6) else 1.0
            dynamic_graph[u].append((v, d * weight_mod))

    _, path = run_dijkstra(dynamic_graph, source, destination)

    if path:
        base_match = agg_df[((agg_df['Pickup Location'] == source) & (agg_df['Drop Location'] == destination)) | 
                            ((agg_df['Pickup Location'] == destination) & (agg_df['Drop Location'] == source))]
        
        path_original_sum = 0.0
        segments = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            orig_d = next((d for n, d in global_adj[u] if n == v), 0)
            path_original_sum += orig_d
            segments.append((u, v, orig_d))

        base_val = base_match['Ride Distance'].iloc[0] if not base_match.empty else path_original_sum
        target_total = base_val * cond_config[condition]["mult"]
        
        st.info(f"Environment: **{condition}**.")
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Calculated Distance", f"{target_total:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            
            for u, v, orig_d in segments:
                disp_dist = (orig_d / path_original_sum) * target_total if path_original_sum > 0 else 0
                st.write(f"➡ **{u}** → **{v}** = `{disp_dist:.2f} km`")
                st.divider()
            
        with res_col2:
            m = folium.Map(location=coords[source], zoom_start=11)
            pts = [coords[n] for n in path]
            folium.PolyLine(pts, color=route_color, weight=8, opacity=0.9).add_to(m)
            
            for i, n in enumerate(path):
                role = "START" if i == 0 else ("GOAL" if i == len(path)-1 else "NODE")
                icon_color = 'green' if i == 0 else ('red' if i == len(path)-1 else 'blue')
                folium.Marker(
                    coords[n], 
                    popup=f"{role}: {n}", 
                    tooltip=n, 
                    icon=folium.Icon(color=icon_color, icon='car', prefix='fa')
                ).add_to(m)
            
            legend_html = f'''
                <div style="position: fixed; 
                            bottom: 50px; left: 50px; width: 200px; height: 130px; 
                            background-color: white; border:3px solid {route_color}; z-index:9999; font-size:16px;
                            padding: 10px; border-radius: 10px; font-weight: bold;">
                📍 Route Legend<br>
                 <span style="color: green;">●</span> Source<br>
                 <span style="color: blue;">●</span> Intermediate<br>
                 <span style="color: red;">●</span> Destination<br>
                 <span style="color: {route_color};"><b>—</b></span> <b>{condition} Path</b>
                </div>
                '''
            m.get_root().html.add_child(folium.Element(legend_html))
            components.html(m._repr_html_(), height=800)
    else:
        st.error("The environment is too restricted to find a viable path. Try changing conditions.")
