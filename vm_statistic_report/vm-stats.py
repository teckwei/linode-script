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

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 800  # Maximum requests per 2 minutes (Linode's limit)
RATE_LIMIT_PERIOD = 120   # Time period in seconds (2 minutes)
request_timestamps = []

def check_rate_limit():
    """
    Check and enforce API rate limits.
    Linode's rate limit is 800 requests per 2 minutes.
    We'll use the exact limit since we have proper retry mechanisms in place.
    """
    current_time = time.time()
    
    # Remove timestamps older than our rate limit period
    global request_timestamps
    request_timestamps = [ts for ts in request_timestamps if current_time - ts < RATE_LIMIT_PERIOD]
    
    # If we've hit the rate limit, sleep until we can make another request
    if len(request_timestamps) >= RATE_LIMIT_REQUESTS:
        sleep_time = request_timestamps[0] + RATE_LIMIT_PERIOD - current_time
        if sleep_time > 0:
            logger.info(f"Rate limit reached ({RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_PERIOD} seconds). Waiting {sleep_time:.2f} seconds...")
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
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"vm_statistics_{timestamp}.xlsx"
        
        # Create Excel writer
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Prepare data for the combined sheet
            combined_data = []
            
            for stats in stats_list:
                vm_id = stats["vm_id"]
                label = stats["label"]
                
                # Combine all statistics
                combined_data.append({
                    "Instance Name": label,
                    "Linode ID": vm_id,
                    "CPU Utilization (24h)": f"{stats['cpu']['utilization']['24h']:.2f}%",
                    "CPU Utilization (Last 30 Days)": f"{stats['cpu']['utilization']['month']:.2f}%",
                })
                """
                combined_data.append({
                    "Instance Name": label,
                    "Linode ID": vm_id,
                    "CPU Utilization (24h)": f"{stats['cpu']['utilization']['24h']:.2f}%",
                    "CPU Utilization (Last 30 Days)": f"{stats['cpu']['utilization']['month']:.2f}%",
                    "Disk IO (24h)": f"{stats['disk']['io']['24h']:.2f}",
                    "Disk IO (Month)": f"{stats['disk']['io']['month']:.2f}",
                    "Disk Swap (24h)": f"{stats['disk']['swap']['24h']:.2f}",
                    "Disk Swap (Month)": f"{stats['disk']['swap']['month']:.2f}",
                    "IPv4 Public In (24h)": f"{stats['network']['ipv4']['public']['in']['24h']:.2f}",
                    "IPv4 Public Out (24h)": f"{stats['network']['ipv4']['public']['out']['24h']:.2f}",
                    "IPv4 Private In (24h)": f"{stats['network']['ipv4']['private']['in']['24h']:.2f}",
                    "IPv4 Private Out (24h)": f"{stats['network']['ipv4']['private']['out']['24h']:.2f}",
                    "IPv6 Public In (24h)": f"{stats['network']['ipv6']['public']['in']['24h']:.2f}",
                    "IPv6 Public Out (24h)": f"{stats['network']['ipv6']['public']['out']['24h']:.2f}",
                    "IPv6 Private In (24h)": f"{stats['network']['ipv6']['private']['in']['24h']:.2f}",
                    "IPv6 Private Out (24h)": f"{stats['network']['ipv6']['private']['out']['24h']:.2f}"
                })
                """
            
            # Create DataFrame and save to Excel
            if combined_data:
                df_combined = pd.DataFrame(combined_data)
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

async def get_vm_stats(vm_id: int, session: aiohttp.ClientSession) -> Optional[Dict]:
    """
    Fetch VM statistics for the last 24 hours and specific month.
    """
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
                logger.warning("Rate limit exceeded. Waiting before retry...")
                await asyncio.sleep(60)  # Wait a minute before retrying
                return None
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
                logger.warning("Rate limit exceeded. Waiting before retry...")
                await asyncio.sleep(60)  # Wait a minute before retrying
                return None
            if response.status != 200:
                logger.error(f"Failed to fetch monthly stats for VM {vm_id}: {await response.text()}")
                return None
            stats_month = await response.json()

        # Calculate averages for various metrics
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
        logger.info(f"CPU Utilization (Month): {stats['cpu']['utilization']['month']:.2f}%")
        logger.info(f"Disk IO (24h): {stats['disk']['io']['24h']:.2f}")
        logger.info(f"Disk Swap (24h): {stats['disk']['swap']['24h']:.2f}")

        return stats

    except Exception as e:
        logger.error(f"Error fetching stats for VM {vm_id}: {str(e)}")
        return None

async def get_all_vm_stats():
    """
    Fetch statistics for all VMs of type g6-standard and g6-nanode.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Get list of all VMs
            async with session.get(LINODE_API_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch VM list: {await response.text()}")
                    return
                
                vms = (await response.json()).get("data", [])
                
                # Create tasks for fetching stats for each VM
                tasks = []
                vm_labels = {}  # Store VM labels
                vm_types = {}  # Store VM types
                
                # Filter VMs by type and create tasks
                for vm in vms:
                    vm_type = vm.get("type")
                    if vm_type and any(t in vm_type for t in ["g6-standard", "g6-nanode"]):
                        vm_id = vm["id"]
                        vm_labels[vm_id] = vm["label"]  # Store the label
                        vm_types[vm_id] = vm_type  # Store the type
                        tasks.append(get_vm_stats(vm_id, session))
                
                if not tasks:
                    logger.info("No g6-standard or g6-nanode instances found")
                    return []
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Filter out None results and add labels and types
                valid_stats = []
                for stats in results:
                    if stats is not None:
                        vm_id = stats["vm_id"]
                        stats["label"] = vm_labels[vm_id]
                        stats["type"] = vm_types[vm_id]
                        valid_stats.append(stats)
                
                logger.info(f"Found {len(valid_stats)} g6-standard/g6-nanode instances")
                return valid_stats

    except Exception as e:
        logger.error(f"Error in get_all_vm_stats: {str(e)}")
        return []

async def main():
    """
    Main function to run the VM statistics collection.
    """
    logger.info("Starting VM statistics collection...")
    stats = await get_all_vm_stats()
    logger.info(f"Completed collecting stats for {len(stats)} VMs")
    
    # Save statistics to Excel
    if stats:
        save_to_excel(stats)

if __name__ == "__main__":
    asyncio.run(main()) 