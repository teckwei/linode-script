from datetime import datetime, timedelta
import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Scaling Configurations
MIN_VMS = int(os.getenv("MIN_VMS", 1))
MAX_VMS = int(os.getenv("MAX_VMS", 5))
COOLDOWN_PERIOD = int(os.getenv("COOLDOWN_PERIOD", 300))  # Default 5 minutes
RABBIT_MQ_TIME_INTERVAL_CHECK = int(os.getenv("RABBIT_MQ_TIME_INTERVAL_CHECK", 30)) # Default 30 seconds

# Linode & RabbitMQ API Config
LINODE_API_TOKEN = os.getenv("LINODE_API_TOKEN")
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

HEADERS = {"Authorization": f"Bearer {LINODE_API_TOKEN}", "Content-Type": "application/json"}
LINODE_API_URL = "https://api.linode.com/v4/linode/instances"

# Track idle VM cooldown
idle_vm_timers = {}

# Track recent VM creation times
vm_creation_timestamps = []

#Check Linode Provision status function
def check_vm_provision_status(vm_id):
    """Check the status of a Linode VM until it's 'running'."""
    status_url = f"{LINODE_API_URL}/{vm_id}"
    
    for _ in range(30):  # Check for up to 5 minutes (10s interval)
        response = requests.get(status_url, headers=HEADERS)
        if response.status_code == 200:
            status = response.json().get("status")
            if status == "running":
                print(f"✅ VM {vm_id} is now ready to use.")
                return True
            else:
                print(f"⏳ Waiting for VM {vm_id} to be ready... (Current status: {status})")
        else:
            print(f"⚠️ Error checking VM status: {response.text}")

        time.sleep(10)  # Wait 10 seconds before rechecking
    
    print(f"❌ VM {vm_id} did not become ready in time.")
    return False

