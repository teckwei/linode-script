import requests
import json
import time
from datetime import datetime

# Configuration
API_TOKEN = ""  # Replace with your Linode API token
BASE_URL = f"https://api.linode.com/v4"
RATE_LIMIT_REQUESTS = 800  # Linode API rate limit: 800 requests per minute
RATE_LIMIT_PERIOD = 60  # Seconds in a minute
REQUEST_INTERVAL = RATE_LIMIT_PERIOD / RATE_LIMIT_REQUESTS  # Time between requests
PAGE_SIZE = 100  # Number of results per page, max supported by Linode API
LABEL_FILTER = ["auto-instance"]  # Hardcoded list of labels to filter (partial match, case-insensitive)

# Track request timestamps for rate limiting
request_timestamps = []
# Counter for configurations needing kernel change
kernel_change_count = 0
# Counter for scanned instances
instance_count = 0

def enforce_rate_limit():
    """Ensure API requests stay within rate limits."""
    current_time = time.time()
    # Remove timestamps older than RATE_LIMIT_PERIOD
    global request_timestamps
    request_timestamps = [t for t in request_timestamps if current_time - t < RATE_LIMIT_PERIOD]
    
    # If we've hit the rate limit, sleep until we can make another request
    if len(request_timestamps) >= RATE_LIMIT_REQUESTS:
        sleep_time = RATE_LIMIT_PERIOD - (current_time - request_timestamps[0])
        if sleep_time > 0:
            print(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
    
    # Record the new request timestamp
    request_timestamps.append(time.time())
    # Sleep briefly to pace requests
    time.sleep(REQUEST_INTERVAL)

def get_headers():
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

def get_linode_instances():
    """Fetch all Linode instances, handling pagination and displaying total pages."""
    instances = []
    page = 1
    total_pages = 1  # Default to 1 in case the first request fails
    
    while True:
        enforce_rate_limit()
        try:
            response = requests.get(
                f"{BASE_URL}/linode/instances?page={page}&page_size={PAGE_SIZE}",
                headers=get_headers()
            )
            response.raise_for_status()
            data = response.json()
            instances.extend(data.get('data', []))
            
            # Capture total pages from the first request
            if page == 1:
                total_pages = data.get('pages', 1)
                print(f"Total pages to paginate for instances: {total_pages}")
            
            # Check if there are more pages
            if page >= total_pages or not data.get('data'):
                break
            page += 1
        except requests.RequestException as e:
            print(f"Error fetching instances (page {page}): {e}")
            break
    
    return instances

def get_linode_configs(linode_id):
    """Fetch configurations for a specific Linode instance."""
    enforce_rate_limit()
    try:
        response = requests.get(
            f"{BASE_URL}/linode/instances/{linode_id}/configs?page_size={PAGE_SIZE}",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.RequestException as e:
        print(f"Error fetching configs for Linode {linode_id}: {e}")
        return []

def update_linode_kernel(linode_id, config_id, kernel_id="linode/grub2"):
    """Update the kernel of a specific configuration to GRUB."""
    enforce_rate_limit()
    try:
        payload = {"kernel": kernel_id}
        response = requests.put(
            f"{BASE_URL}/linode/instances/{linode_id}/configs/{config_id}",
            headers=get_headers(),
            data=json.dumps(payload)
        )
        response.raise_for_status()
        print(f"Updated kernel to GRUB for Linode {linode_id}, config {config_id}")
        return True
    except requests.RequestException as e:
        print(f"Error updating kernel for Linode {linode_id}, config {config_id}: {e}")
        return False

def reboot_linode(linode_id):
    """Reboot a Linode instance."""
    enforce_rate_limit()
    try:
        response = requests.post(
            f"{BASE_URL}/linode/instances/{linode_id}/reboot",
            headers=get_headers()
        )
        response.raise_for_status()
        print(f"Initiated reboot for Linode {linode_id}")
        return True
    except requests.RequestException as e:
        print(f"Error rebooting Linode {linode_id}: {e}")
        return False

def count_non_grub_configs():
    """Count configurations with non-GRUB kernels across filtered Linodes."""
    global kernel_change_count, instance_count
    linodes = get_linode_instances()
    if not linodes:
        print("No Linode instances found or error occurred.")
        return []

    non_grub_configs = []
    for linode in linodes:
        linode_id = linode['id']
        label = linode['label']
        
        # Apply label filter if LABEL_FILTER is not empty
        if LABEL_FILTER and not any(filter_label.lower() in label.lower() for filter_label in LABEL_FILTER):
            print(f"Skipping Linode: {label} (ID: {linode_id}) - does not match label filter")
            continue
        
        instance_count += 1
        print(f"\nScanning Linode: {label} (ID: {linode_id})")
        
        configs = get_linode_configs(linode_id)
        if not configs:
            print(f"No configurations found for Linode {linode_id}")
            continue

        for config in configs:
            config_id = config['id']
            kernel = config.get('kernel', '')
            if kernel != 'linode/grub2':
                kernel_change_count += 1
                non_grub_configs.append((linode_id, config_id, label, kernel))
                print(f"Non-GRUB kernel ({kernel}) found in config {config_id} for Linode {linode_id}")
            else:
                print(f"Config {config_id} already using GRUB kernel")
    
    return non_grub_configs

def main():
    print(f"Starting kernel update process at {datetime.now()}")
    if LABEL_FILTER:
        print(f"Filtering instances by labels: {', '.join(LABEL_FILTER)}")
    else:
        print("No label filter applied, processing all instances")
    
    # First pass: Count and identify non-GRUB configurations
    print("\n=== Scanning for non-GRUB kernels ===")
    non_grub_configs = count_non_grub_configs()
    print(f"\nTotal Linode instances scanned: {instance_count}")
    print(f"Total configurations needing kernel change: {kernel_change_count}")
    
    if kernel_change_count == 0:
        print("No configurations need kernel updates.")
        print(f"\nProcess completed at {datetime.now()}")
        return

    # Second pass: Update and reboot
    print("\n=== Updating kernels and rebooting ===")
    for linode_id, config_id, label, kernel in non_grub_configs:
        print(f"\nProcessing Linode: {label} (ID: {linode_id})")
        print(f"Non-GRUB kernel ({kernel}) in config {config_id}")
        
        # Update kernel to GRUB
        if update_linode_kernel(linode_id, config_id):
            # Wait briefly to ensure configuration update is processed
            time.sleep(2)
            
            # Reboot the instance
            if reboot_linode(linode_id):
                print(f"Successfully updated and rebooted Linode {linode_id}")
            else:
                print(f"Failed to reboot Linode {linode_id}")
        else:
            print(f"Failed to update kernel for Linode {linode_id}")

    print(f"\nProcess completed at {datetime.now()}")

if __name__ == "__main__":
    main()