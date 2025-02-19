import time
import os
import requests
import datetime
import asyncio
import ipaddress
import random

# Linode API Token and Configuration
api_token = os.environ.get("API_TOKEN")
vlan_id = os.environ.get("VLAN_ID")
cidr = os.environ.get("CIDR")

# API Base URL and Headers
base_url = 'https://api.linode.com/v4'
headers = {
    'Authorization': f'Bearer {api_token}',
}

MAX_RETRIES = 3
RETRY_INTERVAL = 5
IP_RETRY_LIMIT = 10  # Maximum attempts to find an unused IP

# Utility Functions
def current_time():
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def get_linode_status(linode_id):
    """
    Fetch the status of a specific Linode instance.
    """
    url = f'{base_url}/linode/instances/{linode_id}'
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get('status')
    except Exception as e:
        print(f'{current_time()} Failed to get status for Linode {linode_id}. Error: {e}')
        return None


def get_unused_ipv4(cidr, used_ips):
    """
    Generate a random unused IP from the given CIDR range.
    Exclude already used and attempted IPs.
    """
    import ipaddress
    import random

    network = ipaddress.ip_network(cidr, strict=True)
    all_ips = set(network.hosts())  # Use a set for faster exclusion
    used_ips_set = set(ipaddress.ip_address(ip) for ip in used_ips)  # Convert to IPAddress objects
    attempts = 0

    # Exclude used IPs
    available_ips = all_ips - used_ips_set

    if not available_ips:
        raise RuntimeError(f"{current_time()} No available IPs in the CIDR range after excluding used IPs.")

    while attempts < IP_RETRY_LIMIT:
        random_ip = random.choice(list(available_ips))  # Choose a random IP
        available_ips.remove(random_ip)  # Remove it from the pool to avoid reselecting
        print(f'{current_time()} Attempt {attempts + 1}: Testing IP {random_ip}.')

        if str(random_ip) not in used_ips:
            print(f'{current_time()} Found unused IP: {random_ip}.')
            return str(random_ip)

        attempts += 1
        print(f'{current_time()} Attempt {attempts}: IP {random_ip} is already in use.')

    raise RuntimeError(f'{current_time()} Unable to find an unused IP after {IP_RETRY_LIMIT} attempts.')

def ping_ip(ip):
    """
    Check if an IP address is reachable (up).
    """
    response = os.system(f"ping -c 1 {ip} > /dev/null")
    return response == 0

# API Helper Functions
def get_nodes(page_size=300):
    """
    Fetch all nodes (Linode instances) with labels starting with 'lke'.
    """
    try:
        response = requests.get(f'{base_url}/linode/instances', headers=headers, params={'page_size': page_size}, timeout=15)
        response.raise_for_status()
        nodes = [node for node in response.json()['data'] if node['label'].startswith('lke')]
        return nodes
    except Exception as e:
        print(f'{current_time()} Failed to fetch Linode instances. Error: {e}')
        return []

