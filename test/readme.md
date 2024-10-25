# Leveraging Harbor Replication rules feature (Pull Method) to Import Container Images from External Container Registries


## Problem statement:
Organizations often utilize multiple container registries across different environments and cloud platforms. This can lead to fragmented image management and difficulties in maintaining consistent versions of container images across different platforms. For instance, images stored in a cloud provider's container registry might need to be used in an on-premise environment or other cloud environments for deployment. Maintaining a consistent set of images across multiple platforms manually can become time-consuming and error-prone.

## Objective:
To automate the synchronization of container images across registries, Harbor's Replication feature can be used. The objective is to configure Harbor to pull container images from an external container registry into the Harbor registry automatically. This process will help streamline image management by ensuring the latest versions are consistently available in the Harbor repository, reducing manual effort and the risk of discrepancies between registries.

## Container Registry for harbor replication rules that supported: (Based on Harbor version 2.9)
* Docker registry
* Docker Hub
* AWS Elastic Container Registry
* Azure Container Registry
* Ali Cloud Container Registry
* Google Container Registry (and Google Cloud Artifact Registry)
* Huawei SWR
* Gitlab
* Quay
* Jfrog Artifactory

## Prerequisites:
* Set Up Harbor container registry on Akamai Linode on the region that close to your deployment
* Make sure the have the external container registry ready
* Make sure the registry endpoint credential created on Harbor for the external container registry to be connected.

## Steps to Implement Harbor Replication Rules
1. Set Up Harbor and External Registry
    * Ensure that Harbor is up and running in your environment.
    * Identify the source container registry from which you want to replicate images, such as Docker Hub, Google Container Registry (GCR), or any other supported registry.
2. Login to Harbor UI
    * Open a web browser and log in to the Harbor user interface with admin credentials.
3. Create a Target Registry in Harbor
    * Navigate to Administration > Registries.
    * Click on + New Endpoint to create a new endpoint for the external registry.
    * Enter the necessary details for the external container registry:
        * Name: A descriptive name for the target registry.
        * Endpoint URL: The URL of the external registry.
        * Access ID & Secret: Authentication credentials if required (username/password or API tokens).
    * Test the connection to ensure the Harbor instance can access the external registry successfully.
    * Click Save.
4. Create a Replication Rule
    * Go to Administration > Replication.
    * Click + New Replication Rule to define a new rule for pulling images.
    * Choose the Type as Pull-based replication. (remark: There are pull and push method)
    * Select the source registry from which you will be pulling images.
    * Configure the replication settings:
        * Projects: Select the Harbor project into which the images will be pulled.
        * Repository Filters: Optionally, add filters to restrict which repositories or tags should be pulled.
        * Trigger Mode: Choose between manual or scheduled replication. If choosing scheduled, configure the frequency (e.g., daily, weekly).
    * Enable Override Existing Image if you want to replace images with the same tag.
    * Click Save to create the replication rule.
5. Trigger the Replication
    * If the trigger mode is set to Manual, initiate the replication by going to the Replication tab, selecting the rule, and clicking Start.
    * If scheduled, Harbor will automatically pull the images at the defined intervals. (Eg. 0 */1 * * * * which is scheduled every hours at 0 minutes)
6. Monitor Replication Process
    * Navigate to Administration > Replication to monitor the progress and status of the replication.
    * Confirm that the images have been successfully pulled from the source registry and are available in the Harbor repository.
7. Use the Replicated Images
    * Once replication is complete, the images will be available in your Harbor registry.
    * Deploy these images as needed, ensuring you are pulling from Harbor for your deployments.
