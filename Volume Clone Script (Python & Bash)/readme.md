# Clone and backup your Block Storage via Linode API scripting (Volume Clone)
## Problem Statement:

1. Linode Block Storage currently didn’t have backup feature.

2. Customer looking for alternative that can done via scripting (API/CLI) for Block storage backup (https://www.linode.com/docs/api/volumes/#volume-clone)

## Objective:

1. Automate and utilized the Linode API to perform volume clone and period time scheduling (keep latest two copy for the Linode block storage backup)

2. Reduce the manual work to clone the desired block storage

3. Using as alternative before backup feature for Linode Block Storage introduced in the future

## Prerequisite

1. jq command

## Step to reproduce:

1. Install all the dependencies mentioned above.

2. Nano command to save the script on the device that you using (I created a Nanode instance to perform the command) Script will be attached on the document.

3. Modify the API token and other information from the script based on your need.

4. chmod +x “filename.sh” command to specifically sets the execute permission on a file, allowing it to be run as a program.

5. crontab -e command to schedule the script to execute on the period that you preferred.

6. ./filename.sh to execute your script, you may see the attachment detail how the script will be ran.

## Remark:

1. Do take in mind that this will incur additional cost on block storage depend on the block storage size that you cloned.

## Reference:
1. https://crontab.guru/ - The quick and simple editor for cron schedule expressions
2. https://www.linode.com/docs/api/volumes/#volume-clone - Linode Block Storage (Volume Clone - API)