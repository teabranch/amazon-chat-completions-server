#!/usr/bin/env python3
"""
Enhanced File Upload and Query Example

This script demonstrates the complete workflow of:
1. Uploading various file types
2. Listing and managing files
3. Using files in chat completions for analysis
4. File processing and content extraction
"""

import json
import requests
import tempfile
import os
import csv
from typing import List, Dict, Any
import time

class FileQueryExample:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "test-key"):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.uploaded_files: List[Dict[str, Any]] = []
    
    def check_files_health(self) -> bool:
        """Check if the files service is healthy."""
        try:
            response = requests.get(f"{self.base_url}/v1/files/health")
            health = response.json()
            print(f"🔍 Files service health: {health['status']}")
            print(f"   S3 configured: {health.get('s3_configured', False)}")
            return health['status'] == 'healthy'
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def create_sample_files(self) -> Dict[str, str]:
        """Create sample files of different types for testing."""
        files = {}
        
        # Create a text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""Market Analysis Report Q4 2024

Executive Summary:
- Revenue increased by 15% compared to Q3
- Customer acquisition up 23%
- Product launches in 3 new markets
- Customer satisfaction score: 4.7/5.0

Key Findings:
1. Mobile app usage increased 45%
2. Premium subscriptions grew 30%
3. Support ticket resolution improved 25%

