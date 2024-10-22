#!/bin/bash

# Replace with your actual Linode API token
TOKEN=""

# Define the LKE cluster ID (search the ID via LINODE CLI/API eg.CLI command: linode-cli lke clusters-list)
clusters_ID="249198"

# Define an array of node pool IDs you want to update
NODE_POOL_IDS=("397231" "397240" "397241")  # Add all the node pool IDs you want to update

# Define an array of labels for each node pool (matching the NODE_POOL_IDS array)
LABELS=(
    '{"myapp.io/app": "prod", "example": "foo1"}' # First node pool
    '{"myapp.io/app": "stage", "example": "foo2"}' # Second node pool
    '{"myapp.io/app": "dev", "example": "foo3"}' # Third node pool
)

# Define an array of taints for each node pool (matching the NODE_POOL_IDS array)
TAINTS=(
    '[{"key": "myapp.io/new", "value": "twtest1", "effect": "NoSchedule"}]' # First node pool
    '[{"key": "myapp.io/new", "value": "twtest2", "effect": "NoSchedule"}]' # Second node pool
    '[{"key": "myapp.io/new", "value": "twtest3", "effect": "NoSchedule"}]' # Third node pool
)

# Define an array for instance types for each node pool
TYPES=(
    "g6-standard-1" # Type for the first node pool
    "g6-standard-1" # Type for the second node pool
    "g6-standard-1" # Type for the third node pool
)

# Define an array for the number of nodes (count) for each node pool
COUNTS=(
    3  # Count for the first node pool existing worker node
    3  # Count for the second node pool existing worker node
    3  # Count for the third node pool existing worker node
)

# Iterate over each node pool and update it with customized labels and taints
for i in "${!NODE_POOL_IDS[@]}"; do
    NODE_POOL_ID="${NODE_POOL_IDS[$i]}"
    LABEL="${LABELS[$i]}"
    TAINT="${TAINTS[$i]}"
    TYPE="${TYPES[$i]}"
    COUNT="${COUNTS[$i]}"

    echo "Updating node pool ID: $NODE_POOL_ID with custom labels and taints"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -X PUT -d '{
        "type": "'"$TYPE"'",
        "count": '"$COUNT"',
        "taints": '"$TAINT"',
        "labels": '"$LABEL"'
    }' https://api.linode.com/v4/lke/clusters/$clusters_ID/pools/"$NODE_POOL_ID")

    if [ "$HTTP_CODE" -ne 200 ]; then
        echo "Failed to update Cluster $cluster_ID node pool $NODE_POOL_ID. HTTP Status: $HTTP_CODE"
    else
        echo "Cluster $cluster_ID Node pool $NODE_POOL_ID updated successfully."
    fi

done
