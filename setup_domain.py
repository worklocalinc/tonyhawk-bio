import requests
import json
import time
import xml.etree.ElementTree as ET
import os
import sys

# API Credentials
NAMESILO_API_KEY = os.environ.get("NAMESILO_API_KEY")
CLOUDFLARE_API_KEY = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

if not all([NAMESILO_API_KEY, CLOUDFLARE_API_KEY]):
    print("Please set NAMESILO_API_KEY and CLOUDFLARE_API_TOKEN environment variables")
    sys.exit(1)

DOMAIN = "tonyhawk.bio"

def get_cloudflare_zone_token():
    """Try to get a Cloudflare token with zone creation permissions"""
    # Check if we can create zones with current token
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try to list zones first
    response = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers)
    if response.status_code == 200:
        print("Current Cloudflare token has zone read permissions")
        return CLOUDFLARE_API_KEY
    else:
        print("Current token cannot access zones")
        return None

def update_namesilo_nameservers(domain, nameservers):
    """Update nameservers for a domain on NameSilo"""
    # First, get current nameservers
    url = f"https://www.namesilo.com/api/listDomains"
    params = {
        "version": "1",
        "type": "xml",
        "key": NAMESILO_API_KEY
    }
    
    response = requests.get(url, params=params)
    print(f"NameSilo list domains response: {response.status_code}")
    
    # Check if domain exists
    url = f"https://www.namesilo.com/api/getDomainInfo"
    params = {
        "version": "1",
        "type": "xml",
        "key": NAMESILO_API_KEY,
        "domain": domain
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print(f"Domain {domain} found on NameSilo")
        
        # Parse XML response
        root = ET.fromstring(response.text)
        code = root.find('.//code')
        
        if code is not None and code.text == "300":
            print("Domain info retrieved successfully")
            
            # Update nameservers
            ns_url = f"https://www.namesilo.com/api/changeNameServers"
            ns_params = {
                "version": "1",
                "type": "xml",
                "key": NAMESILO_API_KEY,
                "domain": domain,
                "ns1": nameservers[0],
                "ns2": nameservers[1]
            }
            
            ns_response = requests.get(ns_url, params=ns_params)
            ns_root = ET.fromstring(ns_response.text)
            ns_code = ns_root.find('.//code')
            
            if ns_code is not None and ns_code.text == "300":
                print(f"Successfully updated nameservers for {domain}")
                return True
            else:
                detail = ns_root.find('.//detail')
                print(f"Failed to update nameservers: {detail.text if detail is not None else 'Unknown error'}")
        else:
            detail = root.find('.//detail')
            print(f"Failed to get domain info: {detail.text if detail is not None else 'Unknown error'}")
    else:
        print(f"Error accessing NameSilo API: {response.status_code}")
    
    return False

def create_cloudflare_zone_alternative():
    """Try alternative method to create zone"""
    print("\nAttempting to create Cloudflare zone...")
    
    # First check if we need to use email + global API key instead
    # The token might need different permissions
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Check current user permissions
    user_response = requests.get("https://api.cloudflare.com/client/v4/user", headers=headers)
    if user_response.status_code == 200:
        print("API token is valid")
        user_data = user_response.json()
        
        # Try to get account details
        account_response = requests.get(f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}", headers=headers)
        if account_response.status_code == 200:
            print(f"Account access confirmed")
            
            # Check if zone already exists
            zones_response = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}", headers=headers)
            if zones_response.status_code == 200:
                zones = zones_response.json()["result"]
                if zones:
                    print(f"Zone {DOMAIN} already exists!")
                    return zones[0]
            
            print(f"\nZone creation requires additional permissions.")
            print("Please add the zone manually through Cloudflare dashboard:")
            print(f"1. Go to https://dash.cloudflare.com")
            print(f"2. Click 'Add a Site'")
            print(f"3. Enter: {DOMAIN}")
            print(f"4. Select the Free plan")
            print(f"5. Note the nameservers provided")
            
            return None

def connect_domain_to_pages():
    """Connect custom domain to Pages project"""
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Add custom domain to Pages project
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/pages/projects/tonyhawk-bio/domains"
    
    data = {
        "name": DOMAIN
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code in [200, 201]:
        print(f"\nSuccessfully connected {DOMAIN} to Pages project!")
        return True
    else:
        error_data = response.json()
        if "errors" in error_data:
            for error in error_data["errors"]:
                if error.get("code") == 8000013:
                    print(f"\nNote: {DOMAIN} needs to be added to Cloudflare first")
                else:
                    print(f"Error: {error.get('message', 'Unknown error')}")
        return False

def main():
    print(f"Setting up {DOMAIN} with Cloudflare and NameSilo...\n")
    
    # Step 1: Try to create Cloudflare zone
    zone = create_cloudflare_zone_alternative()
    
    if zone and "name_servers" in zone:
        # Step 2: Update NameSilo nameservers
        print(f"\nUpdating NameSilo nameservers...")
        success = update_namesilo_nameservers(DOMAIN, zone["name_servers"])
        
        if success:
            print(f"\nNameservers updated! DNS propagation may take up to 48 hours.")
    
    # Step 3: Try to connect domain to Pages
    print(f"\nAttempting to connect {DOMAIN} to Pages project...")
    connect_domain_to_pages()
    
    print(f"\n=== Summary ===")
    print(f"Website is live at: https://tonyhawk-bio.pages.dev")
    print(f"\nTo complete custom domain setup:")
    print(f"1. Add {DOMAIN} to your Cloudflare account manually")
    print(f"2. Update nameservers on NameSilo (if not done automatically)")
    print(f"3. In Cloudflare Pages, add {DOMAIN} as custom domain")
    print(f"\nThe Cloudflare API token needs 'Zone:Zone:Edit' permission to create zones automatically.")

if __name__ == "__main__":
    main()