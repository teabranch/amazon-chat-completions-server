# Files API Documentation

## Overview

The Amazon Chat Completions Server now includes OpenAI-compatible file management functionality through the `/v1/files` endpoint. This feature allows you to upload files to Amazon S3 for use with various AI services.

## Configuration

### Required Environment Variables

Add the following to your `.env` file:

```bash
# S3 Configuration for File Storage
S3_FILES_BUCKET=your-s3-bucket-name

# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# API Authentication
API_KEY=your-secret-api-key
```

### S3 Bucket Setup

1. Create an S3 bucket in your AWS account
2. Ensure your AWS credentials have the following permissions:
   - `s3:PutObject`
   - `s3:GetObject`  
   - `s3:DeleteObject`
   - `s3:ListBucket`

### CLI Configuration

You can use the built-in CLI to configure these settings:

```bash
uv run amazon-chat configure
```

## API Endpoints

### POST /v1/files

Upload a file to the server for use with AI services.

**Request Format:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Bearer token required

**Parameters:**
- `file` (required): The file to upload
- `purpose` (required): The intended use of the file (e.g., "fine-tune", "assistants", "batch")

**Example Request:**

```bash
curl -X POST http://localhost:8000/v1/files \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@training_data.jsonl" \
  -F "purpose=fine-tune"
```

**Example Response:**

```json
{
  "id": "file-abc123def456",
  "object": "file",
  "bytes": 1024,
  "created_at": 1613779657,
  "filename": "training_data.jsonl",
  "purpose": "fine-tune",
  "status": "uploaded"
}
```

### GET /v1/files/health

Check the health status of the files service.

**Example Request:**

```bash
curl http://localhost:8000/v1/files/health
```

**Example Response:**

```json
{
  "status": "healthy",
  "service": "files",
  "s3_bucket_configured": true,
  "aws_region": "us-east-1"
}
```

## File Storage

### S3 Key Structure

Files are stored in S3 with the following key pattern:
```
files/{file-id}-{original-filename}
```

Example: `files/file-abc123def456-training_data.jsonl`

### Metadata

Each uploaded file includes the following S3 metadata:
- `file_id`: Unique identifier
- `original_filename`: Original filename
- `purpose`: Specified purpose
- `uploaded_by`: "amazon-chat-completions-server"

## Usage Examples

### Python Example

```python
import requests

# Configuration
server_url = "http://localhost:8000"
api_key = "your-api-key"

# Upload a file
with open("training_data.jsonl", "rb") as f:
    response = requests.post(
        f"{server_url}/v1/files",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": f},
        data={"purpose": "fine-tune"}
    )

if response.status_code == 200:
    file_info = response.json()
    print(f"File uploaded: {file_info['id']}")
else:
    print(f"Upload failed: {response.text}")
```

### cURL Example

```bash
# Upload a file
curl -X POST http://localhost:8000/v1/files \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@sample.json" \
  -F "purpose=assistants"

# Check service health
curl http://localhost:8000/v1/files/health
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('purpose', 'fine-tune');

const response = await fetch('http://localhost:8000/v1/files', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-api-key'
  },
  body: formData
});

const result = await response.json();
console.log('Upload result:', result);
```

## Error Handling

### Common Error Responses

**400 Bad Request - Missing file:**
```json
{
  "error": {
    "message": "Missing required field: 'file'",
    "type": "api_error",
    "code": 400
  }
}
```

**400 Bad Request - Empty file:**
```json
{
  "error": {
    "message": "File is empty",
    "type": "api_error", 
    "code": 400
  }
}
```

**403 Forbidden - Invalid API key:**
```json
{
  "error": {
    "message": "Invalid API key",
    "type": "api_error",
    "code": 403
  }
}
```

**500 Internal Server Error - S3 configuration:**
```json
{
  "error": {
    "message": "S3_FILES_BUCKET is not configured. Cannot upload files.",
    "type": "api_error",
    "code": 500
  }
}
```

## OpenAI Compatibility

This implementation is fully compatible with OpenAI's file upload API, meaning you can:

1. Use existing OpenAI client libraries
2. Switch between OpenAI and this server without code changes
3. Maintain the same request/response format

### Supported File Purposes

- `fine-tune`: For fine-tuning models
- `assistants`: For assistant tools
- `batch`: For batch processing
- Custom purposes are also supported

## Security Considerations

1. **API Authentication**: All requests require a valid API key
2. **S3 Permissions**: Use principle of least privilege for S3 access
3. **File Validation**: Files are validated for basic requirements
4. **Secure Storage**: Files are stored securely in S3 with appropriate metadata

## Testing

Run the included tests to verify functionality:

```bash
# Run all file endpoint tests
uv run pytest tests/test_files_endpoint.py -v

# Run integration tests (requires AWS credentials)
uv run pytest tests/test_files_endpoint.py::TestFilesEndpointIntegration -v
```

## Troubleshooting

### Common Issues

1. **"S3_FILES_BUCKET is not set"**
   - Add `S3_FILES_BUCKET=your-bucket-name` to your `.env` file

2. **"Access denied to S3 bucket"**
   - Verify AWS credentials have proper S3 permissions
   - Check bucket policy and IAM roles

3. **"python-multipart" error**
   - Install: `uv add python-multipart`

4. **File upload fails**
   - Check file size limits
   - Verify S3 bucket exists and is accessible
   - Ensure proper AWS region configuration

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export LOG_LEVEL=DEBUG
uv run uvicorn src.open_amazon_chat_completions_server.api.app:app
``` 