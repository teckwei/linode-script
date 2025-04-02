import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
from typing import Dict, List, Optional, Union
import pandas as pd
from openpyxl.utils import get_column_letter
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Linode API Configuration
LINODE_API_TOKEN = os.getenv("LINODE_API_TOKEN")
HEADERS = {"Authorization": f"Bearer {LINODE_API_TOKEN}", "Content-Type": "application/json"}
LINODE_API_URL = "https://api.linode.com/v4/linode/instances"
LINODE_REGIONS_URL = "https://api.linode.com/v4/regions"
LINODE_TYPES_URL = "https://api.linode.com/v4/linode/types"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 800  # Maximum requests per 2 minutes (Linode's limit)
RATE_LIMIT_PERIOD = 120   # Time period in seconds (2 minutes)
BATCH_SIZE = 3           # Process 3 VMs per batch (6 API calls)
BATCH_DELAY = 5         # 5 seconds delay between batches
request_timestamps = []

# For 1000 instances:
# - Each instance requires 2 API calls (24h and monthly stats)
# - Total API calls = 1000 * 2 = 2000 calls
# - At 800 calls per 2 minutes (6.67 calls/second)
# - With 3 VMs per batch (6 API calls) and 5s delay
# - Estimated time: ~35-40 minutes
TOTAL_TIMEOUT = 3600    # 45 minutes total timeout

