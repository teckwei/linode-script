#!/bin/bash

# Set your Linode API access token
ACCESS_TOKEN=your_linode_api_token

# Set deployment parameters
region="ap-south"  # Replace with your desired region
image="linode/ubuntu22.04"  # Replace with your desired Ubuntu image
label="ProjectTestCode"  # Replace with your desired label
root_pass="YourRootPassword,./"  # Replace with your desired root password
type="g6-dedicated-2" # Replace with your desired instance type
desired_cpu_version="EPYC 7713"  # Replace with your desired CPU version

# Provision 50 instances with desired CPU model
counter=1
while [[ $counter -lt 51 ]];
do
    echo "Provisioning instance $counter..."

    # Create the Linode instance
    create_instance_response=$(curl -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -X POST -d '{
            "label": "'"$label$counter"'",
            "image": "'"$image"'",
            "type": "'"$type"'",
            "region": "'"$region"'",
            "root_pass": "'"$root_pass"'",
            "booted": true
        }' \
        "https://api.linode.com/v4/linode/instances")

    # Extract the Linode instance ID from the response
    instance_id=$(echo "$create_instance_response" | jq -r '.id')

    # Wait for the Linode instance to be running
    while true; do
        instance_status_response=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linode.com/v4/linode/instances/$instance_id")
        instance_status=$(echo "$instance_status_response" | jq -r '.status')
        if [[ "$instance_status" == "running" ]]; then
            break
        fi
        sleep 150
    done

    # Get the Linode instance IP address
    instance_ip=$(echo "$instance_status_response" | jq -r '.ipv4[0]')

    # SSH into the Linode instance and check the CPU version
    cpu_version=$(sshpass -p "$root_pass" ssh -o StrictHostKeyChecking=no root@"$instance_ip" "lscpu | grep 'Model name:' | awk -F': ' '{print \$2}'")

    # Compare the CPU version
    if [[ "$cpu_version" == *"$desired_cpu_version"* ]]; then
        echo "Ubuntu server on Linode $instance_id has the desired CPU version: $desired_cpu_version"
	$counter+=$(counter+1)
    else
        echo "Ubuntu server on Linode $instance_id does not have the desired CPU version. Current CPU version: $cpu_version"
        
        # Delete the Linode instance
        delete_instance_response=$(curl -X DELETE \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            "https://api.linode.com/v4/linode/instances/$instance_id")
        echo "Linode $instance_id deleted."
    fi
done