#!/bin/bash

LINODE_API_TOKEN= #include your own API token
VOLUME_ID=  # Input your volume ID (eg: linode-cli volumes list)
DATE_TIME="`date +%Y%m%d%H%M%S`";

#volume group to be choose
volume_group_label="backup" #input unique label for your respective backup

linode_cli() {
    curl -H "Authorization: Bearer $LINODE_API_TOKEN" -X POST -H "Content-Type: application/json" \
        -d "{\"label\": \"$volume_group_label-$DATE_TIME\"}" \
        "https://api.linode.com/v4/volumes/$VOLUME_ID/clone"
}

response_2=$(linode_cli)

echo $response_2

response=$(curl -H "Authorization: Bearer $LINODE_API_TOKEN" "https://api.linode.com/v4/volumes")

# Array to store the latest items
latest_items=()

# Array to store the oldest items
oldest_item=()

# Iterate over the JSON array using a process substitution for the while loop
while IFS= read -r item; do
  decoded=$(echo "$item" | base64 --decode)
  id=$(echo "$decoded" | jq -r '.id')
  label=$(echo "$decoded" | jq -r '.label')

  # Add the item to the latest_items array
  latest_items+=($id)

  # Remove the oldest items if the array length exceeds 2
  if [ "${#latest_items[@]}" -gt 2 ]; then
    oldest_item=${latest_items[0]}
    oldest_items+=("$oldest_item")
    unset 'latest_items[0]'
    latest_items=("${latest_items[@]}")
  fi

done < <(echo "$response" | jq -r --arg volume_label "$volume_group_label" '.data[] | select(.linode_id == null) | select(.label | contains($volume_label)) | @base64')

if [ ${#oldest_items[@]} -eq 0 ]; then
  echo "Don't have any oldest volume"
else
  #Delete Linode Oldest Volume
  for item in "${oldest_items[@]}"; do
  delete_response=$(curl -H "Authorization: Bearer $LINODE_API_TOKEN" -X DELETE "https://api.linode.com/v4/volumes/$item")

  # Check if the volume deletion was successful
  if [ $? -eq 0 ]; then
    echo "Volume with ID $item deleted successfully"
  else
    echo "Failed to delete volume with ID $item"
  fi
  done
fi