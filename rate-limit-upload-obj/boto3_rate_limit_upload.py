import os
import threading
import time
import queue
import boto3

# Configuration
ACCESS_KEY = 'LKQJHVBVEGWEUICXM0P2'
SECRET_KEY = 'D8EofYA4BdAMNCwzLg9ByXRj4hSIU9G06bCkeePs'
ENDPOINT_URL = 'https://jp-osa-1.linodeobjects.com'
RPS = 300  # Request per second limit
NUM_WORKERS = 10  # Number of worker threads to handle uploads
SECONDS = 1  # Rate limiting period
OUTPUT_DIR = 'output_files'  # Directory where files are stored
BUCKET_NAME = 'testing-bucket-project'  # Name of your S3 bucket
S3_DIRECTORY = 'new_code/'  # Directory within the bucket to upload files

# Function to upload file to S3
def upload_file(file_path, s3_key):
    try:
        s3_client = boto3.client('s3',
                endpoint_url=ENDPOINT_URL,
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY)
        s3_client.upload_file(file_path, BUCKET_NAME, s3_key)
        print(f"Uploaded {file_path} to s3://{BUCKET_NAME}/{s3_key}")
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")

# Worker function for threads
def worker(upload_queue, rate_limiter):
    while True:
        item = upload_queue.get()
        if item is None:
            break
        file_path, s3_path = item
        rate_limiter()
        upload_file(file_path, s3_path)
        upload_queue.task_done()

# Rate limiter function
def create_rate_limiter(tps, period):
    interval = period / tps
    last_called = [time.time()]

    def rate_limiter():
        elapsed = time.time() - last_called[0]
        wait_time = interval - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        last_called[0] = time.time()

    return rate_limiter

# Main function to set up the queue and workers
def main():
    upload_queue = queue.Queue()
    rate_limiter = create_rate_limiter(RPS, SECONDS)

    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        print(f"Output directory '{OUTPUT_DIR}' does not exist.")
        return

    # Start worker threads
    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(upload_queue, rate_limiter))
        t.start()
        threads.append(t)

    # Traverse the directory and upload all files
    for root, _, files in os.walk(OUTPUT_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)
            s3_key = os.path.relpath(file_path, OUTPUT_DIR)
            s3_key = os.path.join(S3_DIRECTORY, s3_key)
            upload_queue.put((file_path, s3_key))

    # Wait for all tasks to be done
    upload_queue.join()

    # Stop workers
    for _ in range(NUM_WORKERS):
        upload_queue.put(None)
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
