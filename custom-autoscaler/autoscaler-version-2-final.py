from datetime import datetime, timedelta
import os
import time
import requests
import asyncio
import aiohttp
from dotenv import load_dotenv
import logging
from typing import Dict, Set
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Scaling Configurations
MIN_VMS = int(os.getenv("MIN_VMS", 1))
MAX_VMS = int(os.getenv("MAX_VMS", 10))
RABBIT_MQ_TIME_INTERVAL_CHECK = int(os.getenv("RABBIT_MQ_TIME_INTERVAL_CHECK", 30)) # Default 30 seconds
SCALE_COOLDOWN = int(os.getenv("SCALE_COOLDOWN", 300))  # Default 5 minutes for both scale up/down
SCALE_THRESHOLD = int(os.getenv("SCALE_THRESHOLD", 2))  # Default 2 VMs difference threshold

# VM Tag Configuration
VM_TAGS = os.getenv("VM_TAGS", "fitroom-autoscaler").split(",")  # Default tag, can be comma-separated list
VM_TAGS = [tag.strip() for tag in VM_TAGS]  # Remove any whitespace from tags

# Linode & RabbitMQ API Config
LINODE_API_TOKEN = os.getenv("LINODE_API_TOKEN")

# RabbitMQ Configuration
RABBITMQ_ENDPOINT = os.getenv("RABBITMQ_ENDPOINT")
RABBITMQ_VHOST = quote_plus(os.getenv("RABBITMQ_VHOST", "/"))  # URL encode vhost
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "default_queue")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

# Construct RabbitMQ API URL
RABBITMQ_API_URL = f"{RABBITMQ_ENDPOINT}/api/queues/{RABBITMQ_VHOST}/{RABBITMQ_QUEUE}"

HEADERS = {"Authorization": f"Bearer {LINODE_API_TOKEN}", "Content-Type": "application/json"}
LINODE_API_URL = "https://api.linode.com/v4/linode/instances"

# Track idle VM cooldown
idle_vm_timers = {}

# Track recent VM creation times
vm_creation_timestamps = []

# Track VM provisioning attempts
vm_provision_tracking: Dict[int, datetime] = {}
MAX_PROVISION_WAIT_TIME = 600  # 10 minutes in seconds

# Track scale operations cooldown
scale_timestamps = []

# Track VM last activity
vm_last_activity = {}

