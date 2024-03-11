import requests
import json
from datetime import datetime, timedelta, timezone
import time

# Replace with your Linode API key and Object Storage cluster ID
linode_api_key = "74a2ebc388f27a41b2b77e31b37c890601c3c85ff2a0e6c29aeaa3290506e004"
bucket_name = "testing-bucket-project"
cluster_id = "jp-osa-1"
permission = "read_write" #setup your access key permission
create_function = True  #if you want to perform delete existing access key, kindly set to False and it will proceed for deletion of the access key which is expired based on timeframe created.

# Function to handle API requests with rate limiting
def api_request_with_limit(endpoint, method="GET", headers=None, json_data=None, rate_limit=800, per_seconds=120):
    # Calculate the time interval between requests based on the rate limit
    interval = per_seconds / rate_limit

    # Check if enough time has passed since the last request
    current_time = time.time()
    elapsed_time = current_time - api_request_with_limit.last_request_time
    if elapsed_time < interval:
        # If not enough time has passed, sleep for the remaining time
        sleep_time = interval - elapsed_time
        time.sleep(sleep_time)

    # Perform the API request
    response = requests.request(method, endpoint, headers=headers, json=json_data)

    # Update the last request time
    api_request_with_limit.last_request_time = time.time()

    return response

# Initialize the last request time to the current time
api_request_with_limit.last_request_time = time.time()

def delete_api_key(api_key_id):
    endpoint = f"https://api.linode.com/v4/object-storage/keys/{api_key_id}"
    headers = {
        "Authorization": f"Bearer {linode_api_key}",
        "Content-Type": "application/json",
    }
    response = api_request_with_limit(endpoint, method="DELETE", headers=headers)
    return response

# Later, read the stored_keys from the JSON file
with open("stored_keys.json", "r") as json_file:
    stored_keys = json.load(json_file)

current_time = datetime.now()

# Iterate through stored keys and delete those created more than delete_timeframe ago (404 error code = old access which expired based on the creation date)
for label, key_info in stored_keys.items():
    creation_time = datetime.strptime(key_info["creation_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    delete_timeframe_minutes = key_info["delete_timeframe"]
    
    if current_time - creation_time > timedelta(minutes=delete_timeframe_minutes):
        response_delete = delete_api_key(key_info["id"])
        if response_delete.status_code == 200:
            print(f"API key '{label}' deleted successfully.")
            # Mark the key as deleted in the stored_keys dictionary
            key_info["deleted"] = True
        else:
            # Display a different error message if the key is not marked as deleted
            if "deleted" in key_info or key_info.get("deleted", False):
                print(f"API key '{label}' was old record which deleted previously.")
            else:
                print(f"Failed to delete API key '{label}'. Status code: {response_delete.status_code}")

# Update the JSON file with the modified stored_keys
with open("stored_keys.json", "w") as json_file:
    json.dump(stored_keys, json_file, default=str)
