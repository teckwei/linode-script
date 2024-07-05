import requests
import time
import json

# Linode API Token
LINODE_API_TOKEN = ''

# Linode API Endpoint for Listing Linodes
API_ENDPOINT = 'https://api.linode.com/v4/linode/instances'

# Predefined CPU alert value
CPU_ALERT_VALUE=0  # Set your desired CPU alert threshold value here
NETWORK_IN_VALUE=0 # Set your desired network in alert threshold value here
NETWORK_OUT_VALUE=0 # Set your desired network out alert threshold value here
TRANSFER_QUOTA_VALUE=0 # Set your desired transfer quota alert threshold value here
ALERT_IO_VALUE=0 # Set your desired IOPS alert threshold value here

def fetch_linode_ids():
    """Fetch Linode instances with pagination and filter by alert settings."""
    page = 1
    total_pages = 1
    linode_ids = []

    while page <= total_pages:
        response = requests.get(
            f'{API_ENDPOINT}?page={page}&page_size=100',
            headers={
                'Authorization': f'Bearer {LINODE_API_TOKEN}',
                'Content-Type': 'application/json'
            }
        )

        # Check for errors in the API response
        if response.status_code != 200:
            print(f"Error: Unable to fetch Linode IDs. Response: {response.text}")
            exit(1)

        data = response.json()
        total_pages = data['pages']

        # Extract Linode IDs from the response and filter by alert settings
        for linode in data['data']:
            alerts = linode['alerts']
            if (alerts['cpu'] != CPU_ALERT_VALUE or alerts['network_in'] != NETWORK_IN_VALUE or
                alerts['network_out'] != NETWORK_OUT_VALUE or alerts['transfer_quota'] != TRANSFER_QUOTA_VALUE or
                alerts['io'] != ALERT_IO_VALUE):
                linode_ids.append(linode['id'])

        page += 1

    return linode_ids

def rate_limit(request_count, start_time):
    """Handle rate limiting."""
    current_time = time.time()
    elapsed_time = current_time - start_time

    if request_count >= 800:
        if elapsed_time < 120:
            sleep_time = 120 - elapsed_time
            print(f"Rate limit reached. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)
        request_count = 0
        start_time = time.time()

    return request_count, start_time

def update_alert_threshold(linode_id):
    """Update the alert threshold for a Linode ID."""
    response = requests.put(
        f'{API_ENDPOINT}/{linode_id}',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LINODE_API_TOKEN}'
        },
        data=json.dumps({
            'alerts': {
                'cpu': CPU_ALERT_VALUE,
                'network_in': NETWORK_IN_VALUE,
                'network_out': NETWORK_OUT_VALUE,
                'transfer_quota': TRANSFER_QUOTA_VALUE,
                'io': ALERT_IO_VALUE
            }
        })
    )

    if response.status_code != 200:
        print(f"Error updating alert threshold for Linode ID {linode_id}: {response.status_code} - {response.text}")
    else:
        print(f"Successfully updated alert threshold for Linode ID: {linode_id}")

def main():
    linode_id_array = fetch_linode_ids()

    # Print the list of Linode IDs
    if linode_id_array == []:
        print("All alert threshold values for existing deployed instances based on predefined settings scripts.")
    else:
        print("List of Linode IDs:")
        print(linode_id_array)

    # Initialize the request counter and start time
    request_count = 0
    start_time = time.time()

    # Loop through the Linode IDs and update the alert threshold
    for linode_id in linode_id_array:
        print(f"Updating alert threshold for Linode ID: {linode_id}")

        # Rate limiting
        request_count, start_time = rate_limit(request_count, start_time)

        # Make the API Request to Update Alert Threshold
        update_alert_threshold(linode_id)

        # Increment the request counter
        request_count += 1

    print("Script Execute Complete")

if __name__ == "__main__":
    main()
