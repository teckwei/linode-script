import subprocess
import json
import os

# Set Kubernetes environment variables
os.environ["KUBECONFIG"] = "falco-kubeconfig.yaml"

def apply_taint_if_spec_taints_null(pool_id_matched, taint_value):
    try:
        # Run the shell command to get node information and capture its output
        command = "kubectl get nodes -o json"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        # Check if the command was successful (return code 0) and if there is any output
        if process.returncode == 0 and output:
            # Parse the JSON output
            nodes_info = json.loads(output.decode('utf-8'))
            
            # Check each node's spec.taints field and apply taint if it is null
            for node in nodes_info.get("items", []):
                pool_id = node.get("metadata", {}).get("labels").get("lke.linode.com/pool-id")
                if pool_id == pool_id_matched:
                    if node.get("spec", {}).get("taints") is None:
                        node_name = node.get("metadata", {}).get("name")
                        print(f"Applying taint to node: {node_name}")
                        # Run kubectl taint command here
                        subprocess.run(["kubectl", "taint", "nodes", node_name, taint_value])
                    else:
                        print(f"Node {node.get('metadata', {}).get('name')} already has taints.")
                else:
                   print(f"Selected Node Pool {node.get('metadata', {}).get('labels').get('lke.linode.com/pool-id')} not existed for taint.")       
        else:
            # Handle the case where the command did not return any output or encountered an error
            print("Error: Unable to fetch node information.")
            if error:
                print("Error message:", error.decode('utf-8'))
    except Exception as e:
        print("An error occurred:", str(e))

def apply_label_if_label_null(pool_id_matched, label_value):
    try:
        # Run the shell command to get node information and capture its output
        command = "kubectl get nodes -o json"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        # Check if the command was successful (return code 0) and if there is any output
        if process.returncode == 0 and output:
            # Parse the JSON output
            nodes_info = json.loads(output.decode('utf-8'))
            
            # Check each node's labels.node_group field and apply label if it is null
            for node in nodes_info.get("items", []):
                pool_id = node.get("metadata", {}).get("labels").get("lke.linode.com/pool-id")
                if pool_id == pool_id_matched:
                    if node.get("metadata", {}).get("labels").get("node_group") is None:
                        node_name = node.get("metadata", {}).get("name")
                        print(f"Applying label to node: {node_name}")
                        # Run kubectl taint command here
                        subprocess.run(["kubectl", "label", "nodes", node_name, label_value])
                    else:
                        print(f"Node {node.get('metadata', {}).get('name')} already has {node.get('metadata', {}).get('labels').get('node_group')} labels.")
                else:
                    print(f"Selected Node Pool {node.get('metadata', {}).get('labels').get('lke.linode.com/pool-id')} not existed for label.")
        else:
            # Handle the case where the command did not return any output or encountered an error
            print("Error: Unable to fetch node information.")
            if error:
                print("Error message:", error.decode('utf-8'))
    except Exception as e:
        print("An error occurred:", str(e))

# Call the function to apply taints to nodes where spec.taints is null
apply_taint_if_spec_taints_null("199804", "app=dsp:NoExecute")

# Call the function to apply labels to nodes where spec.labels.node_group is null
apply_label_if_label_null("207492","node_group=dsp_other")