Recommendations:
- Expand mobile features
- Increase premium marketing
- Scale support team
""")
            files['report.txt'] = f.name
        
        # Create a CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Product', 'Units_Sold', 'Revenue', 'Region'])
            writer.writerow(['2024-01-01', 'Widget A', '150', '4500.00', 'North'])
            writer.writerow(['2024-01-01', 'Widget B', '89', '3560.00', 'South']) 
            writer.writerow(['2024-01-02', 'Widget A', '167', '5010.00', 'North'])
            writer.writerow(['2024-01-02', 'Widget C', '203', '8120.00', 'East'])
            writer.writerow(['2024-01-03', 'Widget B', '145', '5800.00', 'West'])
            files['sales_data.csv'] = f.name
        
        # Create a JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {
                "company": "TechCorp",
                "year": 2024,
                "departments": {
                    "engineering": {
                        "employees": 45,
                        "budget": 2500000,
                        "projects": ["AI Platform", "Mobile App", "API Gateway"]
                    },
                    "sales": {
                        "employees": 23,
                        "budget": 800000,
                        "targets": {
                            "q1": 1200000,
                            "q2": 1350000,
                            "q3": 1400000,
                            "q4": 1500000
                        }
                    },
                    "marketing": {
                        "employees": 12,
                        "budget": 600000,
                        "campaigns": ["Social Media", "Content Marketing", "SEO"]
                    }
                },
                "metrics": {
                    "revenue": 15600000,
                    "customers": 2340,
                    "growth_rate": 0.23
                }
            }
            json.dump(data, f, indent=2)
            files['company_data.json'] = f.name
        
        # Create an HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Product Launch Report</title>
</head>
<body>
    <h1>New Product Launch Analysis</h1>
    
    <h2>Product Overview</h2>
    <p>Our latest product, <strong>SuperWidget Pro</strong>, was launched on October 15, 2024.</p>
    
    <h2>Launch Metrics</h2>
    <ul>
        <li>First week sales: 1,250 units</li>
        <li>Customer rating: 4.8/5 stars</li>
        <li>Social media mentions: 15,000+</li>
        <li>Website traffic increase: 340%</li>
    </ul>
    
    <h2>Customer Feedback</h2>
    <p>Customers particularly praised the improved battery life and user-friendly interface.</p>
    
    <h2>Next Steps</h2>
    <p>Based on the positive response, we recommend increasing production capacity by 50%.</p>
</body>
</html>""")
            files['launch_report.html'] = f.name
        
        return files
    
    def upload_file(self, file_path: str, purpose: str = "assistants") -> Dict[str, Any]:
        """Upload a file to the server."""
        filename = os.path.basename(file_path)
        print(f"📤 Uploading {filename}...")
        
        try:
            with open(file_path, 'rb') as f:
                files = {"file": (filename, f)}
                data = {"purpose": purpose}
                
                response = requests.post(
                    f"{self.base_url}/v1/files",
                    headers=self.headers,
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    file_info = response.json()
                    print(f"   ✅ Uploaded: {file_info['id']} ({file_info['bytes']} bytes)")
                    self.uploaded_files.append(file_info)
                    return file_info
                else:
                    print(f"   ❌ Upload failed: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            return {}
    
    def list_files(self, purpose: str = None) -> List[Dict[str, Any]]:
        """List uploaded files."""
        print(f"📋 Listing files{f' (purpose: {purpose})' if purpose else ''}...")
        
        try:
            params = {}
            if purpose:
                params['purpose'] = purpose
            
            response = requests.get(
                f"{self.base_url}/v1/files",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('data', [])
                print(f"   Found {len(files)} files:")
                for file_info in files:
                    print(f"   - {file_info['filename']} ({file_info['id']}) - {file_info['bytes']} bytes")
                return files
            else:
                print(f"   ❌ List failed: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"   ❌ List error: {e}")
            return []
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a specific file."""
        print(f"📊 Getting metadata for {file_id}...")
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/files/{file_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                metadata = response.json()
                print(f"   ✅ File: {metadata['filename']} ({metadata['bytes']} bytes, {metadata['purpose']})")
                return metadata
            else:
                print(f"   ❌ Get metadata failed: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"   ❌ Get metadata error: {e}")
            return {}
    
    def download_file_content(self, file_id: str) -> bytes:
        """Download file content."""
        print(f"⬇️ Downloading content for {file_id}...")
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/files/{file_id}/content",
                headers=self.headers
            )
            
            if response.status_code == 200:
                content = response.content
                print(f"   ✅ Downloaded {len(content)} bytes")
                return content
            else:
                print(f"   ❌ Download failed: {response.status_code} - {response.text}")
                return b""
        except Exception as e:
            print(f"   ❌ Download error: {e}")
            return b""
    
    def chat_with_files(self, message: str, file_ids: List[str], model: str = "claude-3-sonnet") -> str:
        """Send a chat completion request with file context."""
        print(f"💬 Chat with {len(file_ids)} files: '{message[:50]}{'...' if len(message) > 50 else ''}'")
        
        try:
            request_data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": message}
                ],
                "file_ids": file_ids,
                "temperature": 0.3
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data["choices"][0]["message"]["content"]
                print(f"   ✅ Response received ({len(assistant_message)} characters)")
                return assistant_message
            else:
                print(f"   ❌ Chat failed: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"   ❌ Chat error: {e}")
            return ""
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file."""
        print(f"🗑️ Deleting {file_id}...")
        
        try:
            response = requests.delete(
                f"{self.base_url}/v1/files/{file_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                print(f"   ✅ Deleted successfully")
                return True
            else:
                print(f"   ❌ Delete failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Delete error: {e}")
            return False
    
    def cleanup_files(self):
        """Clean up temporary files."""
        for file_path in getattr(self, '_temp_files', []):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file {file_path}: {e}")
    
    def run_demo(self):
        """Run the complete demonstration."""
        print("🚀 Starting File Upload and Query Demo")
        print("=" * 50)
        
        # Check service health
        if not self.check_files_health():
            print("❌ Files service is not healthy. Please check configuration.")
            return
        
        print()
        
        # Create sample files
        print("📁 Creating sample files...")
        sample_files = self.create_sample_files()
        self._temp_files = list(sample_files.values())
        
        # Upload files
        print("\n📤 Uploading files...")
        file_ids = []
        for file_type, file_path in sample_files.items():
            file_info = self.upload_file(file_path, purpose="assistants")
            if file_info:
                file_ids.append(file_info['id'])
        
        if not file_ids:
            print("❌ No files uploaded successfully")
            return
        
        print()
        
        # List files
        self.list_files()
        print()
        
        # Get metadata for first file
        if file_ids:
            self.get_file_metadata(file_ids[0])
            print()
        
        # Demo different types of queries
        queries = [
            {
                "message": "Analyze the sales data and provide key insights about product performance and regional trends.",
                "files": [id for id in file_ids if 'csv' in str(id)][:1] if any('csv' in str(id) for id in file_ids) else file_ids[:1],
                "description": "Sales Data Analysis"
            },
            {
                "message": "Summarize the company structure and financial information from the uploaded data.",
                "files": [id for id in file_ids if 'json' in str(id)][:1] if any('json' in str(id) for id in file_ids) else file_ids[:1],
                "description": "Company Data Summary"
            },
            {
                "message": "Create an executive summary that combines insights from all uploaded documents.",
                "files": file_ids,
                "description": "Multi-Document Analysis"
            },
            {
                "message": "What are the main recommendations across all the reports?",
                "files": file_ids[:2],  # Use first 2 files
                "description": "Recommendations Extraction"
            }
        ]
        
        print("💬 Running chat completion demos...")
        for i, query in enumerate(queries, 1):
            print(f"\n--- Demo {i}: {query['description']} ---")
            response = self.chat_with_files(
                query['message'], 
                query['files']
            )
            
            if response:
                print(f"\n📝 Response:\n{response[:500]}{'...' if len(response) > 500 else ''}\n")
            
            # Brief pause between requests
            time.sleep(1)
        
        # Demonstrate file management
        print("\n🔧 File Management Demo...")
        
        # Download content example
        if file_ids:
            content = self.download_file_content(file_ids[0])
            if content:
                print(f"   Sample content: {content[:100].decode('utf-8', errors='ignore')}...")
        
        print()
        
        # Clean up - delete uploaded files
        print("🧹 Cleaning up uploaded files...")
        for file_id in file_ids:
            self.delete_file(file_id)
        
        # Clean up temp files
        self.cleanup_files()
        
        print("\n✅ Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- File upload with multiple formats (TXT, CSV, JSON, HTML)")
        print("- File listing and metadata retrieval") 
        print("- File content download")
        print("- Chat completions with file context")
        print("- Automatic file processing and text extraction")
        print("- Multi-document analysis")
        print("- File deletion and cleanup")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="File Upload and Query Demo")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL of the server")
    parser.add_argument("--api-key", default="test-key",
                       help="API key for authentication")
    
    args = parser.parse_args()
    
    demo = FileQueryExample(args.base_url, args.api_key)
    demo.run_demo()

if __name__ == "__main__":
    main() 