import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import heapq
import streamlit.components.v1 as components

# =========================
# 1. CORE DIJKSTRA LOGIC
# =========================
def run_dijkstra(graph, start, goal):
    # Priority queue stores (cost, current_node, path_history)
    queue = [(0, start, [])]
    visited = set()
    
    while queue:
        (cost, current_node, path) = heapq.heappop(queue)
        
        if current_node not in visited:
            visited.add(current_node)
            path = path + [current_node]
            
            if current_node == goal:
                return cost, path
            
            for neighbor, data in graph[current_node].items():
                if neighbor not in visited:
                    # 'weight' here includes the dynamic penalties
                    total_cost = cost + data.get('weight', 0)
                    heapq.heappush(queue, (total_cost, neighbor, path))
                    
    return float("inf"), []

# =========================
# 2. STREAMLIT APP
# =========================
st.set_page_config(layout="wide")
st.title("🛣️ Dijkstra Smart Route Optimizer")

@st.cache_data
def load_data():
    df = pd.read_csv("bookings.csv", encoding="latin1")
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    return df.dropna(subset=['Ride Distance'])

df = load_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# Build Graph
@st.cache_resource
def build_graph_structure(_df):
    G = nx.Graph()
    for row in _df.itertuples():
        u, v, d = row[1], row[2], row[3] # Assuming standard column order
        if G.has_edge(u, v):
            G[u][v]['weight'] = min(G[u][v]['weight'], d)
        else:
            G.add_edge(u, v, weight=d)
    return G

G_base = build_graph_structure(df)

# Sidebar Environment
condition = st.sidebar.selectbox("Condition", ["Clear", "Traffic", "Rain", "Block"])
penalties = {"Clear": 1.0, "Traffic": 2.5, "Rain": 1.8, "Block": 10.0}

# Selection
col1, col2 = st.columns(2)
start_city = col1.selectbox("Source", cities, index=0)
goal_city = col2.selectbox("Destination", cities, index=1)

if st.button("🚀 Run Dijkstra Optimization"):
    # Apply Dynamic Penalties
    temp_G = G_base.copy()
    random.seed(hash(condition))
    for u, v in temp_G.edges():
        if random.random() < 0.3:
            temp_G[u][v]['weight'] *= penalties[condition]
            
    # RUN DIJKSTRA
    # Note: We convert nx graph to dict for our custom Dijkstra function
    graph_dict = nx.to_dict_of_dicts(temp_G)
    total_cost, path = run_dijkstra(graph_dict, start_city, goal_city)
    
    if path:
        st.success(f"Optimized Path Found: {' → '.join(path)}")
        st.metric("Total Path Cost", f"{total_cost:.2f} km")
        
        # Step-by-Step Distance (Using original Dataset values for accuracy)
        st.write("### 🧭 Segment Breakdown")
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            # Show original vs penalized if you wish, here we show penalized
            st.write(f"📍 {u} to {v}: **{temp_G[u][v]['weight']:.2f} km**")
    else:
        st.error("No path exists between selected nodes.")
