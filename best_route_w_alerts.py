import pandas as pd
import networkx as nx
import requests
import feedparser

# ===============================
# Step 1: Load and prepare data
# ===============================

# Load station data
df = pd.read_csv('unique_cta_rail_stations_by_route.csv')  # All stations
df_accessible = pd.read_csv('accessible_unique_CTA_L_stations_by_color.csv')  # Accessible stations

# Merge accessibility info
df = df.merge(df_accessible[['stop_name']], on='stop_name', how='left')
df['accessible'] = df['stop_name'].isin(df_accessible['stop_name']).astype(int)

# Build the graph
G = nx.Graph()

# Add stations as nodes
for _, row in df.iterrows():
    G.add_node(
        row['stop_name'],
        pos=(row['stop_lat'], row['stop_lon']),
        line=row['route_long_name'],
        accessible=bool(row['accessible']),
        name=row['stop_name']  # Add name field for easy matching
    )

# Add edges (connections between adjacent stations)
for line in df['route_long_name'].unique():
    line_stations = df[df['route_long_name'] == line].sort_values(by=['stop_lat', 'stop_lon'], ascending=[False, True])
    station_list = line_stations['stop_name'].tolist()

    for i in range(len(station_list) - 1):
        station_a = station_list[i]
        station_b = station_list[i + 1]

        if not G.has_edge(station_a, station_b):
            G.add_edge(station_a, station_b, line=line, weight=1)

TRANSFER_PENALTY = 5
INACCESSIBLE_PENALTY = 2

# Add transfer self-edges
for node in G.nodes():
    served_lines = df[df['stop_name'] == node]['route_long_name'].unique()
    if len(served_lines) > 1:
        G.add_edge(node, node, transfer=True, weight=TRANSFER_PENALTY)

# Adjust weights based on accessibility
for u, v, d in G.edges(data=True):
    accessible_u = G.nodes[u]['accessible']
    accessible_v = G.nodes[v]['accessible']
    if not accessible_u or not accessible_v:
        d['weight'] += INACCESSIBLE_PENALTY

# ================================================
# Step 2: Real-Time Elevator Outage Fetch Function
# ================================================

def get_inaccessible_station_names():
    url = "https://www.transitchicago.com/elevatorstatus/"
    feed = feedparser.parse(url)
    
    outages = {entry.title.split(' - ')[0].strip() 
               for entry in feed.entries 
               if 'temporarily' in entry.title.lower()}
    
    return outages

# =========================================
# Step 3: Route Planning with Accessibility
# =========================================

def find_best_route(source, target):
    source = source.strip()
    target = target.strip()

    # Fetch elevator outages
    print("\nFetching real-time elevator outages...")
    bad_station_names = get_inaccessible_station_names()

    if bad_station_names:
        print(f"Current stations with elevator outages:\n{bad_station_names}\n")
    else:
        print("No current elevator outages.\n")

    # Create a temporary graph removing inaccessible stations
    temp_G = G.copy()
    to_remove = [n for n, d in temp_G.nodes(data=True) if d['name'] in bad_station_names]
    temp_G.remove_nodes_from(to_remove)

    # Check if source and target are still available
    if source not in temp_G.nodes:
        print(f" Source station '{source}' is currently inaccessible due to elevator outage.")
        return
    if target not in temp_G.nodes:
        print(f" Target station '{target}' is currently inaccessible due to elevator outage.")
        return

    source_accessible = temp_G.nodes[source]['accessible']
    target_accessible = temp_G.nodes[target]['accessible']

    if not source_accessible:
        print(f"⚠️  Source station '{source}' is not accessible!")
    if not target_accessible:
        print(f"⚠️  Target station '{target}' is not accessible!")

    try:
        # Dijkstra’s algorithm using temp_G
        path = nx.dijkstra_path(temp_G, source, target, weight='weight')
        total_weight = 0

        print("\n🚆 Best Route from", source, "to", target, ":")
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            # Fetch edge data from temp_G
            weight = temp_G[u][v]['weight']
            line = temp_G[u][v].get('line', 'Transfer')
            print(f"  {u} -> {v} via {line} (weight={weight})")
            total_weight += weight

        print(f"\nTotal Route Weight: {total_weight}")

    except nx.NetworkXNoPath:
        print(f"No accessible path found from '{source}' to '{target}'.")

# ========================
# Step 4: Run the Program
# ========================

if __name__ == "__main__":
    print("CTA L-Train Route Planner \n")
    source = input("Enter source station name: ")
    target = input("Enter target station name: ")

    find_best_route(source, target)
