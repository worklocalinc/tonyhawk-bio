import requests
import json
import base64
import os
import sys
from pathlib import Path
import mimetypes

# Cloudflare API credentials
CF_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CF_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
if not CF_ACCOUNT_ID:
    print("Please set CLOUDFLARE_ACCOUNT_ID environment variable")
    sys.exit(1)
PROJECT_NAME = "tonyhawk-bio"

if not CF_API_TOKEN:
    print("Please set CLOUDFLARE_API_TOKEN environment variable")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
}

def create_pages_project():
    """Create or get existing Pages project"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects/{PROJECT_NAME}"
    
    # First try to get existing project
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Project {PROJECT_NAME} already exists")
        return response.json()["result"]
    
    # Create new project if doesn't exist
    create_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects"
    create_headers = headers.copy()
    create_headers["Content-Type"] = "application/json"
    
    data = {
        "name": PROJECT_NAME,
        "production_branch": "main"
    }
    
    response = requests.post(create_url, headers=create_headers, json=data)
    
    if response.status_code == 200:
        print(f"Created new project: {PROJECT_NAME}")
        return response.json()["result"]
    else:
        print(f"Error creating project: {response.text}")
        return None

def upload_files():
    """Upload all files to Cloudflare Pages"""
    # Create form data with all files
    files_to_upload = []
    
    # Get all files in the current directory
    for file_path in Path(".").iterdir():
        if file_path.is_file() and file_path.suffix not in ['.py', '.pyc']:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = 'application/octet-stream'
                
            with open(file_path, 'rb') as f:
                files_to_upload.append(
                    ('file', (file_path.name, f.read(), mime_type))
                )
                print(f"Preparing to upload: {file_path.name}")
    
    # Create deployment
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects/{PROJECT_NAME}/deployments"
    
    # Create manifest
    manifest = {
        "/index.html": "index.html",
        "/styles.css": "styles.css",
        "/tony-hawk-portrait.jpg": "tony-hawk-portrait.jpg",
        "/tony-hawk-900.jpg": "tony-hawk-900.jpg",
        "/tony-hawk-skatepark.jpg": "tony-hawk-skatepark.jpg"
    }
    
    files_to_upload.append(
        ('manifest', (None, json.dumps(manifest), 'application/json'))
    )
    
    response = requests.post(url, headers=headers, files=files_to_upload)
    
    if response.status_code in [200, 201]:
        deployment = response.json()["result"]
        print(f"\n[SUCCESS] Deployment successful!")
        print(f"Deployment ID: {deployment['id']}")
        print(f"URL: https://{deployment['url']}")
        return deployment
    else:
        print(f"Error deploying: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    print("Deploying tonyhawk.bio to Cloudflare Pages...\n")
    
    # Change to project directory
    os.chdir("C:/workspace/tonyhawk-bio")
    
    # Create or get project
    project = create_pages_project()
    if not project:
        print("Failed to create/get project")
        return
    
    # Upload files
    print("\nUploading files...")
    deployment = upload_files()
    
    if deployment:
        print("\n=== Deployment Complete! ===")
        print(f"Your site is now live at:")
        print(f"  - https://{PROJECT_NAME}.pages.dev")
        print(f"\nTo connect your custom domain (tonyhawk.bio):")
        print(f"1. First add tonyhawk.bio to Cloudflare (requires zone creation permissions)")
        print(f"2. Then go to the Pages project settings to add the custom domain")
    else:
        print("\nDeployment failed. Please check the error messages above.")

if __name__ == "__main__":
    main()