import requests
import datetime

LINODE_API_TOKEN = ""  # Include your own API token
VOLUME_ID = ""  # Input your volume ID (e.g., linode-cli volumes list)
DATE_TIME = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# Volume group to be chosen
volume_group_label = "backup"  # Input unique label for your respective backup

def linode_cli():
    url = f"https://api.linode.com/v4/volumes/{VOLUME_ID}/clone"
    headers = {
        "Authorization": f"Bearer {LINODE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "label": f"{volume_group_label}-{DATE_TIME}"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

response_2 = linode_cli()
print(response_2)

url = "https://api.linode.com/v4/volumes"
headers = {
    "Authorization": f"Bearer {LINODE_API_TOKEN}"
}
response = requests.get(url, headers=headers)
volumes_data = response.json()

# List to store the latest items
latest_items = []

# List to store the oldest items
oldest_items = []

for volume in volumes_data["data"]:
    if volume["linode_id"] is None and volume["label"].startswith(volume_group_label):
        latest_items.append(volume["id"])

        # Remove the oldest items if the list length exceeds 2
        if len(latest_items) > 2:
            oldest_item = latest_items.pop(0)
            oldest_items.append(oldest_item)

if len(oldest_items) == 0:
    print("Don't have any oldest volume")
else:
    # Delete Linode Oldest Volume
    for item in oldest_items:
        url = f"https://api.linode.com/v4/volumes/{item}"
        response = requests.delete(url, headers=headers)

        # Check if the volume deletion was successful
        if response.status_code == 204:
            print(f"Volume with ID {item} deleted successfully")
        else:
            print(f"Failed to delete volume with ID {item}")
