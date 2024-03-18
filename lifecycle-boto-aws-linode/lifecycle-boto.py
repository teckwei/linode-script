import boto3
from botocore.exceptions import NoCredentialsError

# Replace these with your Linode Object Storage credentials
access_key = '' #include your Linode Object Storage access key (Access Key)
secret_key = '' #include your Linode Object Storage access key (Secret Key)
endpoint_url = 'https://jp-osa-1.linodeobjects.com'  # Replace with your Linode Object Storage cluster URL
bucket_name = 'testing-bucket-project' #setup the bucket which require lifecycle policy

# Create an S3 client for Linode Object Storage
s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, endpoint_url=endpoint_url)

# Define the lifecycle configuration
lifecycle_configuration = {
    'Rules': [
        {
            'ID': 'DeleteOldObjectsRule',
            'Filter': {'Prefix': 'image/'},  # Apply the rule (image directory) to all objects in the bucket
            'Status': 'Enabled',
            'Expiration': {
                'Days': 30,  # Objects will be deleted after 30 days
            }
        }
    ]
}

# Set the lifecycle configuration for the bucket
s3_client.put_bucket_lifecycle_configuration(
    Bucket=bucket_name,
    LifecycleConfiguration=lifecycle_configuration
)

print(f"Lifecycle configuration set for bucket: {bucket_name}")


# Display the current lifecycle rules for the bucket
response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
lifecycle_rules = response.get('Rules', [])

print("\nCurrent Lifecycle Rules:")
for rule in lifecycle_rules:
    print(f"ID: {rule.get('ID')}")
    
    # Check if 'Filter' key exists
    filter_prefix = rule.get('Filter', {}).get('Prefix', 'All Objects')
    print(f"Filter Prefix: {filter_prefix}")
    
    print(f"Status: {rule.get('Status')}")
    print(f"Expiration Days: {rule['Expiration'].get('Days')}")
    print("--------------------------")
