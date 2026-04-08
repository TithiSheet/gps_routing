import streamlit as st
import pandas as pd
import heapq
import folium
import random
from streamlit_folium import st_folium

# ==========================================
# 1. DATA & CONSTANTS (From your GPS script)
# ==========================================
# (Note: Paste your full CITY_COORDS dictionary here)
CITY_COORDS = {
    "AIIMS": (28.5672, 77.2100), "Adarsh Nagar": (28.7167, 77.1833),
    "Vidhan Sabha": (28.6812, 77.2223), "IGI Airport": (28.5562, 77.1000),
    "Madipur": (28.6740, 77.1182), "Anand Vihar": (28.6469, 77.3152)
    # ... include all 176 from your file
}

st.set_page_config(layout="wide", page_title="GPS Route Optimizer")

# ==========================================
# 2. CORE ROUTING ENGINE
# ==========================================
def dijkstra(nodes, edges, start, goal):
    queue = [(0, start, [])]
    seen = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node not in seen:
            path = path + [node]
            seen.add(node)
            if node == goal:
                return (cost, path)
            for (neighbor, weight) in edges.get(node, []):
                heapq.heappush(queue, (cost + weight, neighbor, path))
    return float("inf"), []

# ==========================================
# 3. STREAMLIT UI
# ==========================================
st.title("🗺️ Smart GPS Route Optimizer")

# Sidebar for Dynamic Environments
st.sidebar.header("🌍 Environment Settings")
env_condition = st.sidebar.selectbox(
    "Select Current Condition",
    ["Clear Sky", "Heavy Traffic", "Monsoon Rain", "Road Closure"]
)

# Q-Learning inspired weight multipliers
penalties = {
    "Clear Sky": 1.0,
    "Heavy Traffic": 3.5,
    "Monsoon Rain": 2.2,
    "Road Closure": 15.0
}

col1, col2 = st.columns([1, 3])

with col1:
    source = st.selectbox("🟢 Source Location", sorted(CITY_COORDS.keys()), index=0)
    destination = st.selectbox("🔴 Destination", sorted(CITY_COORDS.keys()), index=1)
    
    # Load and build graph
    df = pd.read_csv("bookings.csv")
    df = df.dropna()
    
    # Apply dynamic weights based on environment
    penalty = penalties[env_condition]
    graph = {}
    for _, row in df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        # Apply penalty randomly to simulate specific road blocks
        current_weight = d * (penalty if random.random() < 0.4 else 1.0)
        
        if u not in graph: graph[u] = []
        graph[u].append((v, current_weight))
        if v not in graph: graph[v] = []
        graph[v].append((u, current_weight))

    if st.button("🚀 Optimize Route"):
        cost, path = dijkstra(CITY_COORDS.keys(), graph, source, destination)
        
        if path:
            st.success(f"Path Found: {len(path)} nodes")
            st.metric("Total Travel Cost", f"{cost:.2f} units")
            
            # Step-by-step display
            st.write("### 🧭 Route Steps")
            for i in range(len(path)-1):
                st.write(f"📍 {path[i]} ⮕ {path[i+1]}")
        else:
            st.error("No path found under these conditions.")

with col2:
    # Map Visualization
    if 'path' in locals() and path:
        # Center map at source
        m = folium.Map(location=CITY_COORDS[source], zoom_start=12)
        
        # Plot full path line
        points = [CITY_COORDS[node] for node in path]
        folium.PolyLine(points, color="blue", weight=5, opacity=0.8).add_to(m)
        
        # Add specific markers
        folium.Marker(CITY_COORDS[source], popup="START", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker(CITY_COORDS[destination], popup="END", icon=folium.Icon(color='red')).add_to(m)
        
        # Middle nodes
        for node in path[1:-1]:
            folium.Marker(CITY_COORDS[node], popup=node, icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)
            
        st_folium(m, width=900, height=600)
    else:
        st.info("Select locations and click 'Optimize' to view the map.")
