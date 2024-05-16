import os
import threading
import time
import queue
import subprocess

# Configuration
RPS = 1  # Transactions per second limit
NUM_WORKERS = 2  # Number of worker threads to handle uploads
SECONDS = 1  # Rate limiting period
OUTPUT_DIR = 'output_files'  # Directory where files are stored
BUCKET_NAME = 'testing-bucket-project/test4'

# Function to execute s3cmd put
def upload_file(file_path, s3_path):
    try:
        result = subprocess.run(['s3cmd', 'put', file_path, s3_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Uploaded {file_path} to {s3_path}: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to upload {file_path}: {e.stderr}")

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
def create_rate_limiter(rps, period):
    interval = period / rps
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
            s3_path = f's3://{BUCKET_NAME}/{os.path.relpath(file_path, OUTPUT_DIR)}'
            upload_queue.put((file_path, s3_path))

        if os.path.exists(file_path):
            upload_queue.put((file_path, s3_path))
        else:
            print(f"File {file_path} does not exist. Skipping.")

    # Wait for all tasks to be done
    upload_queue.join()

    # Stop workers
    for _ in range(NUM_WORKERS):
        upload_queue.put(None)
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