def check_rate_limit():
    """
    Check and enforce API rate limits.
    Linode's rate limit is 800 requests per 2 minutes.
    We'll implement a more conservative limit to avoid hitting the rate limit.
    """
    current_time = time.time()
    
    # Remove timestamps older than our rate limit period
    global request_timestamps
    request_timestamps = [ts for ts in request_timestamps if current_time - ts < RATE_LIMIT_PERIOD]
    
    # Use a more conservative limit (700 requests per 2 minutes)
    conservative_limit = 700
    
    # If we've hit the conservative limit, sleep until we can make another request
    if len(request_timestamps) >= conservative_limit:
        sleep_time = request_timestamps[0] + RATE_LIMIT_PERIOD - current_time + 5  # Add 5 second buffer
        if sleep_time > 0:
            logger.warning(f"Approaching rate limit ({conservative_limit} requests per {RATE_LIMIT_PERIOD} seconds). Waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            # After sleeping, remove old timestamps again
            request_timestamps = [ts for ts in request_timestamps if time.time() - ts < RATE_LIMIT_PERIOD]
    
    # Add current request timestamp
    request_timestamps.append(current_time)

def extract_data(data_dict: Dict, path: List[str]) -> List[float]:
    """Helper function to safely extract data arrays from nested dictionary and handle time-series format
    
    The API returns data in format:
    {
        "data": {
            "io": {
                "swap": [
                    [timestamp1, value1],
                    [timestamp2, value2],
                    ...
                ]
            }
        }
    }
    """
    try:
        current = data_dict
        for key in path[:-1]:  # Navigate through all keys except the last one
            if not isinstance(current, dict) or key not in current:
                logger.debug(f"Key {key} not found in path {path}")
                return []
            current = current[key]
        
        # Get the final metric
        final_key = path[-1]
        if not isinstance(current, dict) or final_key not in current:
            logger.debug(f"Final key {final_key} not found")
            return []
            
        data_points = current[final_key]
        
        # Handle time-series data format
        if isinstance(data_points, list):
            if not data_points:
                return []
            if isinstance(data_points[0], list):
                # Extract values from [timestamp, value] pairs
                values = [point[1] for point in data_points if isinstance(point, list) and len(point) > 1]
                logger.debug(f"Extracted values from time-series: {values}")
                return values
            # Handle direct value list
            return [float(point) for point in data_points if isinstance(point, (int, float))]
            
        return []
    except Exception as e:
        logger.error(f"Error extracting data: {str(e)}")
        return []

def calculate_average(data: List[Union[float, int]]) -> float:
    """
    Calculate the average of a list of numeric values from time-series data.
    
    Args:
        data: List of numeric values (integers or floats) from time-series data
        
    Returns:
        float: The average of the values, or 0.0 if the list is empty
    """
    try:
        if not data:
            return 0.0
        
        # Convert all values to float and filter out None or non-numeric values
        numeric_values = []
        for x in data:
            try:
                if x is not None:
                    value = float(x)
                    if value >= 0:  # Only include non-negative values
                        numeric_values.append(value)
            except (ValueError, TypeError):
                continue
        
        if not numeric_values:
            return 0.0
            
        avg = sum(numeric_values) / len(numeric_values)
        logger.debug(f"Calculated average: {avg} from {len(numeric_values)} values")
        return avg
        
    except Exception as e:
        logger.error(f"Error calculating average: {str(e)}")
        return 0.0

def save_to_excel(stats_list: List[Dict], output_file: str = "vm_statistics.xlsx"):
    """
    Save VM statistics to an Excel file with a single combined sheet.
    
    Args:
        stats_list: List of VM statistics dictionaries
        output_file: Name of the output Excel file
    """
    try:
        if not stats_list:
            logger.error("No statistics to save to Excel")
            return

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"vm_statistics_{timestamp}.xlsx"
        
        # Prepare data for the combined sheet
        combined_data = []
        
        for stats in stats_list:
            vm_id = stats["vm_id"]
            label = stats["label"]
            vm_type = stats["type"]
            region = stats["region"]
            
            # Combine all statistics
            '''
            combined_data.append({
                "Instance Name": label,
                "Linode ID": vm_id,
                "Type": vm_type,
                "Region": region,
                "CPU Utilization (24h)": f"{stats['cpu']['utilization']['24h']:.2f}%",
                "CPU Utilization (Last 30 Days)": f"{stats['cpu']['utilization']['month']:.2f}%"
            })
            '''
            combined_data.append({
                "Instance Name": label,
                "Linode ID": vm_id,
                "Type": vm_type,
                "Region": region,
                "CPU Utilization (24h)": f"{stats['cpu']['utilization']['24h']:.2f}%",
                "CPU Utilization (Last 30 Days)": f"{stats['cpu']['utilization']['month']:.2f}%",
                "Disk IO (24h)": f"{stats['disk']['io']['24h']:.2f}",
                "Disk IO (Last 30 Days)": f"{stats['disk']['io']['month']:.2f}",
                "Disk Swap (24h)": f"{stats['disk']['swap']['24h']:.2f}",
                "Disk Swap (Last 30 Days)": f"{stats['disk']['swap']['month']:.2f}",
                "IPv4 Public In (24h)": f"{stats['network']['ipv4']['public']['in']['24h']:.2f}",
                "IPv4 Public Out (24h)": f"{stats['network']['ipv4']['public']['out']['24h']:.2f}",
                "IPv4 Private In (24h)": f"{stats['network']['ipv4']['private']['in']['24h']:.2f}",
                "IPv4 Private Out (24h)": f"{stats['network']['ipv4']['private']['out']['24h']:.2f}",
                "IPv4 Public In (Last 30 Days)": f"{stats['network']['ipv4']['public']['in']['month']:.2f}",
                "IPv4 Public Out (Last 30 Days)": f"{stats['network']['ipv4']['public']['out']['month']:.2f}",
                "IPv4 Private In (Last 30 Days)": f"{stats['network']['ipv4']['private']['in']['month']:.2f}",
                "IPv4 Private Out (Last 30 Days)": f"{stats['network']['ipv4']['private']['out']['month']:.2f}",
                "IPv6 Public In (24h)": f"{stats['network']['ipv6']['public']['in']['24h']:.2f}",
                "IPv6 Public Out (24h)": f"{stats['network']['ipv6']['public']['out']['24h']:.2f}",
                "IPv6 Private In (24h)": f"{stats['network']['ipv6']['private']['in']['24h']:.2f}",
                "IPv6 Private Out (24h)": f"{stats['network']['ipv6']['private']['out']['24h']:.2f}",
                "IPv6 Public In (Last 30 Days)": f"{stats['network']['ipv6']['public']['in']['month']:.2f}",
                "IPv6 Public Out (Last 30 Days)": f"{stats['network']['ipv6']['public']['out']['month']:.2f}",
                "IPv6 Private In (Last 30 Days)": f"{stats['network']['ipv6']['private']['in']['month']:.2f}",
                "IPv6 Private Out (Last 30 Days)": f"{stats['network']['ipv6']['private']['out']['month']:.2f}"
            })
        
        # Create DataFrame first
        df_combined = pd.DataFrame(combined_data)
        
        # Then create the Excel writer and save
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_combined.to_excel(writer, sheet_name="VM Statistics", index=False)
            
            # Format the sheet
            worksheet = writer.sheets["VM Statistics"]
            for idx, col in enumerate(df_combined.columns):
                max_length = max(
                    df_combined[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                col_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[col_letter].width = max_length + 2
    
        logger.info(f"Statistics saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving statistics to Excel: {str(e)}")
        raise

async def get_region_labels() -> Dict[str, str]:
    """
    Fetch region labels from Linode API.
    Returns a dictionary mapping region IDs to their labels.
    """
    try:
        async with aiohttp.ClientSession() as session:
            check_rate_limit()
            async with session.get(LINODE_REGIONS_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch region list: {await response.text()}")
                    return {}
                
                regions_data = await response.json()
                return {region["id"]: region["label"] for region in regions_data.get("data", [])}
    except Exception as e:
        logger.error(f"Error fetching region labels: {str(e)}")
        return {}

async def get_type_labels() -> Dict[str, str]:
    """
    Fetch Linode type labels from API.
    Returns a dictionary mapping type IDs to their labels.
    """
    try:
        async with aiohttp.ClientSession() as session:
            check_rate_limit()
            async with session.get(LINODE_TYPES_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch type list: {await response.text()}")
                    return {}
                
                types_data = await response.json()
                return {type_info["id"]: f"{type_info['label']} ({type_info['vcpus']} vCPUs, {type_info['memory']/1024:.1f}GB RAM)" 
                        for type_info in types_data.get("data", [])}
    except Exception as e:
        logger.error(f"Error fetching type labels: {str(e)}")
        return {}

async def get_vm_stats(vm_id: int, session: aiohttp.ClientSession, retry_count: int = 3, retry_delay: int = 5) -> Optional[Dict]:
    """
    Fetch VM statistics for the last 24 hours and specific month.
    Includes retry mechanism for rate limit handling.
    """
    for attempt in range(retry_count):
        try:
            # Check rate limit before each API call
            check_rate_limit()
            
            # Get current time
            now = datetime.now()
            current_year = now.year
            current_month = now.month

            # Fetch 24-hour stats
            stats_24h_url = f"{LINODE_API_URL}/{vm_id}/stats"
            async with session.get(stats_24h_url, headers=HEADERS) as response:
                if response.status == 429:  # Too Many Requests
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                if response.status != 200:
                    logger.error(f"Failed to fetch 24h stats for VM {vm_id}: {await response.text()}")
                    return None
                stats_24h = await response.json()

            # Check rate limit before second API call
            check_rate_limit()

            # Fetch monthly stats using the specific monthly endpoint
            stats_month_url = f"{LINODE_API_URL}/{vm_id}/stats/{current_year}/{current_month}"
            async with session.get(stats_month_url, headers=HEADERS) as response:
                if response.status == 429:  # Too Many Requests
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                if response.status != 200:
                    logger.error(f"Failed to fetch last 30 days stats for VM {vm_id}: {await response.text()}")
                    return None
                stats_month = await response.json()

            # If we got here, both API calls were successful
            stats = {
                "vm_id": vm_id,
                "cpu": {
                    "utilization": {
                        "24h": calculate_average(extract_data(stats_24h, ["data", "cpu"])),
                        "month": calculate_average(extract_data(stats_month, ["data", "cpu"])),
                    }
                },
                "disk": {
                    "io": {
                        "24h": calculate_average(extract_data(stats_24h, ["data", "io", "io"])),
                        "month": calculate_average(extract_data(stats_month, ["data", "io", "io"]))
                    },
                    "swap": {
                        "24h": calculate_average(extract_data(stats_24h, ["data", "io", "swap"])),
                        "month": calculate_average(extract_data(stats_month, ["data", "io", "swap"]))
                    }
                },
                "network": {
                    "ipv4": {
                        "public": {
                            "in": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv4", "in"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv4", "in"]))
                            },
                            "out": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv4", "out"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv4", "out"]))
                            }
                        },
                        "private": {
                            "in": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv4", "private_in"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv4", "private_in"]))
                            },
                            "out": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv4", "private_out"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv4", "private_out"]))
                            }
                        }
                    },
                    "ipv6": {
                        "public": {
                            "in": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv6", "in"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv6", "in"]))
                            },
                            "out": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv6", "out"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv6", "out"]))
                            }
                        },
                        "private": {
                            "in": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv6", "private_in"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv6", "private_in"]))
                            },
                            "out": {
                                "24h": calculate_average(extract_data(stats_24h, ["data", "netv6", "private_out"])),
                                "month": calculate_average(extract_data(stats_month, ["data", "netv6", "private_out"]))
                            }
                        }
                    }
                }
            }

            # Log the statistics
            logger.info(f"VM {vm_id} Statistics:")
            logger.info(f"CPU Utilization (24h): {stats['cpu']['utilization']['24h']:.2f}%")
            logger.info(f"CPU Utilization (Last 30 Days): {stats['cpu']['utilization']['month']:.2f}%")
            logger.info(f"Disk IO (24h): {stats['disk']['io']['24h']:.2f}")
            logger.info(f"Disk Swap (24h): {stats['disk']['swap']['24h']:.2f}")

            return stats

        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                logger.warning(f"Error fetching stats for VM {vm_id}, attempt {attempt + 1}/{retry_count}. Retrying in {wait_time} seconds... Error: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Error fetching stats for VM {vm_id} after {retry_count} attempts: {str(e)}")
                return None

