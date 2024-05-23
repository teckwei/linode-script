#!/bin/bash

admin_token="" #provide PTA with full access scopes
readonly_users="" #provide read-only usernames that need to be granted access

## Initialize
echo -e "Started at $(date)\n"

## Retrive grants
echo "Retrieving grants for the user $readonly_users..."
user_grants=$(curl -s -H "Authorization: Bearer $admin_token" https://api.linode.com/v4/account/users/$readonly_users/grants)

## Linodes
echo "Granting Linodes permissions..."
gap_linodes=$(jq '.linode[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_linodes_count=$(echo "$gap_linodes" | wc -l)

if [ -n "$gap_linodes" ]; then
    payload_linode='{
        "linode": [
    '
    for id in $gap_linodes; do
        payload_linode+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_linode=${payload_linode%?}
    payload_linode+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_linode" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_linodes_count Linodes access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

## Firewalls
echo "Granting Firewall permissions..."
gap_firewalls=$(jq '.firewall[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_firewalls_count=$(echo "$gap_firewalls" | wc -l)

if [ -n "$gap_firewalls" ]; then
    payload_firewalls='{
        "firewall": [
    '
    for id in $gap_firewalls; do
        payload_firewalls+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_firewalls=${payload_firewalls%?}
    payload_firewalls+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_firewalls" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_firewalls_count firewalls access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

## Stackscripts
echo "Granting Stackscripts permissions..."
gap_stackscripts=$(jq '.stackscript[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_stackscripts_count=$(echo "$gap_stackscripts" | wc -l)

if [ -n "$gap_stackscripts" ]; then
    payload_stackscripts='{
        "stackscript": [
    '
    for id in $gap_stackscripts; do
        payload_stackscripts+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_stackscripts=${payload_stackscripts%?}
    payload_stackscripts+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_stackscripts" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_stackscripts_count Stackscripts access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

# Images
echo "Granting Images permissions..."
gap_images=$(jq '.image[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_images_count=$(echo "$gap_images" | wc -l)

if [ -n "$gap_images" ]; then
    payload_images='{
        "image": [
    '
    for id in $gap_images; do
        payload_images+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_images=${payload_images%?}
    payload_images+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_images" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_images_count images access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

# Volumes
echo "Granting Volumes permissions..."
gap_volumes=$(jq '.volume[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_volumes_count=$(echo "$gap_volumes" | wc -l)

if [ -n "$gap_volumes" ]; then
    payload_volumes='{
        "volume": [
    '
    for id in $gap_volumes; do
        payload_volumes+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_volumes=${payload_volumes%?}
    payload_volumes+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_volumes" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_volumes_count volumes access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

# Nodebalancers
echo "Granting Nodebalancers permissions..."
gap_nodebalancers=$(jq '.nodebalancer[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_nodebalancers_count=$(echo "$gap_nodebalancers" | wc -l)

if [ -n "$gap_nodebalancers" ]; then
    payload_nodebalancers='{
        "nodebalancer": [
    '
    for id in $gap_nodebalancers; do
        payload_nodebalancers+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_nodebalancers=${payload_nodebalancers%?}
    payload_nodebalancers+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_nodebalancers" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_nodebalancers_count nodebalancers access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

# Domains
echo "Granting Domains permissions..."
gap_domains=$(jq '.domain[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_domains_count=$(echo "$gap_domains" | wc -l)

if [ -n "$gap_domains" ]; then
    payload_domains='{
        "domain": [
    '
    for id in $gap_domains; do
        payload_domains+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_domains=${payload_domains%?}
    payload_domains+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_domains" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_domains_count domains access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

# VPCs
echo "Granting VPCs permissions..."
gap_vpcs=$(jq '.vpc[] | select(.permissions == null) | .id' <<< "$user_grants")
gap_vpcs_count=$(echo "$gap_vpcs" | wc -l)

if [ -n "$gap_vpcs" ]; then
    payload_vpcs='{
        "vpc": [
    '
    for id in $gap_vpcs; do
        payload_vpcs+='{
            "id": '$id',
            "permissions": "read_only"
        },'
    done
    payload_vpcs=${payload_vpcs%?}
    payload_vpcs+='
        ]
    }'
    curl -s -o /dev/null  -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -X PUT -d "$payload_vpcs" \
        https://api.linode.com/v4/account/users/$readonly_users/grants

    echo "$gap_vpcs_count vpcs access added successfully"
else
    echo "       No gap found. Grants are up to date"
fi

## End 
echo -e "\nCompleted at $(date)"


