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

def create_api_key(label, cluster_id):
    endpoint = "https://api.linode.com/v4/object-storage/keys"
    headers = {
        "Authorization": f"Bearer {linode_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "label": label,
        "bucket_access": [
            {
                "cluster": cluster_id,
                "bucket_name": bucket_name,
                "permissions": permission
            },
        ],
    }
    response = api_request_with_limit(endpoint, method="POST", headers=headers, json_data=data)
    return response

def create_and_store_key(label, cluster_id, delete_timeframe_minutes, key_storage):

    # Check if the label already exists in stored_keys
    if label in key_storage:
        print(f"API key with label '{label}' already exists. Skipping creation.")
        return
    
    # Create API key
    response_create = create_api_key(label, cluster_id)

    if response_create.status_code == 200:
        print(f"API key '{label}' created successfully.")
        key_info = response_create.json()
        key_info["creation_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # Convert to string
        key_info["delete_timeframe"] = delete_timeframe_minutes  # Store the delete timeframe in minutes
        key_info["bucket_name"] = bucket_name
        key_info["permission"] = permission
        key_storage[label] = key_info  # Store the key info for later deletion
    else:
        print(f"Failed to create API key '{label}'. Status code: {response_create.status_code}")
        return

# Dictionary to store key info
stored_keys = {}

# Load existing records from the JSON file, if any
try:
    with open("stored_keys.json", "r") as json_file:
        stored_keys = json.load(json_file)
except FileNotFoundError:
    pass  # File not found, ignore and proceed with an empty dictionary

if create_function == True:
    # Create and store API keys with rate limiting
    create_and_store_key("final-1-5", cluster_id, 1, stored_keys)  # Create key_1, delete after 1 minute
    create_and_store_key("final-2-6", cluster_id, 2, stored_keys)  # Create key_2, delete after 2 minutes

# Save the combined stored_keys to a JSON file
with open("stored_keys.json", "w") as json_file:
    json.dump(stored_keys, json_file, default=str)  # Use default=str to serialize datetime objects to strings

# Display the stored keys
print("Stored Keys:")
for label, key_info in stored_keys.items():
    print(f"{label}: {key_info['id']} (Created at: {key_info['creation_time']}, Delete after: {key_info['delete_timeframe']} minutes)")

# Later, read the stored_keys from the JSON file
with open("stored_keys.json", "r") as json_file:
    stored_keys = json.load(json_file)
    
