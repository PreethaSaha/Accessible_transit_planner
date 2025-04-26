import pandas as pd
import networkx as nx

#Load the data
df = pd.read_csv('unique_cta_rail_stations_by_route.csv')  # Full stations
df_accessible = pd.read_csv('accessible_unique_CTA_L_stations_by_color.csv')  # Accessible subset

# Merge to add accessibility info
df = df.merge(df_accessible[['stop_name']], on='stop_name', how='left')
df['accessible'] = df['stop_name'].isin(df_accessible['stop_name']).astype(int)

# Build the graph
G = nx.Graph()

# Add nodes
for _, row in df.iterrows():
    G.add_node(
        row['stop_name'],
        pos=(row['stop_lat'], row['stop_lon']),
        line=row['route_long_name'],
        accessible=bool(row['accessible'])
    )

# Add edges (connections along a line)
for line in df['route_long_name'].unique():
    line_stations = df[df['route_long_name'] == line].sort_values(by=['stop_lat', 'stop_lon'], ascending=[False, True])
    station_list = line_stations['stop_name'].tolist()
    
    for i in range(len(station_list) - 1):
        station_a = station_list[i]
        station_b = station_list[i + 1]
        
        if not G.has_edge(station_a, station_b):
            G.add_edge(station_a, station_b, line=line, weight=1)

# Define penalties (you tweak these based on your use case)
TRANSFER_PENALTY = 5
INACCESSIBLE_PENALTY = 2

# Add transfer self-edges (for stations served by multiple lines)
for node in G.nodes():
    served_lines = df[df['stop_name'] == node]['route_long_name'].unique()
    if len(served_lines) > 1:
        G.add_edge(node, node, transfer=True, weight=TRANSFER_PENALTY)

# Adjust edge weights for accessibility
for u, v, d in G.edges(data=True):
    accessible_u = G.nodes[u]['accessible']
    accessible_v = G.nodes[v]['accessible']
    if not accessible_u or not accessible_v:
        d['weight'] += INACCESSIBLE_PENALTY

# --- Pathfinding Section ---

def find_best_route(G, source, target):
    if source not in G:
        raise ValueError(f"Source station '{source}' not found in the network.")
    if target not in G:
        raise ValueError(f"Target station '{target}' not found in the network.")
    
    # Check accessibility
    source_accessible = G.nodes[source]['accessible']
    target_accessible = G.nodes[target]['accessible']
    
    if not source_accessible:
        print(f"Warning: Source station '{source}' is NOT accessible.")
    if not target_accessible:
        print(f"Warning: Target station '{target}' is NOT accessible.")
    
    try:
        path = nx.dijkstra_path(G, source, target, weight='weight')
        total_weight = nx.dijkstra_path_length(G, source, target, weight='weight')
    except nx.NetworkXNoPath:
        print(f"No path found between {source} and {target}.")
        return

    print(f"\nBest Route from '{source}' to '{target}':")
    print("-" * 40)
    
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge_data = G.get_edge_data(u, v)
        
        # If multiple edges exist, choose the first
        if isinstance(edge_data, dict) and 0 in edge_data:
            edge_data = edge_data[0]
        
        line = edge_data.get('line', 'Transfer')
        weight = edge_data['weight']
        
        if u == v:
            print(f"Transfer at '{u}' (penalty weight {weight})")
        else:
            print(f"From '{u}' to '{v}' via {line} line (weight {weight})")
    
    print("-" * 40)
    print(f"Total trip weight: {total_weight}")

# Example Usage:

# Asks for user input
source_station = input("Enter source station name: ").strip()
target_station = input("Enter target station name: ").strip()

try:
    find_best_route(G, source_station, target_station)
except ValueError as e:
    print(e)
