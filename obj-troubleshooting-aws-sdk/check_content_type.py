import boto3

# Initialize Linode Object Storage client
s3 = boto3.client('s3',
                  endpoint_url='https://jp-osa-1.linodeobjects.com',
                  aws_access_key_id='',
                  aws_secret_access_key='')

# Specify bucket name and object key
bucket_name = ''
object_key = ''

# Perform a HEAD request to retrieve metadata, including content type
response = s3.head_object(
    Bucket=bucket_name,
    Key=object_key
)

# Retrieve the content type from the response headers
content_type = response['ContentType']

print(f"Content type of the object '{object_key}' is: {content_type}")
