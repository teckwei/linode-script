# Test VLAN IP Without Duplicate (v2)

## Overview
This Python script checks for duplicate IP addresses in a VLAN environment and ensures that each IP is unique across the network. It is designed for use cases where maintaining unique IP addresses in a VLAN is critical for network stability and communication.

## Features
- Scans VLAN for assigned IP addresses.
- Identifies duplicate IPs.
- Logs results for further analysis.
- Lightweight and easy to use.

## Prerequisites
- Python 3.x
- Required dependencies (see [Installation](#installation))
- Access to VLAN network

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/teckwei/linode-script.git
   ```
2. Navigate to the script directory:
   ```bash
   cd linode-script/VLAN_use_case_script
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setup Environment Variables
Before running the script, set up the required environment variables:

### Linux/macOS (Bash)
```bash
export API_TOKEN="your_api_token"
export VLAN_ID="your_vlan_id"
export CIDR="your_cidr"
```

### Windows (Command Prompt)
```cmd
set API_TOKEN=your_api_token
set VLAN_ID=your_vlan_id
set CIDR=your_cidr
```

### Windows (PowerShell)
```powershell
$env:API_TOKEN="your_api_token"
$env:VLAN_ID="your_vlan_id"
$env:CIDR="your_cidr"
```

### Using a `.env` File
1. Install `python-dotenv`:
   ```bash
   pip install python-dotenv
   ```
2. Create a `.env` file in the same directory as your script and add:
   ```
   API_TOKEN=your_api_token
   VLAN_ID=your_vlan_id
   CIDR=your_cidr
   ```
3. Update the script to load the `.env` file:
   ```python
   from dotenv import load_dotenv
   import os

   load_dotenv()

   api_token = os.environ.get("API_TOKEN")
   vlan_id = os.environ.get("VLAN_ID")
   cidr = os.environ.get("CIDR")
   ```

## Usage
Run the script with the following command:
```bash
python test-vlan-ip-without-duplicate-v2.py
```

The script will scan the VLAN network, check for duplicate IPs, and display the results in the console.

## Configuration
If needed, modify the script to match your VLAN setup. You may need to update:
- VLAN interface details
- IP range to scan
- Logging settings

## Example Output
```
2025/02/12 16:46:22 Starting check...
2025/02/12 16:46:26 Used IPs: {'10.136.91.56', '10.136.90.241', '10.21.97', '10.136.89.56', '10.0.20.255', '10.0.20.154'}
2025/02/12 16:46:26 CIDR: 10.136.88.0/21, Total Usable IPs: 2046, Used IPs: 6, Remaining IPs: 2040
2025/02/12 16:46:26 Remaining available IPs in 10.136.88.0/21: 2040
2025/02/12 16:46:26 Found 10 node(s).
2025/02/12 16:46:27 lke338887-544651-51c5879a0000 is already properly configured.
2025/02/12 16:46:30 lke338887-544651-13efbf00000 is already properly configured.
2025/02/12 16:46:31 lke338887-544651-521395b0000 is already properly configured.
2025/02/12 16:46:32 lke338887-544705-5fbe4eaa0000 is already properly configured.
2025/02/12 16:46:33 lke338887-544705-3ed1787d0000 is already properly configured.
2025/02/12 16:46:34 lke338887-544705-90eb0a000000 is already properly configured.
2025/02/12 16:46:40 Attempt 1: Testing IP 10.136.95.67.
2025/02/12 16:46:41 Found unused IP: 10.136.95.67.
2025/02/12 16:46:42 lke338887-544651-01449d830000 Successfully attached VLAN to Linode instance.
2025/02/12 16:46:43 lke338887-544651-01449d830000 Successfully rebooted Linode instance.
2025/02/12 16:46:44 Attempt 1: Testing IP 10.136.91.198.
2025/02/12 16:46:45 Found unused IP: 10.136.91.198.
2025/02/12 16:46:46 lke338887-544651-0f5783c60000 Successfully attached VLAN to Linode instance.
2025/02/12 16:46:47 lke338887-544651-0f5783c60000 Successfully rebooted Linode instance.
2025/02/12 16:46:48 Check completed. No changes needed.
```

## Contributing
Feel free to submit issues or pull requests to improve the script.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

