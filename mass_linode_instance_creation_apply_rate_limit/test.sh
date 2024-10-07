#!/bin/bash

# API TOKEN
ACCESS_TOKEN="c7daf497cac7964ebbacfe49b3417afdefa5f170568983ef84602f83bfa8febd"

# Set value parameters
region="ap-south"  # region to deploy
image="linode/ubuntu22.04"  # linode image
label="IPTEST"  # label
root_pass="AkamaiLinode123!*"  # password
type="g6-nanode-1" # Linode Instance Plan Type

# Setup CSV file to store IP
output_file="linode_ips.csv"
echo "Linode ID,IP address" > "$output_file"

LABEL_COUNTER=1  # Counter for labels

# Create Linode instance
create_instance() {
    create_response=$(curl -s -w "\n%{http_code}" -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -X POST -d '{
            "label": "'"IPTEST$LABEL_COUNTER"'",
            "image": "'"$image"'",
            "type": "'"$type"'",
            "region": "'"$region"'",
            "root_pass": "'"$root_pass"'",
            "booted": true
        }' \
        "https://api.linode.com/v4/linode/instances")

    # Split the response to get the body and HTTP status
    http_status=$(echo "$create_response" | tail -n1)
    response_body=$(echo "$create_response" | sed '$d')

    # Log the raw response for debugging
    echo "Raw Response for instance $LABEL_COUNTER: $create_response"

    if [[ "$http_status" == "200" ]]; then
        instance_id=$(echo "$response_body" | jq -r '.id')
        instance_ip=$(echo "$response_body" | jq -r '.ipv4[0]')

        if [[ -n "$instance_id" && -n "$instance_ip" ]]; then
            echo "$instance_id,$instance_ip" >> "$output_file"
            echo "Linode instance $LABEL_COUNTER has been created with IP Address: $instance_ip"
            LABEL_COUNTER=$((LABEL_COUNTER + 1))
        else
            echo "Error parsing Linode instance details for instance $LABEL_COUNTER."
        fi
    else
        echo "Error creating instance $LABEL_COUNTER: HTTP status $http_status."
        echo "Stopping instance creation process due to failure."
        exit 1  # Exit the script when a failure occurs
    fi
}

# Main loop to create Linode instances
for ((i=1; i<=100; i++)); do
    echo "Creating Linode instance $LABEL_COUNTER..."
    create_instance
    sleep 3  # Sleep between requests to avoid API rate limits

    # Implement rate-limiting logic
    if ((i % 5 == 0)); then
        echo "Waiting to respect 5 requests per 15 seconds rate limit..."
        sleep 15
    elif ((i % 10 == 0)); then
        echo "Waiting to respect 10 requests per 30 seconds rate limit..."
        sleep 30
    fi
done

echo "Linode instance creation process completed."

