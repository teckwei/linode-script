# LKE Worker VLAN Auto-Attacher

This Python script automates the process of attaching a VLAN interface (`eth1`) with static IP assignment to **Linode Kubernetes Engine (LKE)** worker nodes.

## 🔍 Features

- Filters only LKE worker nodes by checking for the `lke.linode.com/pool-id` label.
- Matches Kubernetes nodes with Linode instances using the instance `label`.
- Skips nodes that already have the VLAN configured.
- Assigns a unique static IP address from a specified VLAN subnet (IPAM).
- Updates the Linode config with VLAN attachment using the Linode API.
- Automatically reboots the Linode to apply the network changes.

## ✅ Requirements

- Python 3.7+
- `kubectl` installed and accessible in PATH
- A valid kubeconfig pointing to your LKE cluster
- A Linode API Token with full access to Linodes and VLANs

## ⚙️ Configuration

Update these variables in the script:

```python
KUBECONFIG = "/path/to/your/kubeconfig.yaml"
LINODE_API_TOKEN = "your_linode_api_token"
TARGET_VLAN_ID = "vlan-xxxxx"
VLAN_CIDR = "192.168.100.0/24"
VLAN_GATEWAY = "192.168.100.1"
```

## 🧱 Script Workflow

**Step 1: Load Kubernetes Nodes**  
Uses `kubectl` to retrieve all nodes from the cluster.  
Parses each node's metadata and labels.

**Step 2: Filter by LKE Pool Membership**  
Only nodes with the `lke.linode.com/pool-id` label are processed.  
This ensures only LKE worker nodes are targeted.

**Step 3: Fetch Linode Instances**  
Queries the Linode API to get all Linode instances.  
Matches Kubernetes node names with Linode instance labels.

**Step 4: Check VLAN Configuration**  
For each matched Linode instance, retrieves its configs.  
Skips any configs that already have the target VLAN attached on `eth1`.

**Step 5: Detect Used IPs**  
Gathers all IPs already assigned to the VLAN across instances.  
Uses IPAM logic to determine the next available IP in the subnet (excluding gateway).

**Step 6: Update Linode Config**  
Adds or updates the `eth1` interface in the Linode config.  
Attaches the specified VLAN and assigns the selected IP.  
Sends a PUT request to the Linode config endpoint to apply changes.

**Step 7: Reboot the Instance**  
Reboots the Linode instance using the Linode API.  
Ensures the new VLAN settings are applied and active.

## 🛡️ Safety & Idempotency

- Nodes already configured with the VLAN are skipped.
- Avoids duplicate IP assignments within the configured subnet.
- Only modifies `eth1` and leaves existing interfaces (e.g., `eth0`) untouched.

