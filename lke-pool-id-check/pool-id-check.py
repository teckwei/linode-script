import subprocess
import json

# CONFIG
KUBECONFIG = "" #kubeconfig path

def get_all_nodes():
    cmd = [
        "kubectl", "--kubeconfig", KUBECONFIG,
        "get", "nodes", "-o", "json"
    ]
    try:
        output = subprocess.check_output(cmd, text=True)
        return json.loads(output).get("items", [])
    except subprocess.CalledProcessError as e:
        print("Error fetching nodes list:", e)
        return []

def check_lke_label_on_nodes(nodes):
    for node in nodes:
        name = node.get("metadata", {}).get("name", "unknown")
        labels = node.get("metadata", {}).get("labels", {})
        pool_id = labels.get("lke.linode.com/pool-id")

        if pool_id:
            print(f"✅ Node: {name} | LKE pool ID: {pool_id}")
        else:
            print(f"❌ Node: {name} | LKE pool ID label not found")

def main():
    nodes = get_all_nodes()
    if not nodes:
        print("❌ No nodes found.")
        return
    check_lke_label_on_nodes(nodes)

if __name__ == "__main__":
    main()
