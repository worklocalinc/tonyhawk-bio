import requests
import json
import time
import os
import sys

# Cloudflare Global API credentials
CF_EMAIL = os.environ.get("CLOUDFLARE_EMAIL", "james@worklocal.ca")
CF_GLOBAL_API_KEY = os.environ.get("CLOUDFLARE_GLOBAL_API_KEY")
NAMESILO_API_KEY = os.environ.get("NAMESILO_API_KEY")

if not all([CF_GLOBAL_API_KEY, NAMESILO_API_KEY]):
    print("Please set CLOUDFLARE_GLOBAL_API_KEY and NAMESILO_API_KEY environment variables")
    sys.exit(1)

DOMAIN = "tonyhawk.bio"

# Headers for global API
headers = {
    "X-Auth-Email": CF_EMAIL,
    "X-Auth-Key": CF_GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

def create_cloudflare_zone():
    """Create a new zone in Cloudflare using global API"""
    print(f"Creating Cloudflare zone for {DOMAIN}...")
    
    url = "https://api.cloudflare.com/client/v4/zones"
    
    data = {
        "name": DOMAIN,
        "jump_start": True  # Auto-scan for DNS records
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        zone_data = response.json()["result"]
        print(f"[SUCCESS] Zone created successfully!")
        print(f"Zone ID: {zone_data['id']}")
        print(f"\nNameservers to configure:")
        for ns in zone_data["name_servers"]:
            print(f"  - {ns}")
        return zone_data
    else:
        error_data = response.json()
        if "errors" in error_data and error_data["errors"]:
            if error_data["errors"][0]["code"] == 1061:
                print("Zone already exists. Fetching existing zone...")
                # Get existing zone
                zones_response = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}", headers=headers)
                if zones_response.status_code == 200:
                    zones = zones_response.json()["result"]
                    if zones:
                        zone = zones[0]
                        print(f"Found existing zone: {zone['id']}")
                        print(f"\nNameservers:")
                        for ns in zone["name_servers"]:
                            print(f"  - {ns}")
                        return zone
        print(f"Error: {response.text}")
        return None

def update_namesilo_nameservers(nameservers):
    """Update NameSilo nameservers"""
    import xml.etree.ElementTree as ET
    
    print(f"\nUpdating NameSilo nameservers for {DOMAIN}...")
    
    # Change nameservers
    url = f"https://www.namesilo.com/api/changeNameServers"
    params = {
        "version": "1",
        "type": "xml",
        "key": NAMESILO_API_KEY,
        "domain": DOMAIN,
        "ns1": nameservers[0],
        "ns2": nameservers[1]
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        root = ET.fromstring(response.text)
        code = root.find('.//code')
        
        if code is not None and code.text == "300":
            print("[SUCCESS] Nameservers updated successfully!")
            return True
        else:
            detail = root.find('.//detail')
            error_msg = detail.text if detail is not None else 'Unknown error'
            print(f"[ERROR] Failed to update nameservers: {error_msg}")
            
            # If domain doesn't exist in NameSilo, that's worth noting
            if "not found" in error_msg.lower():
                print(f"\nNote: {DOMAIN} may not be registered in NameSilo yet.")
                print("Please ensure the domain is registered before updating nameservers.")
    else:
        print(f"[ERROR] NameSilo API error: {response.status_code}")
    
    return False

def add_dns_records(zone_id):
    """Add DNS records for Pages"""
    print(f"\nAdding DNS records...")
    
    # Add CNAME for www
    cname_data = {
        "type": "CNAME",
        "name": "www",
        "content": "tonyhawk-bio.pages.dev",
        "ttl": 1,  # Auto
        "proxied": True
    }
    
    cname_response = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        headers=headers,
        json=cname_data
    )
    
    if cname_response.status_code == 200:
        print("[SUCCESS] Added www CNAME record")
    else:
        print(f"[INFO] www record may already exist: {cname_response.json().get('errors', [])}")
    
    # Add root domain CNAME (using CNAME flattening)
    root_data = {
        "type": "CNAME",
        "name": "@",
        "content": "tonyhawk-bio.pages.dev",
        "ttl": 1,
        "proxied": True
    }
    
    root_response = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        headers=headers,
        json=root_data
    )
    
    if root_response.status_code == 200:
        print("[SUCCESS] Added root domain CNAME record")
    else:
        print(f"[INFO] Root record may already exist: {root_response.json().get('errors', [])}")

def connect_pages_custom_domain():
    """Connect custom domain to Pages project"""
    # First get account ID
    accounts_response = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
    if accounts_response.status_code == 200:
        account_id = accounts_response.json()["result"][0]["id"]
        
        # Use token API for Pages (global API doesn't work well with Pages)
        token_headers = {
            "Authorization": f"Bearer QrhAZCVDEgztycifIx8tKlU03WmWxn6MVYrKdjcO",
            "Content-Type": "application/json"
        }
        
        # Add custom domain
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/tonyhawk-bio/domains"
        
        for domain_variant in [DOMAIN, f"www.{DOMAIN}"]:
            data = {"name": domain_variant}
            response = requests.post(url, headers=token_headers, json=data)
            
            if response.status_code in [200, 201]:
                print(f"[SUCCESS] Connected {domain_variant} to Pages project")
            else:
                error = response.json()
                if "already exists" in str(error):
                    print(f"[INFO] {domain_variant} already connected")
                else:
                    print(f"[INFO] {domain_variant}: {error.get('errors', [])}")

def main():
    print(f"=== Setting up {DOMAIN} with Cloudflare Global API ===\n")
    
    # Step 1: Create zone
    zone = create_cloudflare_zone()
    if not zone:
        print("\nFailed to create/retrieve zone. Exiting.")
        return
    
    zone_id = zone["id"]
    nameservers = zone["name_servers"]
    
    # Step 2: Update NameSilo nameservers
    update_namesilo_nameservers(nameservers)
    
    # Step 3: Add DNS records
    add_dns_records(zone_id)
    
    # Step 4: Connect to Pages
    print("\nConnecting domain to Pages project...")
    connect_pages_custom_domain()
    
    print(f"\n=== Setup Complete! ===")
    print(f"\nYour site will be available at:")
    print(f"  - https://tonyhawk-bio.pages.dev (already live)")
    print(f"  - https://tonyhawk.bio (after DNS propagation)")
    print(f"  - https://www.tonyhawk.bio (after DNS propagation)")
    print(f"\nDNS propagation typically takes 5-30 minutes but can take up to 48 hours.")
    print(f"\nCloudflare Dashboard: https://dash.cloudflare.com/?to=/:account/{zone['account']['id']}/domains")

if __name__ == "__main__":
    main()