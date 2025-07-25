import requests
import json
import os
import sys

# Cloudflare API credentials
CF_API_TOKEN = "QrhAZCVDEgztycifIx8tKlU03WmWxn6MVYrKdjcO"
CF_ACCOUNT_ID = None  # We'll fetch this

headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_account_id():
    """Get the Cloudflare account ID"""
    url = "https://api.cloudflare.com/client/v4/accounts"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data["result"]:
            account_id = data["result"][0]["id"]
            print(f"Found account ID: {account_id}")
            return account_id
    else:
        print(f"Error getting account: {response.text}")
        return None

def create_cloudflare_zone(domain):
    """Create a new zone in Cloudflare"""
    url = "https://api.cloudflare.com/client/v4/zones"
    
    data = {
        "name": domain,
        "account": {
            "id": CF_ACCOUNT_ID
        },
        "jump_start": True
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        zone_data = response.json()["result"]
        print(f"Zone created successfully!")
        print(f"Zone ID: {zone_data['id']}")
        print(f"\nNameservers to add to NameSilo:")
        for ns in zone_data["name_servers"]:
            print(f"  - {ns}")
        return zone_data
    else:
        error_data = response.json()
        if "errors" in error_data and error_data["errors"]:
            if error_data["errors"][0]["code"] == 1061:
                print("Zone already exists. Fetching existing zone...")
                # Get existing zone
                zones_response = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={domain}", headers=headers)
                if zones_response.status_code == 200:
                    zones = zones_response.json()["result"]
                    if zones:
                        return zones[0]
        print(f"Error creating zone: {response.text}")
        return None

def create_pages_project(project_name):
    """Create a Cloudflare Pages project"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects"
    
    data = {
        "name": project_name,
        "production_branch": "main"
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        project_data = response.json()["result"]
        print(f"\nPages project created!")
        print(f"Project name: {project_data['name']}")
        print(f"Project subdomain: {project_data['subdomain']}")
        return project_data
    else:
        error_data = response.json()
        if "errors" in error_data and error_data["errors"]:
            if "already exists" in str(error_data["errors"][0]):
                print(f"Project {project_name} already exists")
                return {"name": project_name, "subdomain": project_name}
        print(f"Error creating Pages project: {response.text}")
        return None

def main():
    global CF_ACCOUNT_ID
    
    print("Setting up tonyhawk.bio on Cloudflare...\n")
    
    # Get account ID
    CF_ACCOUNT_ID = get_account_id()
    if not CF_ACCOUNT_ID:
        print("Failed to get account ID")
        return
    
    # Create zone
    print("\n1. Creating Cloudflare zone...")
    zone = create_cloudflare_zone("tonyhawk.bio")
    if not zone:
        print("Failed to create zone")
        return
    
    # Create Pages project
    print("\n2. Creating Pages project...")
    project = create_pages_project("tonyhawk-bio")
    if not project:
        print("Failed to create Pages project")
        return
    
    print("\n=== Next Steps ===")
    print("1. Add these nameservers to your NameSilo domain:")
    if zone and "name_servers" in zone:
        for ns in zone["name_servers"]:
            print(f"   - {ns}")
    
    print(f"\n2. Your site will be available at:")
    print(f"   - https://tonyhawk-bio.pages.dev (immediately)")
    print(f"   - https://tonyhawk.bio (after DNS propagation)")
    
    print("\n3. To deploy your site, run:")
    print("   npm install -g wrangler")
    print("   wrangler pages deploy . --project-name=tonyhawk-bio")

if __name__ == "__main__":
    main()