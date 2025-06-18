import subprocess
import json
import requests
import ipaddress

# CONFIG
KUBECONFIG = ""  # Path to kubeconfig file for Kubernetes cluster authentication
LINODE_API_TOKEN = ""  # Linode API token for accessing Linode resources
TARGET_VLAN_ID = ""  # VLAN label to attach to nodes (e.g., vlan-xxxxx)
VLAN_CIDR = ""  # VLAN subnet for IP assignment (e.g., 192.168.100.0/24)
VLAN_GATEWAY = ""  # Gateway IP for the VLAN subnet (e.g., 192.168.100.1)

LINODE_API_URL = "https://api.linode.com/v4"
HEADERS = {
    "Authorization": f"Bearer {LINODE_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_all_nodes():
    """
    Retrieves all Kubernetes nodes using kubectl.
    Returns a list of node objects from the cluster, or an empty list if an error occurs.
    """
    cmd = [
        "kubectl", "--kubeconfig", KUBECONFIG,
        "get", "nodes", "-o", "json"
    ]
    try:
        output = subprocess.check_output(cmd, text=True)
        return json.loads(output).get("items", [])
    except subprocess.CalledProcessError as e:
        print("Error fetching nodes:", e)
        return []

def get_all_linode_instances():
    """
    Fetches all Linode instances using the Linode API, handling pagination.
    Returns a list of Linode instance objects.
    """
    instances = []
    page = 1
    while True:
        resp = requests.get(f"{LINODE_API_URL}/linode/instances?page={page}", headers=HEADERS)
        if resp.status_code != 200:
            print(f"Failed to fetch Linode instances: {resp.text}")
            break
        data = resp.json()
        instances.extend(data["data"])
        if page >= data["pages"]:
            break
        page += 1
    return instances

def find_linode_by_node_name(node_name, instances):
    """
    Matches a Kubernetes node name to a Linode instance by its label.
    Args:
        node_name (str): Name of the Kubernetes node.
        instances (list): List of Linode instance objects.
    Returns:
        dict: Matching Linode instance, or None if no match is found.
    """
    for linode in instances:
        if linode.get("label") == node_name:
            return linode
    return None

def get_linode_configs(linode_id):
    """
    Retrieves all configuration profiles for a specific Linode instance.
    Args:
        linode_id (int): ID of the Linode instance.
    Returns:
        list: List of configuration profiles, or empty list if the request fails.
    """
    url = f"{LINODE_API_URL}/linode/instances/{linode_id}/configs"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ Failed to get configs for Linode {linode_id}: {resp.text}")
        return []
    return resp.json().get("data", [])

def has_vlan_already(config, vlan_label):
    """
    Checks if a Linode config already has the specified VLAN attached.
    Args:
        config (dict): Linode configuration profile.
        vlan_label (str): VLAN label to check for.
    Returns:
        bool: True if the VLAN is already attached, False otherwise.
    """
    for iface in config.get("interfaces", []):
        if iface.get("purpose") == "vlan" and iface.get("label") == vlan_label:
            return True
    return False

def get_used_vlan_ips(instances, vlan_label):
    """
    Collects all IP addresses already assigned to the specified VLAN across all instances.
    Args:
        instances (list): List of Linode instance objects.
        vlan_label (str): VLAN label to check for assigned IPs.
    Returns:
        set: Set of used IP addresses (strings).
    """
    used_ips = set()
    for instance in instances:
        linode_id = instance["id"]
        configs = get_linode_configs(linode_id)
        for config in configs:
            interfaces = config.get("interfaces", [])
            for iface in interfaces:
                if iface.get("purpose") == "vlan" and iface.get("label") == vlan_label:
                    ipam = iface.get("ipam_address")
                    if ipam:
                        used_ips.add(ipam.split("/")[0])
    return used_ips

def get_next_available_ip(vlan_cidr, used_ips):
    """
    Finds the next available IP address in the VLAN subnet, excluding the gateway.
    Args:
        vlan_cidr (str): CIDR notation for the VLAN subnet (e.g., 192.168.100.0/24).
        used_ips (set): Set of already used IP addresses.
    Returns:
        str: Next available IP address.
    Raises:
        RuntimeError: If no free IPs are available in the subnet.
    """
    net = ipaddress.ip_network(vlan_cidr)
    for ip in net.hosts():
        ip_str = str(ip)
        if ip_str == VLAN_GATEWAY:
            continue
        if ip_str not in used_ips:
            return ip_str
    raise RuntimeError("No free IPs available in VLAN pool")

def reboot_linode(linode_id):
    """
    Triggers a reboot for the specified Linode instance via the Linode API.
    Args:
        linode_id (int): ID of the Linode instance to reboot.
    """
    url = f"{LINODE_API_URL}/linode/instances/{linode_id}/reboot"
    resp = requests.post(url, headers=HEADERS)
    if resp.status_code == 200:
        print(f"🔁 Reboot triggered for Linode {linode_id}")
    else:
        print(f"❌ Failed to reboot Linode {linode_id}: {resp.text}")

def update_config_with_vlan_and_ipam(linode_id, config_id, config, used_ips):
    """
    Updates a Linode configuration to attach a VLAN with a unique IP address.
    Args:
        linode_id (int): ID of the Linode instance.
        config_id (int): ID of the configuration profile to update.
        config (dict): Current configuration profile.
        used_ips (set): Set of already used IP addresses in the VLAN.
    """
    interfaces = config.get("interfaces", [])

    while len(interfaces) < 2:
        interfaces.append({"purpose": "public"})

    ipam_ip = get_next_available_ip(VLAN_CIDR, used_ips)
    used_ips.add(ipam_ip)

    interfaces[1] = {
        "purpose": "vlan",
        "label": TARGET_VLAN_ID,
        "ipam_address": f"{ipam_ip}/24"
    }

    payload = {
        "interfaces": interfaces
    }

    url = f"{LINODE_API_URL}/linode/instances/{linode_id}/configs/{config_id}"
    resp = requests.put(url, headers=HEADERS, json={**config, **payload})
    if resp.status_code == 200:
        print(f"✅ VLAN {TARGET_VLAN_ID} + IP {ipam_ip}/24 assigned on eth1 (Config {config_id})")
        reboot_linode(linode_id)
    else:
        print(f"❌ Failed to update config {config_id} for Linode {linode_id}: {resp.text}")

def main():
    """
    Main function to orchestrate VLAN attachment for LKE worker nodes.
    Fetches nodes, matches them to Linode instances, checks for existing VLANs,
    assigns new IPs, updates configurations, and reboots instances as needed.
    """
    print("🔍 Fetching Kubernetes nodes...")
    nodes = get_all_nodes()
    if not nodes:
        print("No Kubernetes nodes found.")
        return

    print("🔍 Fetching Linode instances...")
    linode_instances = get_all_linode_instances()
    if not linode_instances:
        print("No Linode instances retrieved.")
        return

    used_ips = get_used_vlan_ips(linode_instances, TARGET_VLAN_ID)

    for node in nodes:
        name = node.get("metadata", {}).get("name", "")
        labels = node.get("metadata", {}).get("labels", {})
        pool_id = labels.get("lke.linode.com/pool-id")

        if not pool_id:
            print(f"⚠️  Node {name} is not part of an LKE pool. Skipping.")
            continue

        linode = find_linode_by_node_name(name, linode_instances)
        if not linode:
            print(f"❌ No Linode instance found for node {name}")
            continue

        linode_id = linode["id"]
        print(f"\n🔧 Checking node {name} (Linode ID: {linode_id})")

        configs = get_linode_configs(linode_id)
        if not configs:
            print(f"❌ No configs found for Linode {linode_id}")
            continue

        config = configs[0]  # use first config (assumed active)
        config_id = config["id"]

        if has_vlan_already(config, TARGET_VLAN_ID):
            print(f"✅ VLAN already configured for node {name}. Skipping.")
            continue

        update_config_with_vlan_and_ipam(linode_id, config_id, config, used_ips)

if __name__ == "__main__":
    main()