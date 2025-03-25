# Linode VM Statistics Collector

This script collects and exports performance statistics for Linode virtual machines (VMs), specifically targeting Nanode and shared linode instances types. It gathers CPU utilization, disk I/O, and network traffic metrics for both 24-hour and last 30 days periods.

## Features

- Filters VMs by type (g6-standard and g6-nanode)
- Collects performance metrics:
  - CPU Utilization
  - Disk I/O and Swap usage
  - Network traffic (IPv4 and IPv6, public and private)
- Exports data to Excel with formatted columns
- Supports both 24-hour and monthly statistics
- Asynchronous data collection for improved performance
- Built-in rate limiting to prevent API throttling
  - Respects Linode's 1200 requests/hour limit
  - Conservative limit of 120 requests/minute
  - Automatic request throttling and retry mechanism

## Prerequisites

- Python 3.7 or higher
- Linode API Token with read access
- Required Python packages (install via pip):
  ```bash
  pip install aiohttp pandas python-dotenv openpyxl
  ```

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/teckwei/linode-script.git
   cd linode-script/vm_statistic_report
   ```

2. Create a `.env` file in the project directory:
   ```bash
   touch .env
   ```

3. Add your Linode API token to the `.env` file:
   ```
   LINODE_API_TOKEN=your_api_token_here
   ```

## Usage

Run the script using Python:
```bash
python vm-stats.py
```

The script will:
1. Fetch a list of all your Linode instances
2. Filter for g6-standard and g6-nanode instances
3. Collect performance statistics for each VM
4. Generate an Excel file named `vm_statistics_YYYYMMDD_HHMMSS.xlsx`

## Output Format

The generated Excel file contains the following columns:
- Instance Name: The label of your Linode instance
- Linode ID: The unique identifier of the instance
- Type: The Linode instance type (g6-standard or g6-nanode)
- CPU Utilization (24h): Average CPU usage over the last 24 hours
- CPU Utilization (Month): Average CPU usage for the current month
- Disk IO metrics (24h and Month)
- Network traffic metrics (24h and Month)

## Error Handling

The script includes comprehensive error handling and logging:
- Failed API requests are logged with error messages
- Invalid or missing data is handled gracefully
- Debug information is available in the logs

## Logging

Logs are written to stdout with the following format:
```
YYYY-MM-DD HH:MM:SS - LEVEL - Message
```

Log levels include:
- INFO: General progress information
- ERROR: Failed operations and errors
- DEBUG: Detailed debugging information (disabled by default)

## Customization

To modify the script's behavior:

1. To enable debug logging, modify the logging configuration:
   ```python
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )
   ```

2. To change the VM types being filtered, modify the filter condition in `get_all_vm_stats()`:
   ```python
   if vm_type and any(t in vm_type for t in ["your-type-1", "your-type-2"]):
   ```

## Troubleshooting

Common issues and solutions:

1. **API Token Issues**
   - Ensure your API token has read access
   - Verify the token is correctly set in the `.env` file
   - Check for any whitespace in the token

2. **No Data Collected**
   - Verify you have g6-standard or g6-nanode instances
   - Check the API token permissions
   - Look for error messages in the logs

3. **Excel File Issues**
   - Ensure you have write permissions in the directory
   - Check if the file is open in another program
   - Verify openpyxl is installed correctly

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Rate Limiting

The script implements rate limiting to match Linode's API limits exactly:

1. **API Limits**
   - Linode's limit: 800 requests per 2 minutes
   - Script uses exact limit with smart retry mechanism
   - Automatic request pacing to maximize throughput

2. **Rate Limit Handling**
   - Tracks API request timestamps using sliding window
   - Automatically pauses when approaching limits
   - Retries requests that fail due to rate limiting
   - Detailed logging of rate limit events

3. **Customizing Rate Limits**
   
   You can modify the rate limiting behavior by adjusting these constants:
   ```python
   RATE_LIMIT_REQUESTS = 800  # Maximum requests per 2 minutes
   RATE_LIMIT_PERIOD = 120   # Time period in seconds
   ```

4. **Rate Limit Response**
   - When rate limit is reached:
     - Script automatically pauses
     - Calculates optimal wait time
     - Retries the request after waiting
     - Provides detailed logging with request counts and wait times 