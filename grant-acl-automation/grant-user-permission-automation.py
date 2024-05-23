import requests
import json

# Your Linode API token
api_token = ''

# Base URL for Linode API
base_url = 'https://api.linode.com/v4'

#Page size
page_size_number=500

# Headers for the request
headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

# retrieve all Linode service in your account
def get_resources(endpoint):
    all_data = []
    page = 1

    while True:
        #include page & page size query when have more data (default page_size=100, max page_size=500)
        response = requests.get(f'{base_url}{endpoint}?page={page}&page_size={page_size_number}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            all_data.extend(data['data'])
            if data['pages'] <= page:
                break
            page += 1
        else:
            print(f"Failed to retrieve resources from {endpoint}: {response.status_code} - {response.text}")
            break

    return all_data

# retrieve the image resource with vendor = None which created by the Linode user their own
def get_image_resource_with_vendor_none():
    endpoint = '/images'
    all_images = get_resources(endpoint)

    # Filter images with vendor None and id starting with 'private/'
    no_vendor_images = [image for image in all_images if image['vendor'] is None and image['id'].startswith('private/')]

    # Remove the "private/" prefix from image IDs
    for image in no_vendor_images:
        image['id'] = image['id'].replace('private/', '')

    return no_vendor_images

# retrieve the stackscript resource with mine = True which created by the Linode user their own
def get_stackscript_resource_with_mine():
    endpoint = '/linode/stackscripts'
    all_stackscripts = get_resources(endpoint)

    # Filter StackScripts that belong to the authenticated user
    mine_stackscripts = [stackscript for stackscript in all_stackscripts if stackscript['mine']]

    return mine_stackscripts

# core function to re-configure the user permission grant permission
def grant_read_access_to_user(username):
    get_image_resource = get_image_resource_with_vendor_none()
    #include the scenario when there is no image resource created in the account
    image_ids = []
    if get_image_resource:
        image_ids = [int(image['id']) for image in get_image_resource]

    get_stackscript_resource = get_stackscript_resource_with_mine() 
     #include the scenario when there is no stackscript resource created in the account      
    stackscript_ids = []
    if get_stackscript_resource:
        stackscript_ids = [int(stackscript['id']) for stackscript in get_stackscript_resource]

    #Base api url to retrieve each linode resource
    linodes = get_resources('/linode/instances')
    domains = get_resources('/domains')
    nodebalancers = get_resources('/nodebalancers')
    volumes = get_resources('/volumes')
    longviews = get_resources('/longview/clients')
    vpcs = get_resources('/vpcs')
    
    linode_grants = [{"id": item['id'], "permissions": "read_only"} for item in linodes]
    domain_grants = [{"id": item['id'], "permissions": "read_only"} for item in domains]
    nodebalancer_grants = [{"id": item['id'], "permissions": "read_only"} for item in nodebalancers]
    volume_grants = [{"id": item['id'], "permissions": "read_only"} for item in volumes]
    image_grants = [{"id": image_id, "permissions": "read_only" } for image_id in image_ids]
    stack_script_grants = [{"id": stackscript_id, "permissions": "read_only"} for stackscript_id in stackscript_ids]
    longview_grants = [{"id": item['id'], "permissions": "read_only"} for item in longviews]
    vpc_grants = [{"id": item['id'], "permissions": "read_only"} for item in vpcs]

    payload = {
        "global": {
            "add_linodes": True,
            "add_longview": True,
            "longview_subscription": True,
            "account_access": "read_only",
            "cancel_account": False,
            "add_nodebalancers": True,
            "add_volumes": True,
            "add_domains": True,
            "add_stackscripts": True,
            "add_images": True,
            "modify_domains": True,
            "add_backups": True,
            "add_databases": True
        },
        "linode": linode_grants,
        "domain": domain_grants,
        "nodebalancer": nodebalancer_grants,
        "volume": volume_grants,
        "image": image_grants,
        "stackscript": stack_script_grants,
        "longview": longview_grants,
        "vpc": vpc_grants
    }

    endpoint = f'/account/users/{username}/grants'
    response = requests.put(f'{base_url}{endpoint}', headers=headers, json=payload)
    
    if response.status_code == 200:
        print("Successfully granted read-only access to all services.")
    else:
        print(f"Failed to grant access: {response.status_code} - {response.text}")

#main function to call the grant_read_access_to_user() function
if __name__ == "__main__":
    username = ''  # Replace with the actual username
    grant_read_access_to_user(username)
