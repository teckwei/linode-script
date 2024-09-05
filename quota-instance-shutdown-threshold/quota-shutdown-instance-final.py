import requests
import time

# Your Linode API token
API_TOKEN = ""

# API endpoints
BASE_URL = "https://api.linode.com/v4"
LINODES_URL = f"{BASE_URL}/linode/instances"
ACCOUNT_SETTINGS_URL = f"{BASE_URL}/account/settings"

# remove the addtional transfer allowance for Object storage, if customer enable object storage in their account.
OBJECT_STORAGE_QUOTA_REDUCTION = 1000  # GB

# Threshold percentage (e.g., 90% of the network quota)
THRESHOLD_PERCENTAGE = 90 # percentage

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

#function to retrieve all linode instances in their account
""" def get_all_linode_ids():
    response = requests.get(LINODES_URL, headers=headers)
    response.raise_for_status()
    data = response.json()
    linode_ids = [linode['id'] for linode in data['data']]
    return linode_ids """

#function to retrieve all linode instance in their account by excluding LKE worker node
def get_all_linode_ids_without_lke():
    response = requests.get(LINODES_URL, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Filter out instances whose label starts with 'lke'
    linode_ids = [
        linode['id'] for linode in data['data'] 
        if not linode['label'].startswith('lke')
    ]

    return linode_ids

#function to retrieve the linode instance detail
def get_instance_details(linode_id):
    linode_url = f"{BASE_URL}/linode/instances/{linode_id}"
    response = requests.get(linode_url, headers=headers)
    response.raise_for_status()
    return response.json()

#function to retrieve the linode network usage per each linode instance
def get_instance_network_usage(linode_id, object_storage_enabled):
    linode_transfer_url = f"{BASE_URL}/linode/instances/{linode_id}/transfer"
    response = requests.get(linode_transfer_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    network_quota = data['quota']
    network_used = data['used'] / (1024**3)  # Convert from bytes to gigabytes

    # Subtract 1000GB from the quota if object storage is enabled
    if object_storage_enabled:
        network_quota -= OBJECT_STORAGE_QUOTA_REDUCTION

    return network_quota, network_used

#function to validate the enable status for object storage
def check_object_storage_enabled():
    """Check if Object Storage is enabled in the Linode account settings."""
    response = requests.get(ACCOUNT_SETTINGS_URL, headers=headers)
    response.raise_for_status()
    data = response.json()

    return data.get("object_storage", False)

#function to perform turn off the linode instance
def shutdown_linode(linode_id):
    shutdown_url = f"{BASE_URL}/linode/instances/{linode_id}/shutdown"
    response = requests.post(shutdown_url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    try:
        # Check if Object Storage is enabled
        object_storage_enabled = check_object_storage_enabled()
        print(f"Object Storage enabled: {object_storage_enabled}")

        linode_ids = get_all_linode_ids_without_lke()
        for linode_id in linode_ids:
            try:
                data = get_instance_details(linode_id)
                print(f"Checking Linode ID: {linode_id}")

                # Check if the instance is offline
                if data['status'] == 'offline':
                    print("Instance is already offline. No action needed.")
                    continue

                # Retrieve network_quota and network_used from get_instance_network_usage() function
                network_quota, network_used = get_instance_network_usage(linode_id, object_storage_enabled)
                print(f"Current usage: {network_used} Gigabytes. Quota limit: {network_quota} Gigabytes.")

                # Calculate the percentage of quota used
                usage_percentage = (network_used / network_quota) * 100
                print(f"Current usage is {usage_percentage:.2f}% of the quota.")

                print(THRESHOLD_PERCENTAGE, usage_percentage)

                if usage_percentage >= THRESHOLD_PERCENTAGE:
                    print(f"Network usage has reached {THRESHOLD_PERCENTAGE}% of the quota. Shutting down Linode.")
                    shutdown_response = shutdown_linode(linode_id)
                    print(f"Shutdown initiated:", shutdown_response, "\n")
                else:
                    print(f"Usage below quota limit, no action needed.\n")

                # Rate limiting: sleep for 0.15 seconds to stay within the rate limit of 800 requests per 2 minutes
                time.sleep(0.15)

            except KeyError as e:
                print(f"Error for Linode ID {linode_id}: {e}")
            except requests.exceptions.RequestException as e:
                print(f"HTTP Request failed for Linode ID {linode_id}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve Linode IDs: {e}")

if __name__ == "__main__":
    main()
