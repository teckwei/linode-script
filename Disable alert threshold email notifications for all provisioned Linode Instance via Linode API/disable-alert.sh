#!/bin/bash

# Linode API Token
LINODE_API_TOKEN=""

# Linode API Endpoint for Listing Linodes
API_ENDPOINT="https://api.linode.com/v4/linode/instances"

# Make the API Request to List Linodes
response=$(curl -H "Authorization: Bearer $LINODE_API_TOKEN" \
                -s "$API_ENDPOINT")

# Check for errors in the API response
if [[ "$response" =~ "errors" ]]; then
  echo "Error: Unable to fetch Linode IDs."
  echo "Response: $response"
  exit 1
fi


# Extract Linode IDs from the response and format them
linode_ids=$(echo "$response" | jq -r '.data[].id' | tr '\n' ' ' | sed 's/ *$//')

# Create an array to store Linode IDs
linode_id_array=()

# Loop through the Linode IDs and store them in the array
for id in $linode_ids; do
  linode_id_array+=($id)
done


# Print the list of Linode IDs
echo "List of Linode IDs:"
# Print the formatted list of Linode IDs
echo ${linode_id_array[@]}


# Loop through the Linode IDs and update the alert threshold
for LINODE_ID in "${linode_id_array[@]}"; do
  echo "Updating alert threshold for Linode ID: $LINODE_ID"

  # JSON Payload for Alert Threshold Update
  # (Your JSON payload for updating the alert threshold)

  # Make the API Request to Update Alert Threshold
  curl -H "Content-Type: application/json" \
       -H "Authorization: Bearer $LINODE_API_TOKEN" \
       -X PUT -d '{
            "alerts": {
                "cpu": 0,
                "network_in": 0,
                "network_out": 0,
                "transfer_quota": 0,
                "io": 0
            }
        }' \
       "$API_ENDPOINT/$LINODE_ID"
done

echo -e "Script Complete"



