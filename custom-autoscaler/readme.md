# Linode RabbitMQ Autoscaler

This Python script is an autoscaler for RabbitMQ queues running on Linode. It dynamically provisions and deletes Linode GPU virtual machines (VMs) based on the number of messages in the RabbitMQ queue. The script ensures efficient resource utilization by scaling up when there is demand and scaling down when VMs are idle.

## Features
- Monitors RabbitMQ queue length to determine scaling needs.
- Provisions new Linode GPU VMs when message demand exceeds capacity.
- Checks VM provisioning status until it is fully operational.
- Identifies idle VMs and deletes them after a cooldown period.
- Implements rate limiting to prevent excessive API requests.

## Requirements
- Python 3.x
- `requests` library
- `python-dotenv` library

## Prerequisite
1. Clone this repository:
   ```sh
   git clone https://github.com/teckwei/linode-script.git
   cd linode-script/custom-autoscaler
   ```

2. Create a `.env` file and configure the following environment variables:
   ```ini
   LINODE_API_TOKEN=your_linode_api_token
   RABBITMQ_URL=http://your-rabbitmq-server/api/queues/%2f/your-queue
   RABBITMQ_USER=your_rabbitmq_username
   RABBITMQ_PASS=your_rabbitmq_password
   MIN_VMS=1
   MAX_VMS=5
   COOLDOWN_PERIOD=300
   RABBIT_MQ_TIME_INTERVAL_CHECK=30
   ```

## How It Works
1. The script continuously monitors the RabbitMQ queue length.
2. If the number of queued messages exceeds the number of active GPU VMs, a new VM is provisioned (up to `MAX_VMS`).
3. If a VM is idle (no unacknowledged messages) for `COOLDOWN_PERIOD`, it is deleted (down to `MIN_VMS`).
4. The script ensures that no more than 10 VM creation requests are sent within a 30-second window to comply with Linode API rate limits.

## Running the Autoscaler
To start the autoscaler, run:
```sh
python3 autoscaler-version-1-final.py
```

## Functions Overview
### `get_queue_length()`
Fetches the current number of messages in the RabbitMQ queue.

### `get_active_gpu_vm_count()`
Retrieves the number of currently running Linode VMs labeled as GPU instances.

### `provision_vm()`
Provisions a new Linode VM with a GPU label and ensures it is fully ready before use.

### `delete_idle_gpu_vm()`
Deletes idle GPU VMs after they have been idle for the cooldown period.

### `autoscaler_loop()`
Main function that continuously monitors RabbitMQ queue length and adjusts VMs accordingly.

## Logs and Debugging
- The script provides console logs for each action (provisioning, deletion, status checks).
- If any API request fails, it logs the error response.

## Contributions
Feel free to open issues or submit pull requests to improve the script.

## Contact
For any questions or suggestions, reach out at chongteckwei15@gmail.com.

