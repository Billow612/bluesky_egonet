import asyncio
import httpx
import pandas as pd
import networkx as nx
import os
import time
from tqdm import tqdm
import threading
import keyboard

endpoint = 'https://public.api.bsky.app/xrpc/app.bsky.graph.getRelationships'
did_file = "Alter_dids.txt"
csv_file = "data_in_progress.csv"
graph_file = "InterAlter.graphml"
log_file = "processed_dids.txt"
limit = 30
max_concurrent_requests = 5

pause_flag = False
semaphore = asyncio.Semaphore(max_concurrent_requests)
csv_lock = asyncio.Lock()

# keyboard pause function
def listen_for_pause():
    global pause_flag
    while True:
        if keyboard.is_pressed("p"):
            pause_flag = True
            break
        time.sleep(0.1)
listener_thread = threading.Thread(target=listen_for_pause, daemon=True)
listener_thread.start()

# load DID list
with open(did_file, "r", encoding="utf-8") as f:
    did_list = [line.strip() for line in f if line.strip()]

# load processed DID list (if applicable)
if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8") as f_log:
        processed_dids = set(line.strip() for line in f_log)
    print(f"Loaded {len(processed_dids)} processed DIDs from log.")
else:
    processed_dids = set()

# load or initialise CSV data
if os.path.exists(csv_file):
    existing_df = pd.read_csv(csv_file)
    examined_pairs = {
        tuple(sorted([row.source, row.target]))
        for row in existing_df.itertuples()
    }
    print(f"Loaded {len(existing_df)} edges from '{csv_file}'.")
else:
    existing_df = pd.DataFrame(columns=["source", "target", "following", "followed_by"])
    examined_pairs = set()

# initialise the graph
G = nx.DiGraph()
G.add_nodes_from(did_list)

for row in existing_df.itertuples():
    G.add_edge(row.source, row.target, following=row.following, followed_by=row.followed_by)

# fetch alter accounts using API: getRelationships, speeding up with asyncio
async def fetch_relation_data(client, processing_did, batch):
    async with semaphore:
        try:
            params = {"actor": processing_did, "others": batch}
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json().get("relationships", [])
        except Exception as e:
            print(f"Error fetching {processing_did} → batch {len(batch)}: {e}")
            return []

# split and examine the DID relationships from 2 lists: did_list & processed_dids
async def process_did(client, processing_did):
    global pause_flag

    if processing_did in processed_dids:
        return

    others_to_check = [
        other for other in did_list
        if other != processing_did and tuple(sorted([processing_did, other])) not in examined_pairs
    ]

    tasks = []
    # split list into batches for API limit
    batches = [others_to_check[i:i + limit] for i in range(0, len(others_to_check), limit)]

    for batch in batches:
        if pause_flag:
            print("\nPaused. Type 'exit' to quit or press Enter to continue:")
            cmd = input().strip().lower()
            if cmd == 'exit':
                raise KeyboardInterrupt
            pause_flag = False
            threading.Thread(target=listen_for_pause, daemon=True).start()

        # launch fetch task for each batch
        task = asyncio.create_task(fetch_relation_data(client, processing_did, batch))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    new_rows = []
    for rels in results:
        for rel in rels:
            tgt = rel.get("did")
            following = rel.get("following", False)
            followed_by = rel.get("followedBy", False)
            if following:
                G.add_edge(processing_did, tgt, following=following, followed_by=followed_by)
                new_rows.append({
                    "source": processing_did,
                    "target": tgt,
                    "following": following,
                    "followed_by": followed_by
                })
            # mark the pair as examined
            examined_pairs.add(tuple(sorted([processing_did, tgt])))

    # add data to CSV & update log file
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        async with csv_lock:
            file_exists = os.path.exists(csv_file)
            df_new.to_csv(csv_file, mode="a", index=False, header=not file_exists)
    async with csv_lock:
        with open(log_file, "a", encoding="utf-8") as f_log:
            f_log.write(processing_did + "\n")

# main function to fetch all data
async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            process_did(client, processing_did)
            for processing_did in did_list if processing_did not in processed_dids
        ]

        # show progress with tqdm
        for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing DIDs"):
            try:
                await fut
            except Exception as e:
                print(f"Error during processing: {e}")

    nx.write_graphml(G, graph_file)
    print(f"\nGraph saved to '{graph_file}'")
    print(f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# run the main function under the keyboard stopper
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
        nx.write_graphml(G, graph_file)
        print(f"Graph saved to '{graph_file}'")
        print(f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
