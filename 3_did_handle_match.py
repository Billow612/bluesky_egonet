import requests
import time
from tqdm import tqdm
import os

MAX_RETRIES = 5
WAIT_TIME = 0.5
INPUT_FILE = "Alter_dids.txt"
OUTPUT_MATCHED = "matched_dids.txt"
OUTPUT_FAILED = "failed_dids.txt"

failed_dids = {}

# fetch handle names for DID list
def get_handle_from_did(did, max_retries=MAX_RETRIES, wait_time=WAIT_TIME):
    for attempt in range(max_retries):
        try:
            response = requests.get(
                "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile",
                params={"actor": did},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            handle = data.get("handle")

            if attempt > 0:
                if handle:
                    print(f"Recovered after {attempt} retries: {did} → {handle}")
                else:
                    print(f"No handle found for {did} after {attempt} retries")

            return handle

        except requests.exceptions.RequestException as e:
            print(f"Error fetching handle for {did} (attempt {attempt + 1}/{max_retries}): {e}")
            print(f"Retrying in {wait_time:.1f} seconds...")
            time.sleep(wait_time)

    print(f"✗ Failed to fetch handle for {did} after {max_retries} retries.")
    failed_dids[did] = f"after {max_retries} retries"
    return None

# load the DID list
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    did_list = [line.strip() for line in f if line.strip()]

# load the matched DIDs (if applicable)
if os.path.exists(OUTPUT_MATCHED):
    with open(OUTPUT_MATCHED, "r", encoding="utf-8") as f:
        processed_dids = {line.strip().split("\t")[0] for line in f if line.strip()}
else:
    processed_dids = set()

print(f"Loaded {len(processed_dids)} previously matched DIDs.")
print("Starting handle matching...\n")

# main function with tqdm to show the progress
with open(OUTPUT_MATCHED, "a", encoding="utf-8") as matched_file:
    for did in tqdm(did_list, desc="Matching handles", unit="DID"):
        if did in processed_dids:
            continue

        handle = get_handle_from_did(did)
        if handle:
            matched_file.write(f"{did}\t{handle}\n")
            matched_file.flush()
        else:
            failed_dids[did] = "lookup failed"

        time.sleep(0.3)

# save failed DIDs
if failed_dids:
    with open(OUTPUT_FAILED, "w", encoding="utf-8") as f:
        for did in failed_dids:
            f.write(did + "\n")

print(f"Matching complete. {len(did_list) - len(failed_dids)} matched, {len(failed_dids)} failed.")
