#!/usr/bin/env python3
"""
Example script demonstrating how to use the /v1/files endpoint
for uploading files to the Amazon Chat Completions Server.

This script shows how to upload files in an OpenAI-compatible way.
"""

import requests
import json
import os
from pathlib import Path


def upload_file_example():
    """Example of uploading a file to the /v1/files endpoint."""
    
    # Configuration
    server_url = os.getenv("CHAT_SERVER_URL", "http://localhost:8000")
    api_key = os.getenv("CHAT_API_KEY", "your-secret-api-key")
    
    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Create a sample JSON file for fine-tuning
    sample_data = [
        {"prompt": "What is the capital of France?", "completion": "The capital of France is Paris."},
        {"prompt": "What is 2 + 2?", "completion": "2 + 2 equals 4."},
        {"prompt": "Who wrote Romeo and Juliet?", "completion": "William Shakespeare wrote Romeo and Juliet."}
    ]
    
    # Create temporary file
    temp_file = Path("sample_training_data.jsonl")
    with open(temp_file, "w") as f:
        for item in sample_data:
            f.write(json.dumps(item) + "\n")
    
    try:
        print(f"Uploading file to {server_url}/v1/files...")
        
        # Prepare the file upload
        with open(temp_file, "rb") as f:
            files = {
                "file": (temp_file.name, f, "application/jsonl")
            }
            data = {
                "purpose": "fine-tune"
            }
            
            # Make the upload request
            response = requests.post(
                f"{server_url}/v1/files",
                headers=headers,
                files=files,
                data=data
            )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("✅ File uploaded successfully!")
            print(f"File ID: {result['id']}")
            print(f"Filename: {result['filename']}")
            print(f"Purpose: {result['purpose']}")
            print(f"Size: {result['bytes']} bytes")
            print(f"Status: {result['status']}")
            print(f"Created at: {result['created_at']}")
            
            return result['id']
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()


def check_files_health():
    """Check the health of the files service."""
    server_url = os.getenv("CHAT_SERVER_URL", "http://localhost:8000")
    
    try:
        print(f"Checking files service health at {server_url}/v1/files/health...")
        
        response = requests.get(f"{server_url}/v1/files/health")
        
        if response.status_code == 200:
            result = response.json()
            print("📊 Files Service Health:")
            print(f"Status: {result['status']}")
            print(f"S3 Bucket Configured: {result['s3_bucket_configured']}")
            print(f"AWS Region: {result.get('aws_region', 'Not specified')}")
            
            if result['status'] == 'healthy' and result['s3_bucket_configured']:
                print("✅ Files service is ready for uploads!")
            else:
                print("⚠️  Files service may not be fully configured.")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during health check: {e}")


def main():
    """Main function to run the examples."""
    print("🚀 Amazon Chat Completions Server - File Upload Example")
    print("=" * 60)
    
    # Check service health first
    check_files_health()
    print()
    
    # Upload a file
    file_id = upload_file_example()
    
    if file_id:
        print(f"\n🎉 Success! Your file ID is: {file_id}")
        print("You can now use this file ID with other OpenAI-compatible endpoints.")
    else:
        print("\n💡 Tips for troubleshooting:")
        print("1. Make sure the server is running (uvicorn src.open_amazon_chat_completions_server.api.app:app)")
        print("2. Check that S3_FILES_BUCKET is configured in your .env file")
        print("3. Verify AWS credentials are properly set up")
        print("4. Ensure the API_KEY matches between client and server")


if __name__ == "__main__":
    main() 