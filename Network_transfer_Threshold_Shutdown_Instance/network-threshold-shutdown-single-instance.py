import requests

# Your Linode API token
API_TOKEN = ""

# Your Linode ID
LINODE_ID = ""

# API endpoints
BASE_URL = "https://api.linode.com/v4"
#retrieve linode instance detail
LINODE_URL = f"{BASE_URL}/linode/instances/{LINODE_ID}" 
#retrieve linode instance network transfer detail
LINODE_Network_TRANSFER_URL = f"{BASE_URL}/linode/instances/{LINODE_ID}/transfer" 

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

def get_instance_details():
    response = requests.get(LINODE_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def get_instance_network_usage():
    response = requests.get(LINODE_Network_TRANSFER_URL, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    # Check the actual response structure
    #print("Instance data:", data)

    network_quota = data['quota']
    #convert from bytes to gigabytes (binary)
    network_used = data['used'] / (1024**3)

    #print(network_used, network_quota)
    
    return network_quota, network_used

def shutdown_linode():
    shutdown_url = f"{LINODE_URL}]/shutdown"
    response = requests.post(shutdown_url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    try:
        data = get_instance_details()
        
        # Check the actual response structure
        #print("Instance data:", data)

        # Check if the instance is offline
        if data['status'] == 'offline':
            print("Instance is already offline. No action needed.")
            return
        
        #retrieve network_quota, network_used from get_instance_network_usage() funtion
        network_quota, network_used = get_instance_network_usage()
        total_usage = network_used
        print(f"Current usage: {total_usage} Gigabytes. Quota limit: {network_quota} Gigabytes.")

        # Calculate the percentage of quota used
        usage_percentage = (total_usage / network_quota) * 100
        print(f"Current usage is {usage_percentage:.2f}% of the quota.")

        if total_usage >= network_quota:  # Convert GB to bytes
            print("Network quota reached, shutting down Linode.")
            shutdown_response = shutdown_linode()
            print("Shutdown initiated:", shutdown_response)
        else:
            print("Usage below quota limit, no action needed.")
    except KeyError as e:
        print(f"Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")

if __name__ == "__main__":
    main()