import requests
import time
import networkx as nx

# fetch alter accounts using API: getFollowers & getFollows
def fetch_bluesky_data(actor_handle, data_type='followers'):
    endpoints = {
        'followers': "https://public.api.bsky.app/xrpc/app.bsky.graph.getFollowers",
        'following': "https://public.api.bsky.app/xrpc/app.bsky.graph.getFollows"
    }

    if data_type not in endpoints:
        raise ValueError("data_type must be either 'followers' or 'following'")
    
    base_url = endpoints[data_type]
    limit = 100
    cursor = None
    all_data = []

    while True:
        params = {'actor': actor_handle, 'limit': limit}
        if cursor:
            params['cursor'] = cursor
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            records = data.get('followers' if data_type == 'followers' else 'follows', [])
            all_data.extend(records)
            print(f"Fetched {len(records)} {data_type}...")
            cursor = data.get('cursor')
            if not cursor:
                break
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break
        time.sleep(0.5)
    return all_data

# build the directed ego-alter graph with the fetched data
def build_graph(actor_handle, followers_data, following_data):
    G = nx.DiGraph()
    ego_id = f"@{actor_handle}"
    G.add_node(ego_id, type="ego")

    for user in followers_data:
        follower_id = user.get('did')
        handle = user.get('handle', '')
        G.add_node(follower_id, handle=handle, type="follower")
        G.add_edge(follower_id, ego_id)

    for user in following_data:
        following_id = user.get('did')
        handle = user.get('handle', '')
        G.add_node(following_id, handle=handle, type="following")
        G.add_edge(ego_id, following_id)

    return G

# input the ego handle & run the 2 functions
if __name__ == "__main__":
    actor_handle = input("Enter the ego handle (without @): ")

    print("Fetching followers...")
    followers_data = fetch_bluesky_data(actor_handle, 'followers')
    print(f"Total followers: {len(followers_data)}") 

    print("\nFetching following...")
    following_data = fetch_bluesky_data(actor_handle, 'following')
    print(f"Total following: {len(following_data)}") 

    print("\nBuilding graph...")
    G = build_graph(actor_handle, followers_data, following_data)

    output_file = f"EgoAlter.graphml"
    nx.write_graphml(G, output_file)

    print(f"\nGraph saved to {output_file}")

    # Collect all unique DIDs from followers and following
    all_dids = set()

    for user in followers_data + following_data:
        did = user.get('did')
        if did:
            all_dids.add(did)

    with open("Alter_dids.txt", "w") as f:
        for did in sorted(all_dids):
            f.write(did + "\n")

    print(f"DID list saved to Alter_dids.txt")