def get_configs(node_id):
    """
    Fetch configurations for a specific node.
    """
    try:
        response = requests.get(f'{base_url}/linode/instances/{node_id}/configs', headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        print(f'{current_time()} {node_id} Failed to fetch configs for Linode instance. Error: {e}')
        return []

def get_used_ipam_addresses():
    """
    Retrieve all used IPAM addresses from the configurations of all nodes.
    """
    used_ips = set()
    nodes = get_nodes()
    for node in nodes:
        configs = get_configs(node['id'])
        for config in configs:
            for interface in config.get('interfaces', []):
                if interface.get('purpose') == 'vlan' and 'ipam_address' in interface:
                    used_ips.add(interface['ipam_address'].split('/')[0])  # Only store the base IP
    return used_ips

def attach_vlan_if_needed(node_name, node_id, config_id, ipam_address, used_ips):
    """
    Attach VLAN to the node only if it's not already attached.
    """
    url = f'{base_url}/linode/instances/{node_id}/configs/{config_id}'
    config = {
        "interfaces": [
            {"purpose": "public"},
            {"purpose": "vlan", "label": vlan_id, "ipam_address": ipam_address},
        ]
    }

    try:
        response = requests.put(url, headers=headers, json=config, timeout=15)
        response.raise_for_status()
        print(f'{current_time()} {node_name} Successfully attached VLAN to Linode instance.')

        # ✅ Ensure used_ips is a set before adding
        if isinstance(used_ips, set):
            used_ips.add(ipam_address.split('/')[0])
        else:
            print(f"{current_time()} Warning: used_ips is not a set! Converting it now.")
            used_ips = set(used_ips)  # Convert list to set and then add the IP
            used_ips.add(ipam_address.split('/')[0])

    except Exception as e:
        print(f'{current_time()} {node_name} Failed to attach VLAN. Error: {e}')

def reboot_from_config(node_name, node_id):
    """
    Reboot a Linode instance.
    """
    url = f'{base_url}/linode/instances/{node_id}/reboot'
    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f'{current_time()} {node_name} Successfully rebooted Linode instance.')
            break
        except Exception as e:
            retry_count += 1
            print(f'{current_time()} {node_name} Failed to reboot instance (Attempt {retry_count}). Error: {e}')
            if retry_count < MAX_RETRIES:
                print(f'Retrying in {RETRY_INTERVAL} seconds...')
                time.sleep(RETRY_INTERVAL)
            else:
                print(f'{current_time()} {node_name} Maximum retry attempts reached.')


def get_remaining_ips(cidr, used_ips):
    """
    Calculate the number of remaining available IPs in the given CIDR block.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=True)

        # Total usable IPs (excluding network and broadcast)
        total_ips_count = network.num_addresses - 2  

        # Convert used IPs to a set of valid IP addresses
        used_ips_set = {ipaddress.ip_address(ip) for ip in used_ips if ip}

        # Remaining IPs count
        remaining_ips_count = total_ips_count - len(used_ips_set)

        print(f"{current_time()} CIDR: {cidr}, Total Usable IPs: {total_ips_count}, Used IPs: {len(used_ips_set)}, Remaining IPs: {remaining_ips_count}")
        return remaining_ips_count

    except ValueError as e:
        print(f"{current_time()} Error: Invalid CIDR '{cidr}' - {e}")
        return 0  # Return 0 if CIDR is invalid


# Main Logic
def do():
    try:
        used_ips = get_used_ipam_addresses()  # Fetch all used IPAM addresses
        print(f'{current_time()} Used IPs: {used_ips}')
        
        remaining_ips = get_remaining_ips(cidr, used_ips)  # Check remaining IPs
        
        print(f'{current_time()} Remaining available IPs in {cidr}: {remaining_ips}')
        
        nodes = get_nodes()
        print(f'{current_time()} Found {len(nodes)} node(s).')

        for node in nodes:
            node_id = node['id']
            node_name = node['label']
            configs = get_configs(node_id)
            status = get_linode_status(node_id)

            if configs and status == 'running':
                for config in configs:
                    if len(config.get('interfaces', [])) < 2:  # Less than 2 interfaces (public + VLAN)
                        if remaining_ips > 0:  # ✅ Prevent errors if no IPs are left
                            ipam_address = get_unused_ipv4(cidr, used_ips) + '/21'
                            attach_vlan_if_needed(node_name, node_id, config['id'], ipam_address, used_ips)
                            reboot_from_config(node_name, node_id)
                            remaining_ips -= 1  # ✅ Update remaining IP count
                        else:
                            print(f'{current_time()} No remaining IPs available in {cidr}. Skipping attachment.')
                    else:
                        print(f'{current_time()} {node_name} is already properly configured.')

    except Exception as e:
        print(f'{current_time()} Error in do(): {e}')


# Asynchronous Main Loop
async def main():
    while True:
        print(f'{current_time()} Starting check...')
        do()
        print(f'{current_time()} Check completed. No changes needed.')
        await asyncio.sleep(60)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
