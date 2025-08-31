import networkx as nx

MATCHED_FILE = "matched_dids.txt"
GRAPH_FILES = ["EgoAlter.graphml", "InterAlter.graphml"]
OUTPUT_GRAPH = "FullNetwork.graphml"

# load DID-handle pairs from the matched file
did_handle_dict = {}
with open(MATCHED_FILE, "r", encoding="utf-8") as f:
    for line in f:
        did, handle = line.strip().split("\t")
        did_handle_dict[did] = handle

# read the 2 graph files
graphs = []
for path in GRAPH_FILES:
    try:
        G = nx.read_graphml(path)
        graphs.append(G)
    except Exception as e:
        print(f"Error reading {path}: {e}")

if not graphs:
    print("No valid graphs loaded Exiting.")
    exit()

# combine the graphs
G_combined = nx.compose_all(graphs)

#relabel all the nodes with matched handle names
relabel_map = {
    node: did_handle_dict[node]
    for node in G_combined.nodes()
    if node in did_handle_dict
}
G_labeled = nx.relabel_nodes(G_combined, relabel_map)

# save the labeled graph
nx.write_graphml(G_labeled, OUTPUT_GRAPH)
print(f"\nCombined graph saved as: {OUTPUT_GRAPH}")

# summarise the whole network
def summarize_graph(G):
    print("\n=== Network Summary ===")
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")
    print(f"Density: {nx.density(G):.4f}")

    in_degrees = [d for _, d in G.in_degree()]
    out_degrees = [d for _, d in G.out_degree()]
    print(f"In-degree range: {min(in_degrees)} – {max(in_degrees)}")
    print(f"Out-degree range: {min(out_degrees)} – {max(out_degrees)}")

    degree_centrality = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G)
    closeness = nx.closeness_centrality(G)

    print(f"Average degree centrality: {sum(degree_centrality.values()) / len(degree_centrality):.4f}")
    print(f"Average betweenness centrality: {sum(betweenness.values()) / len(betweenness):.4f}")
    print(f"Average closeness centrality: {sum(closeness.values()) / len(closeness):.4f}")
summarize_graph(G_labeled)