#Check Instance status function
async def check_vm_running_status(vm_id, session):
    """Check the status of a Linode VM."""
    status_url = f"{LINODE_API_URL}/{vm_id}"

    try:
        async with session.get(status_url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("status")
            else:
                logger.error(f"Failed to check VM status: {await response.text()}")
                return None
    except Exception as e:
        logger.error(f"Error checking VM status: {str(e)}")
        return None

#Fetch RabbitMQ Queue Length
async def get_queue_length():
    """Fetch RabbitMQ queue length."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                RABBITMQ_API_URL,
                auth=aiohttp.BasicAuth(RABBITMQ_USER, RABBITMQ_PASS)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("messages", 0)
                else:
                    logger.error(f"Failed to get queue length: {await response.text()}")
                    return -1
    except Exception as e:
        logger.error(f"Error fetching queue length: {str(e)}")
        return -1

#fetch active instance created
async def get_active_gpu_vm_count():
    """Fetch active Linode VMs with label starting with 'gpu-'."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(LINODE_API_URL, headers=HEADERS) as response:
                if response.status == 200:
                    data = await response.json()
                    instances = data.get("data", [])
                    # Count VMs with label prefix and configured tags
                    gpu_vms = [vm for vm in instances 
                             if vm["label"].startswith("gpu-") 
                             and all(tag in vm.get("tags", []) for tag in VM_TAGS)]
                    
                    # Log detailed information about found VMs
                    logger.info(f"Found {len(gpu_vms)} GPU VMs:")
                    for vm in gpu_vms:
                        logger.info(f"  - VM {vm['label']} (ID: {vm['id']}) with tags: {vm.get('tags', [])}")
                    
                    return len(gpu_vms)
                else:
                    logger.error(f"Failed to get active VM count: {await response.text()}")
                    return -1
    except Exception as e:
        logger.error(f"Error fetching active VM count: {str(e)}")
        return -1

#Function to create new VM instance
async def create_vm_instance(session, vm_label):
    """Create a new Linode VM instance."""
    try:
        # Create a more descriptive label with status and timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        full_label = f"{vm_label}-{timestamp}"
        
        async with session.post(
            LINODE_API_URL,
            headers=HEADERS,
            json={
                "type": "g6-standard-1",  # Modify this for a GPU VM type if needed
                "region": "us-east",
                "image": "linode/ubuntu22.04",
                "label": full_label,
                "root_pass": "your_secure_password",
                "firewall_id": 849035,
                "tags": VM_TAGS
            }
        ) as response:
            if response.status == 200:
                vm_data = await response.json()
                vm_id = vm_data.get("id")
                logger.info(f"VM {full_label} (ID: {vm_id}) created with tags: {VM_TAGS}")
                return vm_data
            else:
                logger.error(f"Failed to create VM: {await response.text()}")
                return None
    except Exception as e:
        logger.error(f"Error creating VM: {str(e)}")
        return None

#Function to handle rate limiting
async def handle_rate_limit(vm_creation_timestamps):
    """Handle rate limiting for VM creation."""
    now = datetime.now()
    # Clean up timestamps older than 30 seconds
    vm_creation_timestamps = [ts for ts in vm_creation_timestamps if now - ts < timedelta(seconds=30)]
    
    # Rate limit: max 10 requests per 30 seconds
    if len(vm_creation_timestamps) >= 10:
        wait_time = (30 - (now - vm_creation_timestamps[0]).seconds)
        logger.info(f"Rate limit reached! Waiting {wait_time} seconds before next VM creation...")
        await asyncio.sleep(wait_time)
    
    return vm_creation_timestamps

#Function to handle scale cooldown
async def handle_scale_cooldown(bypass_cooldown=False):
    """Handle cooldown period for scale operations."""
    global scale_timestamps
    now = datetime.now()
    
    # Clean up timestamps older than cooldown period
    scale_timestamps = [ts for ts in scale_timestamps if now - ts < timedelta(seconds=SCALE_COOLDOWN)]
    
    # If we've scaled recently and not bypassing cooldown, wait
    if scale_timestamps and not bypass_cooldown:
        wait_time = (SCALE_COOLDOWN - (now - scale_timestamps[0]).seconds)
        logger.info(f"Scale cooldown active! Waiting {wait_time} seconds before next scale operation...")
        await asyncio.sleep(wait_time)
        return False
    
    return True

#Function to setup VM with label GPU
async def provision_vm(bypass_cooldown=False):
    """Create a new Linode GPU VM with a label starting with 'gpu-'."""
    global vm_creation_timestamps, scale_timestamps  # Explicitly declare globals
    current_vms = await get_active_gpu_vm_count()
    
    # Double check MAX_VMS limit before proceeding
    if current_vms >= MAX_VMS:
        logger.info(f"Maximum VM limit ({MAX_VMS}) reached. Skipping VM creation.")
        return None
    
    # Handle rate limiting
    vm_creation_timestamps = await handle_rate_limit(vm_creation_timestamps)

    # Check scale cooldown
    if not await handle_scale_cooldown(bypass_cooldown):
        return None

    # Create a descriptive label with status
    vm_label = f"gpu-worker"
    now = datetime.now()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create VM instance
            vm_data = await create_vm_instance(session, vm_label)
            if vm_data:
                logger.info(f"✅ VM {vm_data['label']} creation initiated.")
                vm_creation_timestamps.append(now)  # Store timestamp after successful creation
                if not bypass_cooldown:  # Only add to scale timestamps if not bypassing cooldown
                    scale_timestamps.append(now)
                return vm_data
            return None
    except Exception as e:
        logger.error(f"Error in provision_vm: {str(e)}")
        return None

#Function to delete a VM
async def delete_vm(vm_id, session):
    """Delete a specific VM by ID."""
    try:
        async with session.delete(f"{LINODE_API_URL}/{vm_id}", headers=HEADERS) as response:
            if response.status == 200:
                logger.info(f"VM {vm_id} deleted")
                return True
            else:
                logger.error(f"Failed to delete VM {vm_id}")
                return False
    except Exception as e:
        logger.error(f"Error deleting VM {vm_id}")
        return False

#Function to check if VM should be deleted
async def should_delete_vm(vm_name, queue_length, active_vm_count):
    """
    Determine if a VM should be deleted based on:
    1. Minimum VM requirement
    2. Queue length vs Active VMs ratio
    3. Scale threshold difference
    """
    # Basic conditions that must be met
    conditions = [
        active_vm_count > MIN_VMS,        # More than minimum VMs
        active_vm_count > queue_length,    # More VMs than needed for queue
        (active_vm_count - queue_length) >= SCALE_THRESHOLD  # Difference exceeds threshold
    ]
    
    if all(conditions):
        logger.info(
            f"VM {vm_name} meets deletion criteria:\n"
            f"- Active VMs: {active_vm_count} (minimum: {MIN_VMS})\n"
            f"- Queue length: {queue_length}\n"
            f"- Difference: {active_vm_count - queue_length} (threshold: {SCALE_THRESHOLD})"
        )
        return True
    
    return False

#Delete function
async def delete_idle_gpu_vm():
    """
    Gracefully delete GPU-labeled VMs based on:
    - Minimum VM requirement
    - Queue length
    - Scale cooldown
    - Scale threshold
    """
    global scale_timestamps
    try:
        # Get current queue length
        queue_length = await get_queue_length()
        if queue_length == -1:
            logger.error("Failed to get queue length, skipping VM deletion")
            return

        # Check scale cooldown first
        if not await handle_scale_cooldown(bypass_cooldown=False):
            return

        async with aiohttp.ClientSession() as session:
            # Get current VM instances
            async with session.get(LINODE_API_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Linode instances: {await response.text()}")
                    return
                
                instances = (await response.json()).get("data", [])
                # Filter for GPU VMs with configured tags
                gpu_instances = [inst for inst in instances 
                               if inst["label"].startswith("gpu-") 
                               and all(tag in inst.get("tags", []) for tag in VM_TAGS)]
                active_vm_count = len(gpu_instances)

                # If we're at or below minimum VMs, don't delete any
                if active_vm_count <= MIN_VMS:
                    logger.info(f"Active VM count ({active_vm_count}) at or below minimum ({MIN_VMS}), skipping deletion check")
                    return

                # If queue length >= active VMs, don't delete any
                if queue_length >= active_vm_count:
                    logger.info(f"Queue length ({queue_length}) >= active VMs ({active_vm_count}), skipping deletion check")
                    return

                # Check if difference between active VMs and queue length meets threshold
                vm_difference = active_vm_count - queue_length
                if vm_difference < SCALE_THRESHOLD:
                    logger.info(f"VM difference ({vm_difference}) below threshold ({SCALE_THRESHOLD}), skipping deletion check")
                    return

                # Calculate how many VMs we need to delete
                target_vm_count = queue_length  # Target should match queue length exactly
                vms_to_delete = min(
                    active_vm_count - MIN_VMS,  # Don't delete below minimum
                    active_vm_count - target_vm_count  # Delete down to target
                )

                logger.info(
                    f"Deletion calculation:\n"
                    f"- Current VMs: {active_vm_count}\n"
                    f"- Queue length: {queue_length}\n"
                    f"- Current difference: {vm_difference}\n"
                    f"- Target VM count: {target_vm_count} (matching queue length)\n"
                    f"- VMs to delete: {vms_to_delete}\n"
                    f"- Final VM count after deletion: {active_vm_count - vms_to_delete}\n"
                    f"- Final difference after deletion: {active_vm_count - vms_to_delete - queue_length}"
                )
                
                # Sort instances by creation time (oldest first) for deletion
                gpu_instances.sort(key=lambda x: x.get("created", ""))
                
                # Delete VMs until we reach target count
                deleted_count = 0
                for instance in gpu_instances:
                    if deleted_count >= vms_to_delete:
                        break
                        
                    vm_name = instance["label"]
                    vm_id = instance["id"]
                    
                    # Check VM status
                    vm_status = await check_vm_running_status(vm_id, session)
                    if vm_status != "running":
                        logger.info(f"⏳ VM {vm_name} (ID: {vm_id}) is not running, skipping...")
                        continue

                    # Check if VM should be deleted
                    logger.info(f"⚠️ Preparing to delete VM {vm_name} (ID: {vm_id})")

                    # Delete the VM
                    if await delete_vm(vm_id, session):
                        deleted_count += 1

                # Only add timestamp after all planned deletions are complete
                if deleted_count > 0:
                    scale_timestamps.append(datetime.now())
                    logger.info(f"Completed deletion of {deleted_count} VMs, applying cooldown")
                    # Wait for cooldown period after deletion
                    await handle_scale_cooldown(bypass_cooldown=False)

    except Exception as e:
        logger.error(f"Error in delete_idle_gpu_vm: {str(e)}")
        
    finally:
        # Log current VM and queue status
        active_vms = await get_active_gpu_vm_count()
        current_queue = await get_queue_length()
        logger.info(
            f"Deletion check completed:\n"
            f"- Current active VMs: {active_vms}\n"
            f"- Current queue length: {current_queue}\n"
            f"- Current difference: {active_vms - current_queue}"
        )

async def monitor_vm_status(vm_id, vm_label, session):
    """Monitor a single VM's provisioning status in a separate thread."""
    try:
        for _ in range(30):  # Check for up to 5 minutes (10s interval)
            status = await check_vm_running_status(vm_id, session)
            if status == "running":
                logger.info(f"VM {vm_label} ready")
                return True
            await asyncio.sleep(10)
        
        logger.error(f"VM {vm_label} failed to initialize")
        await delete_vm(vm_id, session)
        return False
    except Exception as e:
        logger.error(f"Error monitoring VM {vm_label}")
        return False

async def monitor_vm_provisioning():
    """
    Monitor VMs that are being provisioned and delete them if they don't reach running status
    within the maximum wait time.
    """
    logger.info(f"Starting VM provisioning monitor at {datetime.now()}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(LINODE_API_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Linode instances: {await response.text()}")
                    return
                
                instances = (await response.json()).get("data", [])
                current_time = datetime.now()
                vms_to_delete: Set[int] = set()
                
                # Create tasks for monitoring each VM
                monitoring_tasks = []
                
                # Check all instances
                for instance in instances:
                    vm_id = instance["id"]
                    vm_label = instance["label"]
                    status = instance["status"]
                    
                    # Skip non-GPU VMs
                    if not vm_label.startswith("gpu-"):
                        continue
                    
                    # Add to tracking if not already tracked
                    if vm_id not in vm_provision_tracking and status != "running":
                        vm_provision_tracking[vm_id] = current_time
                        logger.info(f"Started tracking VM {vm_label} (ID: {vm_id}) at {current_time}")
                        # Create monitoring task for this VM
                        monitoring_tasks.append(
                            asyncio.create_task(monitor_vm_status(vm_id, vm_label, session))
                        )
                        continue
                    
                    # Check if VM has been in non-running state too long
                    if vm_id in vm_provision_tracking and status != "running":
                        start_time = vm_provision_tracking[vm_id]
                        elapsed_time = (current_time - start_time).total_seconds()
                        
                        if elapsed_time >= MAX_PROVISION_WAIT_TIME:
                            logger.warning(
                                f"VM {vm_label} (ID: {vm_id}) has been in {status} status for "
                                f"{elapsed_time:.1f} seconds (started at {start_time})"
                            )
                            vms_to_delete.add(vm_id)
                    
                    # Remove from tracking if running
                    elif status == "running" and vm_id in vm_provision_tracking:
                        start_time = vm_provision_tracking[vm_id]
                        elapsed_time = (current_time - start_time).total_seconds()
                        logger.info(
                            f"VM {vm_label} (ID: {vm_id}) is now running after "
                            f"{elapsed_time:.1f} seconds (started at {start_time})"
                        )
                        del vm_provision_tracking[vm_id]
                
                # Wait for all monitoring tasks to complete
                if monitoring_tasks:
                    await asyncio.gather(*monitoring_tasks)
                
                # Delete VMs that took too long to provision
                for vm_id in vms_to_delete:
                    logger.warning(f"Deleting VM {vm_id} due to provision timeout at {current_time}")
                    await delete_vm(vm_id, session)
                    if vm_id in vm_provision_tracking:
                        del vm_provision_tracking[vm_id]
                
                # Log current tracking status
                if vm_provision_tracking:
                    logger.info(f"Currently tracking {len(vm_provision_tracking)} VMs in provisioning state:")
                    for vm_id, start_time in vm_provision_tracking.items():
                        elapsed = (current_time - start_time).total_seconds()
                        logger.info(f"  - VM {vm_id}: provisioning for {elapsed:.1f} seconds")
    
    except Exception as e:
        logger.error(f"Error in monitor_vm_provisioning: {str(e)}")

#Function to ensure minimum GPU VMs are running
async def ensure_minimum_gpu_vms():
    """Ensure minimum number of GPU VMs are running at startup."""
    global vm_creation_timestamps  # Declare global variable
    logger.info("Checking minimum VM requirement...")
    
    try:
        # Get current VM count
        current_vms = await get_active_gpu_vm_count()
        if current_vms == -1:
            logger.error("Failed to get VM count")
            return

        vms_needed = max(0, MIN_VMS - current_vms)
        if vms_needed > 0:
            logger.info(f"Creating {vms_needed} VMs to meet minimum requirement")
            
            # Create VMs in parallel with rate limiting
            created_count = 0
            monitoring_tasks = []
            
            # Create a single session for all monitoring tasks
            async with aiohttp.ClientSession() as session:
                for i in range(vms_needed):
                    try:
                        # Handle rate limiting before creating VM
                        vm_creation_timestamps = await handle_rate_limit(vm_creation_timestamps)
                        
                        vm_data = await provision_vm(bypass_cooldown=True)  # Bypass cooldown during initialization
                        
                        if vm_data:
                            vm_id = vm_data.get("id")
                            vm_label = vm_data.get("label")
                            created_count += 1
                            
                            # Start monitoring this VM in parallel using the shared session
                            monitoring_tasks.append(
                                asyncio.create_task(monitor_vm_status(vm_id, vm_label, session))
                            )
                        
                        # Add a delay between VM creation requests
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"Error creating VM {i+1}/{vms_needed}: {str(e)}")
                        continue
                
                # Wait for all monitoring tasks to complete
                if monitoring_tasks:
                    await asyncio.gather(*monitoring_tasks)
            
            # Verify final VM count
            final_vm_count = await get_active_gpu_vm_count()
            if final_vm_count >= MIN_VMS:
                logger.info(f"Initialization complete: {final_vm_count} VMs running")
            else:
                logger.warning(f"Initialization incomplete: {final_vm_count} VMs running (created {created_count} VMs)")
        else:
            logger.info(f"Initialization complete: {current_vms} VMs running")
    
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")

#main function for autoscaller logic
async def autoscaler_loop():
    """Main loop to monitor queue length and scale VMs."""
    # Ensure minimum VMs are running at startup
    await ensure_minimum_gpu_vms()
    
    # Start VM monitoring in a separate task
    monitoring_task = asyncio.create_task(run_vm_monitoring())
    
    # Main autoscaler loop
    while True:
        try:
            queue_length = await get_queue_length()
            active_gpu_vms = await get_active_gpu_vm_count()

            logger.info(f"Queue Length: {queue_length}, Active GPU VMs: {active_gpu_vms}")

            # If we have no active VMs and there are items in the queue, create VMs immediately
            if active_gpu_vms == 0 and queue_length > 0:
                vms_to_create = min(SCALE_THRESHOLD, MAX_VMS, queue_length)
                logger.warning(f"No active VMs but queue has {queue_length} items. Creating {vms_to_create} VMs immediately.")
                # Create all VMs in parallel with cooldown bypassed
                tasks = []
                for _ in range(vms_to_create):
                    tasks.append(asyncio.create_task(provision_vm(bypass_cooldown=True)))
                    await asyncio.sleep(5)  # Small delay between VM creations
                await asyncio.gather(*tasks)
                # Add timestamp after creating VMs
                scale_timestamps.append(datetime.now())
            # Check if we need to scale up based on queue length
            elif queue_length > active_gpu_vms and active_gpu_vms < MAX_VMS:
                # Calculate how many more VMs we can create without exceeding MAX_VMS
                remaining_slots = MAX_VMS - active_gpu_vms
                
                # Calculate how many VMs we need to handle the queue
                vms_needed = queue_length - active_gpu_vms
                
                # Create VMs based on threshold, but never more than needed for queue
                vms_to_create = min(SCALE_THRESHOLD, remaining_slots, vms_needed)
                logger.info(f"Queue length ({queue_length}) > active VMs ({active_gpu_vms}). Creating {vms_to_create} VMs based on threshold.")
                
                # Create all VMs in parallel
                tasks = []
                for _ in range(vms_to_create):
                    tasks.append(asyncio.create_task(provision_vm(bypass_cooldown=True)))
                    await asyncio.sleep(5)  # Small delay between VM creations
                await asyncio.gather(*tasks)
                
                # Only apply cooldown after all VMs are created
                if vms_to_create > 0:
                    scale_timestamps.append(datetime.now())
                    # Check cooldown after creating VMs
                    if not await handle_scale_cooldown(bypass_cooldown=False):
                        await asyncio.sleep(RABBIT_MQ_TIME_INTERVAL_CHECK)
                        continue
            elif queue_length < active_gpu_vms and active_gpu_vms > MIN_VMS:
                logger.info("Checking for VMs to scale down...")
                await delete_idle_gpu_vm()

            await asyncio.sleep(RABBIT_MQ_TIME_INTERVAL_CHECK)
        
        except Exception as e:
            logger.error(f"Error in autoscaler_loop: {str(e)}")
            await asyncio.sleep(RABBIT_MQ_TIME_INTERVAL_CHECK)  # Still sleep on error to prevent rapid retries

async def run_vm_monitoring():
    """Run VM monitoring in a separate loop."""
    while True:
        try:
            await monitor_vm_provisioning()
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in VM monitoring loop: {str(e)}")
            await asyncio.sleep(30)  # Wait before retrying

if __name__ == "__main__":
    asyncio.run(autoscaler_loop())