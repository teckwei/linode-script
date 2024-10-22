#!/bin/bash

# Set your Linode API access token
ACCESS_TOKEN=""
SEARCH_STRING="backend"
INSTANCE_TYPE="" # Leave empty to skip instance_type filter
STATUS="running" # Leave empty to skip status filter
REGION="ap-south"  # Leave empty to skip region filter
TAGS=() # Leave empty to skip tags filter

# Initialize variables
page=1
instances_to_delete=()

# Loop through all pages to get instances
while : ; do
    echo "Fetching page $page..."

    # Get instances from the current page, attempting to get up to 500 instances (page size min=25, max=500)
    response=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linode.com/v4/linode/instances?page=$page&page_size=100")

    # Check if the API response is valid
    if [ -z "$response" ] || [ "$response" == "null" ]; then
        echo "Failed to retrieve API response or response is empty."
        break
    fi

    # Print the entire API response for debugging
    #echo "Response: $response"

    # Retrieve instance data and handle possible empty data
    # Create the jq filter dynamically based on provided filters
    jq_filter='.data[]? | select((.label | contains($search))'

    # Add additional filters if variables are not empty
    if [ -n "$INSTANCE_TYPE" ]; then
        jq_filter+=" and (.type == \"$INSTANCE_TYPE\")"
    fi
    if [ -n "$STATUS" ]; then
        jq_filter+=" and (.status == \"$STATUS\")"
    fi
    if [ -n "$REGION" ]; then
        jq_filter+=" and (.region == \"$REGION\")"
    fi

    # Add multiple tag filtering
    if [ ${#TAGS[@]} -gt 0 ]; then
        for tag in "${TAGS[@]}"; do
            jq_filter+=" and (.tags[] | contains(\"$tag\"))"
        done
    fi

    # Close the jq filter expression
    jq_filter+=') | .id'

    # Print the jq filter for debugging purposes (optional)
    # echo "jq_filter: $jq_filter"

    # Retrieve instances using the dynamically constructed jq filter
    instances=$(echo "$response" | jq -r --arg search "$SEARCH_STRING" "$jq_filter")
    
    # Check if there are instances matching the criteria on the current page
    if [ -z "$instances" ]; then
        echo "Page $page does not have any matching Linode instances."
    else
        # If there are matching instances, add them to the deletion list
        for instance_id in $instances; do
            instances_to_delete+=("$instance_id")
        done
    fi

    # Check total number of pages
    pages=$(echo "$response" | jq -r '.pages // empty')

    # If pages is null or empty, break the loop
    if [ -z "$pages" ]; then
        echo "Unable to determine the total number of pages, stopping pagination."
        break
    fi

    # Print debugging information
    echo "Total pages: $pages"

    # Check if all pages have been processed
    if [ "$page" -ge "$pages" ]; then
        echo "All pages have been processed."
        break
    fi

    # Go to the next page
    ((page++))
done


# Check if there are any instances that match the criteria to be deleted
if [ ${#instances_to_delete[@]} -eq 0 ]; then
    echo "No Linode instances found containing '$SEARCH_STRING'."
    exit 0
fi

# List all instances to be deleted
echo "The following Linode instances will be deleted:"
for instance in "${instances_to_delete[@]}"; do
    echo "$instance"
done

# Wait for user confirmation
read -p "Are you sure you want to continue deleting these instances? (Y/N): " confirmation
if [[ "$confirmation" != "Y" && "$confirmation" != "y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

# If the user confirms, proceed with deletion
for instance_id in "${instances_to_delete[@]}"; do
    echo "Deleting Linode instance with ID $instance_id..."

    # Delete the instance and capture the HTTP status code
    http_status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "Authorization: Bearer $ACCESS_TOKEN" "https://api.linode.com/v4/linode/instances/$instance_id")

    # Check the HTTP status code
    if [ "$http_status" -eq 200 ]; then
        echo "Linode instance with ID $instance_id was successfully deleted."
    else
        echo "Error deleting instance with ID $instance_id, HTTP status code: $http_status"
    fi
    
    # Add a delay to avoid triggering rate limits
    sleep 3
done

echo "All selected Linode instances have been deleted."
