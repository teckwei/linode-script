import csv
import json
import subprocess

# Step 1: Get JSON output from linode-cli
def get_regions_data():
    result = subprocess.run(
        ["linode-cli", "regions", "list", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Error calling linode-cli: {result.stderr}")
    return json.loads(result.stdout)

# Step 2: Define ordered custom capability labels
CUSTOM_CAPABILITY_LABELS = {
    "Linodes": "Linodes (Shared, Dedicated, High Memory Plan)",
    "NETINT Quadra T1U": "Accelerated Plan (NETINT Quadra T1U)",
    "GPU Linodes": "GPU Linodes (RTX 6000/RTX 4000 Ada)",
    "Premium Plans": "Premium Plans",
    "Managed Databases": "Managed Databases (MYSQL & Postgresql)",
    "Kubernetes": "Kubernetes",
    "Kubernetes Enterprise": "Kubernetes Enterprise (LA)",
    "Backups": "Backups",
    "NodeBalancers": "NodeBalancers",
    "Block Storage": "Block Storage",
    "Block Storage Encryption": "Block Storage Encryption",
    "LA Disk Encryption": "LA Disk Encryption",
    "Object Storage": "Object Storage",
    "Cloud Firewall": "Cloud Firewall",
    "Vlans": "Vlans",
    "VPCs": "VPCs",
    "Metadata": "Metadata",
    "Placement Group": "Placement Group",
    "StackScripts": "StackScripts"
}

# Step 3: Create rows using fixed order of capabilities
def create_csv_rows(data):
    rows = []
    for region in data:
        row = {
            "id": region.get("id"),
            "label": region.get("label"),
            "country": region.get("country"),
            "status": region.get("status"),
        }
        region_caps = region.get("capabilities", [])
        for cap, custom_label in CUSTOM_CAPABILITY_LABELS.items():
            row[custom_label] = "Yes" if cap in region_caps else "No"
        rows.append(row)
    return rows

# Step 4: Save to CSV
def save_to_csv(rows, filename="linode_regions.csv"):
    fieldnames = ["id", "label", "country", "status"] + list(CUSTOM_CAPABILITY_LABELS.values())
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

# Run the script
if __name__ == "__main__":
    data = get_regions_data()
    rows = create_csv_rows(data)
    save_to_csv(rows)
    print("CSV export complete: linode_regions.csv")
