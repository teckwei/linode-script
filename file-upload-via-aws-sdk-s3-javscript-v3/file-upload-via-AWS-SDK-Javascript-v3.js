const { S3Client, PutObjectCommand } = require("@aws-sdk/client-s3");
const fs = require("fs");
const path = require("path");
const util = require("util");

// Promisify fs functions
const readdir = util.promisify(fs.readdir);
const stat = util.promisify(fs.stat);
const readFile = util.promisify(fs.readFile);

// Configure AWS SDK with Linode Object Storage endpoint
const s3Client = new S3Client({
  region: 'jp-osa-1', // Replace with your region
  endpoint: 'https://jp-osa-1.linodeobjects.com', // Replace with your Linode region
  credentials: {
    accessKeyId: 'your-access-key', // Replace with your Linode access key
    secretAccessKey: 'your-secret-key' // Replace with your Linode secret key
  },
  forcePathStyle: true // Needed for Linode Object Storage
});

// Specify the bucket name and the directory you want to upload
const bucketName = 'your-bucket-name'; // Replace with your bucket name
const directoryPath = 'your-file-directory'; // Replace with the path to your directory

// Function to upload a single file
const uploadFile = async (filePath) => {
  const fileContent = await readFile(filePath);
  const relativePath = path.relative(directoryPath, filePath);
  const params = {
    Bucket: bucketName,
    Key: relativePath,
    Body: fileContent,
    ACL: 'public-read' // Set appropriate permissions
  };

  try {
    const command = new PutObjectCommand(params);
    const data = await s3Client.send(command);
    console.log(`File uploaded successfully. ${relativePath}`);
  } catch (err) {
    console.error('Error uploading file:', err);
  }
};

// Function to recursively upload a directory
const uploadDirectory = async (dir) => {
  const files = await readdir(dir);

  for (const file of files) {
    const filePath = path.join(dir, file);
    const fileStat = await stat(filePath);

    if (fileStat.isDirectory()) {
      await uploadDirectory(filePath);
    } else {
      await uploadFile(filePath);
    }
  }
};

// Start the upload process
uploadDirectory(directoryPath).then(() => {
  console.log('All files uploaded successfully.');
}).catch((err) => {
  console.error('Error uploading directory:', err);
});
