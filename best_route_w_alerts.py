import pandas as pd
import networkx as nx
import re
from collections import defaultdict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from geopy.distance import geodesic
import time

# ===============================
# Step 1: Load and prepare data
# ===============================

df = pd.read_csv('unique_cta_rail_stations_by_route.csv')
df_accessible = pd.read_csv('accessible_unique_CTA_L_stations_by_color.csv')

# Merge accessibility info
df = df.merge(df_accessible[['stop_name']], on='stop_name', how='left')
df['accessible'] = df['stop_name'].isin(df_accessible['stop_name']).astype(int)

# Build the graph
G = nx.Graph()

# Add nodes
for _, row in df.iterrows():
    node_name = row['stop_name'] + f" ({row['route_long_name']})"
    G.add_node(
        node_name,
        pos=(row['stop_lat'], row['stop_lon']),
        line=row['route_long_name'],
        accessible=bool(row['accessible']),
        base_name=row['stop_name']
    )

# Connect stations on the same route
for line in df['route_long_name'].unique():
    line_df = df[df['route_long_name'] == line].copy()
    line_df = line_df.sort_values(by=['stop_lat', 'stop_lon'], ascending=[False, True])
    station_list = line_df['stop_name'].tolist()
    for i in range(len(station_list) - 1):
        a = station_list[i] + f" ({line})"
        b = station_list[i + 1] + f" ({line})"
        if not G.has_edge(a, b):
            G.add_edge(a, b, line=line, weight=1)

# Add transfer edges between versions of the same station (across lines)
station_to_nodes = defaultdict(list)
for node, data in G.nodes(data=True):
    station_to_nodes[data['base_name']].append(node)

TRANSFER_PENALTY = 5
INACCESSIBLE_PENALTY = 2

for nodes in station_to_nodes.values():
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if not G.has_edge(nodes[i], nodes[j]):
                G.add_edge(nodes[i], nodes[j], line='Transfer', weight=TRANSFER_PENALTY)

# Penalize inaccessible edges
for u, v, d in G.edges(data=True):
    if not G.nodes[u]['accessible'] or not G.nodes[v]['accessible']:
        d['weight'] += INACCESSIBLE_PENALTY

# ===============================
# Step 2: Scrape Elevator Outages
# ===============================

def fetch_cta_elevator_page():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.transitchicago.com/alerts/elevators/")
        time.sleep(10)
        return driver.page_source
    finally:
        driver.quit()

def parse_inaccessible_stations_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    outages = set()
    pattern = re.compile(r"at ([A-Za-z0-9'\- &]+?) \((.*?) Lines?\)", re.IGNORECASE)
    for line in text.splitlines():
        if 'temporarily' in line.lower():
            matches = pattern.findall(line)
            for station, line in matches:
                outages.add(station.strip() + f" ({line.strip()} Line)")
    return outages

# ============================================
# Step 3: Route Planning with Accessibility
# ============================================

def find_nearest_accessible_node(name, exclude_nodes=set()):
    base_latlon = None
    for n, data in G.nodes(data=True):
        if data['base_name'].lower() == name.lower():
            base_latlon = data['pos']
            break
    if base_latlon is None:
        return None

    min_dist = float('inf')
    nearest_node = None
    for n, data in G.nodes(data=True):
        if data['accessible'] and n not in exclude_nodes:
            dist = geodesic(base_latlon, data['pos']).meters
            if dist < min_dist:
                min_dist = dist
                nearest_node = n
    return nearest_node

def resolve_station(name, graph, bad_station_names, kind='source'):
    matches = [n for n in graph.nodes if graph.nodes[n]['base_name'].lower() == name.lower()]
    if not matches:
        print(f" {kind.title()} station '{name}' not found.")
        return None

    for match in matches:
        if match not in bad_station_names:
            return match

    print(f"The {kind} station '{name}' is currently inaccessible due to an elevator outage.")
    nearest = find_nearest_accessible_node(name, exclude_nodes=bad_station_names)
    if nearest:
        print(f"Using nearest accessible station instead: {nearest}")
    else:
        print(f" No accessible nearby station found for '{name}'")
    return nearest

def find_best_route(source, target):
    print("\nFetching real-time elevator outage data...")
    html = fetch_cta_elevator_page()
    bad_station_names = parse_inaccessible_stations_from_html(html)

    if bad_station_names:
        print(f" Stations with elevator outages:\n{bad_station_names}\n")
    else:
        print(" No current elevator outages.\n")

    source_node = resolve_station(source, G, bad_station_names, kind='source')
    target_node = resolve_station(target, G, bad_station_names, kind='target')

    if not source_node or not target_node:
        print("\n Cannot compute route: Source or target is invalid or inaccessible.")
        return

    try:
        path = nx.dijkstra_path(G, source_node, target_node, weight='weight')
        total_weight = sum(G[u][v]['weight'] for u, v in zip(path[:-1], path[1:]))

        print("\n Best Accessible Route:")
        for u, v in zip(path[:-1], path[1:]):
            line = G[u][v].get('line', 'Transfer')
            print(f"  {u} ➝ {v} via {line} (weight={G[u][v]['weight']})")
        print(f"\n Total Route Weight: {total_weight:.2f}")

    except nx.NetworkXNoPath:
        print(f"\n No accessible path found from '{source}' to '{target}'.")

# ========================
# Step 4: Run the Program
# ========================
if __name__ == "__main__":
    print("CTA L-Train Route Planner\n")
    source = input("Enter source station name: ")
    target = input("Enter target station name: ")
    
    find_best_route(source, target)
