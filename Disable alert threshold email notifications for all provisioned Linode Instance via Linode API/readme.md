# Disable alert threshold email notifications for all provisioned Linode Instance via Linode API
## Background on the alert threshold notification on each Linode instance:

When you create a new Linode instance by default, the alert threshold notifications for CPU, IOPS, and Network are set to predefined values. Modifying these values is only possible after the Linode instance has been provisioned.

## Problem Statement:

1. Continue to receive Linode alert threshold email notifications that clutter their email inboxes.

2. Exploring the option to globally disable these notifications, which is currently unavailable.

3. Currently, the only method to disable alert threshold email notifications for all Linode instances is to manually turn them off one by one in the Cloud Manager.

4. Alert threshold notification is spamming their email inbox.

## Objective:

1. Automate the utilization of the Linode API to disable alert threshold email notifications for all provisioned Linode instances, setting the threshold to zero/higher value.

2. Streamline the process of disabling email notifications for alert thresholds individually on Linode Cloud Manager instances, minimizing manual effort.

3. Using as alternative before turn off alert threshold notification feature for Linode instance introduced in the future

## Prerequisite
•	JQ command

## Step to reproduce:

1. Install all the dependencies mentioned above.

2. Nano command to save the script on the device that you using (I created a Nanode instance to perform the command) Script will be attached on the document.

3. Modify the API token and other information from the script based on your need.

4. chmod +x “filename.sh” command to specifically sets the execute permission on a file, allowing it to be run as a program.

5. ./filename.sh to execute your script, you may see the attachment detail how the script will be run.

## Reference:
https://techdocs.akamai.com/linode-api/reference/put-linode-instance