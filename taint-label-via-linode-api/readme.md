# Streamline Multiple Node Pools Updates: Taint and Label Management via Linode API

## Background
When creating or updating an LKE node pool, you can optionally add custom labels and taints to all nodes using the labels and taints parameters. Defining labels and taints on a per-pool basis through the Linode API has several benefits compared to managing them manually with kubectl, including:

Custom labels and taints automatically apply to new nodes when a pool is recycled or scaled up (either manually or through autoscaling).
LKE ensures that nodes have the desired taints in place before they become ready for pod scheduling. This prevents newly created nodes from attracting workloads that don't have the intended tolerations.

## Problem Statement:
Customers with existing worker nodes in a Linode Kubernetes Engine (LKE) cluster often need to update configurations such as taints and labels without altering the fundamental setup of their nodes. Manually applying these updates can be tedious and prone to errors, especially when managing multiple node pools. To streamline this process, there is a need for a script that automates the updating of taints and labels for existing worker nodes in an LKE cluster. This solution will enhance operational efficiency, ensure consistent application of configurations, and minimize the risk of human error.


## Objective
The objective of the script is to automate the process of updating multiple node pools in a Linode Kubernetes Engine cluster. Specifically, it aims to:
1. Update the instance type for each node pool.
2. Adjust the number of existing node in each pool.
3. Apply specific labels and taints to each node pool to facilitate application deployment strategies (e.g., production, staging, and development).

Remark: When updating or adding labels and taints to an existing node pool, it is not necessary to recycle it. This is because the values are updated live on the running nodes.

## Step to reproduce:

1. Nano command to save the script on the device that you using (I created a Nanode instance to perform the command) Script will be attached on the document.

2. Modify the API token and other information from the script based on your need.

3. chmod +x “filename.sh” command to specifically sets the execute permission on a file, allowing it to be run as a program.

4. ./filename.sh to execute your script, you may see the attachment detail how the script will be run.

5. Run the script once; the API will automatically add the taints and labels to new or recycled nodes in your node pools during scaling operations. If there are any changes to the taints and labels for a specific node pool, simply modify the values and rerun the script.

## Reference:
https://techdocs.akamai.com/cloud-computing/docs/deploy-and-manage-a-kubernetes-cluster-with-the-api#add-labels-and-taints-to-your-lke-node-pools