#Check Instance status function
def check_vm_running_status(vm_id):
    """Check the status of a Linode VM."""
    status_url = f"{LINODE_API_URL}/{vm_id}"

    response = requests.get(status_url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("status")
    return None

#Fetch RabbitMQ Queue Length
def get_queue_length():
    """Fetch RabbitMQ queue length."""
    try:
        response = requests.get(RABBITMQ_URL, auth=(RABBITMQ_USER, RABBITMQ_PASS))
        response.raise_for_status()
        return response.json().get("messages", 0)
    except requests.RequestException:
        return -1

#fetch active instance created
def get_active_gpu_vm_count():
    """Fetch active Linode VMs with label starting with 'gpu-'."""
    try:
        response = requests.get(LINODE_API_URL, headers=HEADERS)
        response.raise_for_status()
        instances = response.json().get("data", [])
        return sum(1 for vm in instances if vm["label"].startswith("gpu-"))
    except requests.RequestException:
        return -1

#Function to setup VM with label GPU
def provision_vm():
    """Create a new Linode GPU VM with a label starting with 'gpu-'."""
    global vm_creation_timestamps  # Explicitly declare it as global
    current_vms = get_active_gpu_vm_count()
    
    # Clean up timestamps older than 30 seconds
    now = datetime.now()
    vm_creation_timestamps = [ts for ts in vm_creation_timestamps if now - ts < timedelta(seconds=30)]

    # Rate limit: max 10 requests per 30 seconds
    if len(vm_creation_timestamps) >= 10:
        wait_time = (30 - (now - vm_creation_timestamps[0]).seconds)
        print(f"Rate limit reached! Waiting {wait_time} seconds before next VM creation...")
        time.sleep(wait_time)

    if current_vms < MAX_VMS:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # Format: YYYYMMDD-HHMMSS
        vm_label = f"gpu-{timestamp}"
        response = requests.post(LINODE_API_URL, headers=HEADERS, json={
            "type": "g6-standard-1",  # Modify this for a GPU VM type if needed
            "region": "us-east",
            "image": "linode/ubuntu22.04",
            "label": vm_label,
            "root_pass": "your_secure_password",
            "firewall_id": 849035
        })

    if response.status_code == 200:
        vm_data = response.json()
        vm_id = vm_data.get("id")
        print(f"🚀 Provisioned VM {vm_label} (ID: {vm_id}), checking status...")

        # Wait for VM to be fully ready
        if check_vm_provision_status(vm_id):
            print(f"✅ VM {vm_label} is now ACTIVE and READY TO USE.")
        else:
            print(f"❌ VM {vm_label} failed to become ready.")

        vm_creation_timestamps.append(now)  # Store timestamp after successful creation
    else:
        print(f"Failed to provision VM: {response.text}")

    return response.json()

    return None

#Basic Check if a VM is idle (no unacknowledged messages)
def is_vm_idle(vm_name):
    """Check if a VM is idle (no unacknowledged messages)."""
    response = requests.get(
        "https://172-236-148-105.ip.linodeusercontent.com/api/queues/172-236-148-105.ip.linodeusercontent.com/queue-2",
        auth=(RABBITMQ_USER, RABBITMQ_PASS),
    )
    queue_info = response.json()
    unacked_messages = queue_info.get("messages_unacknowledged", 0)
    
    return unacked_messages == 0

#Delete function
def delete_idle_gpu_vm():
    """Gracefully delete an idle GPU-labeled VM after cooldown period."""
    global idle_vm_timers

    try:
        response = requests.get(LINODE_API_URL, headers=HEADERS)
        instances = response.json().get("data", [])

        for instance in instances:
            vm_name = instance["label"]
            vm_id = instance["id"]

            if not vm_name.startswith("gpu-"):
                continue  # Skip non-GPU VMs
            
            vm_status = check_vm_running_status(vm_id)
            if vm_status != "running":
                print(f"⏳ VM {vm_name} (ID: {vm_id}) is not running, skipping scale down...")
                continue

            if is_vm_idle(vm_name):
                now = time.time()

                if vm_name not in idle_vm_timers:
                    idle_vm_timers[vm_name] = now
                    continue

                elapsed_time = now - idle_vm_timers[vm_name]

                if elapsed_time >= COOLDOWN_PERIOD:
                    print(f"⚠️ VM {vm_name} (ID: {vm_id}) has been idle for {COOLDOWN_PERIOD} seconds. Preparing to delete...")

                    delete_url = f"{LINODE_API_URL}/{vm_id}"
                    response = requests.delete(delete_url, headers=HEADERS)

                    if response.status_code == 200:
                        print(f"✅ Successfully deleted VM {vm_name} (ID: {vm_id}).")
                        del idle_vm_timers[vm_name]
                    else:
                        print(f"❌ Failed to delete VM {vm_name} (ID: {vm_id}): {response.text}")

                    return

            else:
                if vm_name in idle_vm_timers:
                    del idle_vm_timers[vm_name]  # Reset cooldown if VM is no longer idle

    except requests.RequestException as e:
        print(f"Error deleting VM: {e}")

#main function for autoscaller logic
def autoscaler_loop():
    """Main loop to monitor queue length and scale VMs."""
    while True:
        queue_length = get_queue_length()
        active_gpu_vms = get_active_gpu_vm_count()

        print(f"Queue Length: {queue_length}, Active GPU VMs: {active_gpu_vms}")

        if queue_length > active_gpu_vms and active_gpu_vms < MAX_VMS:
            print("Scaling up GPU VM...")
            provision_vm()

        elif queue_length < active_gpu_vms and active_gpu_vms > MIN_VMS:
            print("Checking for idle GPU VMs to scale down...")
            delete_idle_gpu_vm()

        time.sleep(RABBIT_MQ_TIME_INTERVAL_CHECK)  # Check time interval based on RABBIT_MQ_TIME_INTERVAL_CHECK value set


if __name__ == "__main__":
    autoscaler_loop()