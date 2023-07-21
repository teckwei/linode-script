#!/bin/bash

# Define the output directory
output_dir="output_files"

# Create the output directory if it doesn't exist
mkdir -p "$output_dir"

# Get the current date in the "YYYY-MM-DD" format
current_date=$(date +"%Y-%m-%d")

# Get the current date in the "YYYY-MM-DD" format
current_time=$(date +"%Y-%m-%d_%H-%M-%S")

# Define the output file name with the current date included
output_file="$output_dir/file_output_$current_time.pdf"

# Invoke the sysbench.sh script and capture its output in a variable
sysbench_output=$(./scenario-backup-2.sh)

# Redirect the output to the text file
echo "$sysbench_output" > "$output_file"

# Optionally, you can display a message indicating the success
echo "scenario-backup-2.sh result stored in $output_file."

# Upload the output file to Linode Object Storage (replace 'your-bucket-name' with your actual bucket name)
bucket_name="file-output-bucket"
s3cmd put "$output_file" "s3://$bucket_name/$current_date/$output_file"

# Set the public-read ACL for the uploaded object
s3cmd setacl "s3://$bucket_name/$current_date/$output_file" --acl-public

# Optionally, you can display a message indicating the upload success
echo "Output file uploaded to Linode Object Storage."