async def get_all_vm_stats():
    """
    Fetch statistics for all VMs of type g6-standard and g6-nanode.
    Uses pagination to handle large numbers of instances efficiently.
    """
    try:
        # Configure connection pooling
        conn = aiohttp.TCPConnector(limit=30)
        timeout = aiohttp.ClientTimeout(total=TOTAL_TIMEOUT,
                                      connect=30,
                                      sock_read=30,
                                      sock_connect=30)
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            # First, get region and type labels (these are cached)
            region_labels = await get_region_labels()
            type_labels = await get_type_labels()
            logger.info(f"Fetched {len(region_labels)} region labels and {len(type_labels)} type labels")
            
            # Initialize variables for pagination
            page = 1
            page_size = 100  # Using smaller page size
            all_vms = []
            
            # Keep fetching pages until we get no more results
            while True:
                check_rate_limit()
                # Add X-Filter to ensure consistent results
                url = f"{LINODE_API_URL}?page={page}&page_size={page_size}&order=asc&order_by=id"
                
                try:
                    async with session.get(url, headers=HEADERS) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to fetch VM list (page {page}): {error_text}")
                            break
                        
                        response_data = await response.json()
                        vms = response_data.get("data", [])
                        page_count = response_data.get("page", 1)
                        pages = response_data.get("pages", 1)
                        results = response_data.get("results", 0)
                        
                        if page == 1:
                            logger.info(f"API reports: {results} total results across {pages} pages")
                        
                        if not vms:
                            logger.info(f"No VMs found on page {page}")
                            break
                        
                        all_vms.extend(vms)
                        current_count = len(all_vms)
                        logger.info(f"Fetched page {page}/{pages} ({len(vms)} VMs, Total collected: {current_count})")
                        
                        # If we're on the last reported page or got fewer items than page_size, we're done
                        if page >= pages or len(vms) < page_size:
                            break
                        
                        page += 1
                        await asyncio.sleep(1)  # Small delay between pages
                
                except Exception as e:
                    logger.error(f"Error fetching page {page}: {str(e)}")
                    if not all_vms:  # If we haven't fetched any VMs yet, return empty
                        return []
                    break  # Otherwise, proceed with what we have
            
            total_vms = len(all_vms)
            logger.info(f"Completed pagination. Retrieved {total_vms} total VMs")
            
            if not all_vms:
                logger.error("Failed to fetch any VMs")
                return []
            
            # Continue with filtering and processing
            logger.info(f"Total VMs before filtering: {total_vms}")
            
            # Filter VMs and prepare metadata
            filtered_vms = []
            vm_labels = {}
            vm_types = {}
            vm_regions = {}
            
            for vm in all_vms:
                vm_type = vm.get("type")
                if vm_type and any(t in vm_type for t in ["g6-standard", "g6-nanode"]):
                    vm_id = vm["id"]
                    filtered_vms.append(vm_id)
                    vm_labels[vm_id] = vm["label"]
                    vm_types[vm_id] = type_labels.get(vm_type, vm_type)
                    vm_regions[vm_id] = region_labels.get(vm["region"], vm["region"])
            
            if not filtered_vms:
                logger.info("No matching instances found")
                return []
            
            filtered_count = len(filtered_vms)
            logger.info(f"Filtered to {filtered_count} matching VMs")
            
            total_batches = (filtered_count + BATCH_SIZE - 1) // BATCH_SIZE
            estimated_time = (total_batches * BATCH_DELAY + filtered_count * 2 / 6.67) / 60
            
            logger.info(f"Processing {filtered_count} VMs in {total_batches} batches")
            logger.info(f"Estimated processing time: {estimated_time:.1f} minutes")
            
            # Process VMs in batches
            valid_stats = []
            start_time = time.time()
            
            for i in range(0, filtered_count, BATCH_SIZE):
                batch = filtered_vms[i:i + BATCH_SIZE]
                current_batch = (i // BATCH_SIZE) + 1
                elapsed_time = (time.time() - start_time) / 60
                
                logger.info(f"Processing batch {current_batch}/{total_batches} (Elapsed: {elapsed_time:.1f} minutes)")
                
                tasks = [get_vm_stats(vm_id, session) for vm_id in batch]
                batch_results = await asyncio.gather(*tasks)
                
                # Process batch results
                successful_in_batch = 0
                for stats in batch_results:
                    if stats is not None:
                        vm_id = stats["vm_id"]
                        stats["label"] = vm_labels[vm_id]
                        stats["type"] = vm_types[vm_id]
                        stats["region"] = vm_regions[vm_id]
                        valid_stats.append(stats)
                        successful_in_batch += 1
                
                completion_percentage = (len(valid_stats) / filtered_count) * 100
                logger.info(f"Batch {current_batch}: Processed {successful_in_batch}/{len(batch)} VMs successfully ({completion_percentage:.1f}% complete)")
                
                if i + BATCH_SIZE < filtered_count:
                    logger.info(f"Waiting {BATCH_DELAY} seconds before next batch...")
                    await asyncio.sleep(BATCH_DELAY)
            
            total_time = (time.time() - start_time) / 60
            success_rate = (len(valid_stats) / filtered_count) * 100
            logger.info(f"Completed processing all batches in {total_time:.1f} minutes")
            logger.info(f"Successfully processed {len(valid_stats)}/{filtered_count} VMs ({success_rate:.1f}% success rate)")
            return valid_stats

    except Exception as e:
        logger.error(f"Error in get_all_vm_stats: {str(e)}")
        return []

async def main():
    """
    Main function to run the VM statistics collection.
    """
    try:
        logger.info("Starting VM statistics collection...")
        stats = await get_all_vm_stats()
        logger.info(f"Completed collecting stats for {len(stats)} VMs")
        
        # Save statistics to Excel
        if stats:
            save_to_excel(stats)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Script terminated by user.")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 