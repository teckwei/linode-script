#!/bin/bash

# Linode API Token
LINODE_API_TOKEN=""

# Linode API Endpoint for Listing Linodes
API_ENDPOINT="https://api.linode.com/v4/linode/instances"

# Predefined CPU alert value
CPU_ALERT_VALUE=0  # Set your desired CPU alert threshold value here
NETWORK_IN=0 # Set your desired network in alert threshold value here
NETWORK_OUT=0 # Set your desired network out alert threshold value here
TRANSFER_QUOTA=0 # Set your desired transfer quota alert threshold value here
ALERT_IO=0 # Set your desired IOPS alert threshold value here

# Function to fetch Linode instances with pagination and filter by alert settings
fetch_linode_ids() {
  local page=1
  local total_pages=1
  local linode_ids=()

  while [ $page -le $total_pages ]; do
    response=$(curl -H "Authorization: Bearer $LINODE_API_TOKEN" \
                    -s "$API_ENDPOINT?page=$page")

    # Check for errors in the API response
    if [[ "$response" =~ "errors" ]]; then
      echo "Error: Unable to fetch Linode IDs."
      echo "Response: $response"
      exit 1
    fi

    # Extract total pages
    total_pages=$(echo "$response" | jq -r '.pages')

    # Extract Linode IDs from the response and filter by alert settings
    ids=$(echo "$response" | jq -r ".data[] | select(.alerts.cpu == $CPU_ALERT_VALUE and .alerts.network_in == $NETWORK_IN and .alerts.network_out == $NETWORK_OUT and .alerts.transfer_quota == $TRANSFER_QUOTA and .alerts.io == $ALERT_IO) | .id")
    linode_ids+=($ids)

    # Increment page
    page=$((page + 1))
  done

  echo "${linode_ids[@]}"
}

# Fetch all Linode IDs with specified alert settings
linode_id_array=($(fetch_linode_ids))

# Print the list of Linode IDs
echo "List of Linode IDs:"
echo ${linode_id_array[@]}

# Initialize the request counter and start time
request_count=0
start_time=$(date +%s)

# Function to handle rate limiting
rate_limit() {
  local current_time=$(date +%s)
  local elapsed_time=$((current_time - start_time))

  if [ $request_count -ge 800 ]; then
    if [ $elapsed_time -lt 120 ]; then
      sleep_time=$((120 - elapsed_time))
      echo "Rate limit reached. Sleeping for $sleep_time seconds."
      sleep $sleep_time
    fi
    request_count=0
    start_time=$(date +%s)
  fi
}

# Loop through the Linode IDs and update the alert threshold
for LINODE_ID in "${linode_id_array[@]}"; do
  echo "Updating alert threshold for Linode ID: $LINODE_ID"

  # Rate limiting
  rate_limit

  # Make the API Request to Update Alert Threshold
  curl -H "Content-Type: application/json" \
       -H "Authorization: Bearer $LINODE_API_TOKEN" \
       -X PUT -d "{
            \"alerts\": {
                \"cpu\": $CPU_ALERT_VALUE,
                \"network_in\": $NETWORK_IN,
                \"network_out\": $NETWORK_OUT,
                \"transfer_quota\": $TRANSFER_QUOTA,
                \"io\": $ALERT_IO
            }
        }" \
       "$API_ENDPOINT/$LINODE_ID"

  # Increment the request counter
  request_count=$((request_count + 1))
done

echo -e "Script Complete"
