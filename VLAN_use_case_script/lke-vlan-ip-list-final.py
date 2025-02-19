import requests
import csv

# Linode API Token
API_TOKEN = ""

# Base API URL
BASE_URL = "https://api.linode.com/v4"

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

# List of LKE Cluster ID
clusterID = 304292

# Output Table to Store VLAN Addresses
outputTable = []


def api_call(endpoint, method="GET", data=None, params=None):
    """Helper function to make API calls with pagination handling."""
    url = f"{BASE_URL}{endpoint}"
    try:
        # Add pagination parameters if available
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error with API call to {url}: {e}")
        return None

#get the list of nodes from node pools in the mentioned LKE cluster
def get_pools(cluster_id):
    """Fetch pools for a given cluster with pagination."""
    endpoint = f"/lke/clusters/{cluster_id}/pools"
    pools = []
    params = {"page": 1, "page_size": 50}  # Start with page 1 and a reasonable page size
    while True:
        response = api_call(endpoint, params=params)
        if response and "data" in response:
            pools.extend(response["data"])
            # Check if there's another page
            if "next" in response:
                params["page"] += 1
            else:
                break
        else:
            break
    return pools


def get_pool_nodes(pool):
    """Get nodes within a pool."""
    return pool.get("nodes", [])

#get the Linode instance configuration
def get_configs(node_id):
    """Fetch config IDs for a specific node with pagination."""
    endpoint = f"/linode/instances/{node_id}/configs"
    configs = []
    params = {"page": 1, "page_size": 50}  # Start with page 1 and a reasonable page size
    while True:
        response = api_call(endpoint, params=params)
        if response and "data" in response:
            configs.extend(response["data"])
            # Check if there's another page
            if "next" in response:
                params["page"] += 1
            else:
                break
        else:
            break
    return configs

# get the Linode instance interface configuration of the nodes
def get_interfaces(node_id, config_id):
    """Fetch interfaces for a specific config ID with pagination."""
    endpoint = f"/linode/instances/{node_id}/configs/{config_id}/interfaces"
    interfaces = []
    params = {"page": 1, "page_size": 50}  # Start with page 1 and a reasonable page size
    while True:
        response = api_call(endpoint, params=params)
        if response and isinstance(response, list):
            interfaces.extend(response)
            # Check if there's another page (if applicable)
            if len(response) == params["page_size"]:
                params["page"] += 1
            else:
                break
        else:
            break
    return interfaces

# save the output result in csv format function
def save_to_csv(data, filename):
    """Save the data to a CSV file."""
    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        print(f"Data has been written to {filename}")

# Main Execution (skip the interfaces that are not for VLANs)
pools = get_pools(clusterID)
for pool in pools:
    pool_nodes = get_pool_nodes(pool)
    for node in pool_nodes:
        node_id = node["instance_id"]  # Extract the correct node ID
        label = node["id"]
        configs = get_configs(node_id)
        for config in configs:
            interfaces = get_interfaces(node_id, config["id"])
            for interface in interfaces:
                if interface.get("purpose") == "vlan":
                    outputTable.append({
                        "Cluster": clusterID,
                        "Node pool": pool["id"],
                        "Worker node ID": node_id,
                        "Worker Node Label": "lke" + str(clusterID) + "-" + str(label),
                        "Interface Configuration ID": interface["id"],
                        "VLAN ipam_address": interface.get("ipam_address"),
                    })

# Print Output Table
for row in outputTable:
     print(row)

# Save Output Table to CSV
if outputTable:
    save_to_csv(outputTable, "vlan_ip_addresses.csv")
else:
    print("No data found.")
