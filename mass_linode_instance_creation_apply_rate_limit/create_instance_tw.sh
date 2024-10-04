#!/bin/bash

# API TOKEN
ACCESS_TOKEN=""

# Set value parameters
region="ap-south"  # region to deploy
image="linode/ubuntu22.04"  #linode image
label="IPTEST"  # label
root_pass="AkamaiLinode123!*"  #password
type="g6-nanode-1" # Linode Instance Plan Type

# Setup CSV file to store IP
output_file="linode_ips.csv"
echo "Linode ID,IP address" > "$output_file"

# create linode instance and record IPv4 address
create_linodes() {
    for ((i=1; i<=200; i++)); do
        echo "Creating Linode instance $i..."

        # Linode VM Creation 
        create_response=$(curl -s -H "Content-Type: application/json" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -X POST -d '{
                "label": "'"$label$i"'",
                "image": "'"$image"'",
                "type": "'"$type"'",
                "region": "'"$region"'",
                "root_pass": "'"$root_pass"'",
                "booted": true
            }' \
            "https://api.linode.com/v4/linode/instances")

        echo $create_response

        # Extract Linode instance ID and IP address from response
        instance_id=$(echo "$create_response" | jq -r '.id')
        instance_ip=$(echo "$create_response" | jq -r '.ipv4[0]')

        # Log instance ID and IP address to CSV file
        echo "$instance_id,$instance_ip" >> "$output_file"

        echo "Linode instance $i has been created，IP Address: $instance_ip"

        # Rate Limit condition
        if ! ((i % 10)); then
            echo "Wait to respect API rate limits..."
            sleep 30
        fi
    done
}

# Call the function to create Linodes and record their IP
create_linodes

echo "Linode instance creation and IP records stored are completed."