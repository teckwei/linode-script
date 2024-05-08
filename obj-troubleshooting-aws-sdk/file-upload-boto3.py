import boto3

# Initialize Linode Object Storage client
s3 = boto3.client('s3',
                  endpoint_url='https://jp-osa-1.linodeobjects.com',
                  aws_access_key_id='',
                  aws_secret_access_key='')

# Specify bucket name and object key
bucket_name = ''
object_key = ''

# Specify file path
file_path = ''

# Upload file with content type application/octet-stream and set ACL to public-read
with open(file_path, 'rb') as file:
    s3.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=file,
        ContentType='application/octet-stream',
        ACL='public-read'
    )

print("File uploaded successfully with public read ACL!")