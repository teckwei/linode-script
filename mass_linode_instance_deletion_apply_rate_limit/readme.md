
# Mass deploy Linode instances while considering the API rate limit for instance creation.

## Problem Statement
1. The process of mass deletion Linode instances may be hindered by the API rate limit for instance creation, which allows for only a limited number of instances to be delete within a specific timeframe.
2. Customers are seeking to perform mass delete deployments through the API/CLI instead of using the Linode Cloud Manager.
3. Customers are looking on customize the filtering on the deletion for instances to ensure relative instance will be removed based on region, tags, status, and label filtering which include pagination since linode API default page_size is 100 which require pagination logic applied to flip to next pages.

## Objective
1. To automate the mass deletion deployment of Linode instances using the Linode API, taking into account the API rate limit.
2. To minimize manual effort in deleting a large number of Linode instances, streamlining the deployment process.

## Prerequisites 
1. jq command

## Step to reproduce: 
1.	Install all the dependencies mentioned above.
2.	Modify the API token and other information from the script based on your need.
3.	chmod +x “filename.sh” command to specifically sets the execute permission on a file, allowing it to be run as a program.
4.	./filename.sh to execute your script, you may see the attachment detail how the script will be ran.

## Reference script code:
https://github.com/teckwei/linode-script/blob/main/mass_linode_instance_deletion_apply_rate_limit/delete_instance_tw.sh

