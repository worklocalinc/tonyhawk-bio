import requests
import json
import time
import sys
import os

# Cloudflare Global API credentials
CF_EMAIL = os.environ.get("CLOUDFLARE_EMAIL", "james@worklocal.ca")
CF_GLOBAL_API_KEY = os.environ.get("CLOUDFLARE_GLOBAL_API_KEY")

if not CF_GLOBAL_API_KEY:
    print("Please set CLOUDFLARE_GLOBAL_API_KEY environment variable")
    sys.exit(1)

DOMAIN = "tonyhawk.bio"

# Headers for global API
headers = {
    "X-Auth-Email": CF_EMAIL,
    "X-Auth-Key": CF_GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

def test_api_connection():
    """Test if API credentials are working"""
    print("Testing API connection...")
    
    # Add delay to avoid rate limiting
    time.sleep(2)
    
    url = "https://api.cloudflare.com/client/v4/user"
    response = requests.get(url, headers=headers)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        user_data = response.json()
        if user_data.get("success"):
            print(f"[SUCCESS] Connected as: {user_data['result']['email']}")
            return True
        else:
            print(f"[ERROR] API response not successful: {user_data}")
    elif response.status_code == 429:
        print("[ERROR] Rate limited (429). Please wait a few minutes before trying again.")
        print("Cloudflare typically rate limits at:")
        print("  - 1200 requests per 5 minutes")
        print("  - 10 requests per second")
    else:
        print(f"[ERROR] Failed to connect: {response.text}")
    
    return False

def wait_for_rate_limit():
    """Wait for rate limit to clear"""
    print("\nWaiting 60 seconds for rate limit to clear...")
    for i in range(60, 0, -10):
        print(f"  {i} seconds remaining...")
        time.sleep(10)
    print("Continuing...\n")

def check_existing_zone():
    """Check if zone already exists"""
    print(f"Checking if {DOMAIN} zone exists...")
    time.sleep(2)  # Delay to avoid rate limit
    
    url = f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("result"):
            zone = data["result"][0]
            print(f"[SUCCESS] Zone already exists!")
            print(f"Zone ID: {zone['id']}")
            print(f"Nameservers:")
            for ns in zone.get("name_servers", []):
                print(f"  - {ns}")
            return zone
    elif response.status_code == 429:
        print("[ERROR] Rate limited while checking zone")
        return None
    
    print("Zone does not exist yet")
    return None

def create_zone_with_retry():
    """Create zone with retry logic"""
    print(f"\nCreating zone for {DOMAIN}...")
    time.sleep(3)  # Extra delay before zone creation
    
    url = "https://api.cloudflare.com/client/v4/zones"
    data = {
        "name": DOMAIN,
        "jump_start": True
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        zone_data = response.json()["result"]
        print(f"[SUCCESS] Zone created!")
        return zone_data
    elif response.status_code == 429:
        print("[ERROR] Rate limited during zone creation")
        return None
    else:
        print(f"[ERROR] Failed to create zone: {response.text}")
        return None

def main():
    print(f"=== Cloudflare Zone Setup for {DOMAIN} ===\n")
    
    # Test connection first
    if not test_api_connection():
        print("\nAPI connection failed. Please check:")
        print("1. The global API key is correct")
        print("2. The email address is correct")
        print("3. You're not rate limited (wait a few minutes)")
        return
    
    # Check for existing zone
    zone = check_existing_zone()
    
    if not zone:
        # If rate limited, wait
        response = requests.get("https://api.cloudflare.com/client/v4/user", headers=headers)
        if response.status_code == 429:
            wait_for_rate_limit()
        
        # Try to create zone
        zone = create_zone_with_retry()
    
    if zone:
        print(f"\n=== Success! ===")
        print(f"Zone is ready for {DOMAIN}")
        print(f"\nNext steps:")
        print(f"1. Update NameSilo nameservers to:")
        for ns in zone.get("name_servers", []):
            print(f"   - {ns}")
        print(f"\n2. DNS records will be automatically configured")
        print(f"3. Your site will be available at https://{DOMAIN} after propagation")
    else:
        print(f"\n=== Rate Limited ===")
        print("Please wait 5-10 minutes and try again")
        print("You can also manually create the zone at:")
        print("https://dash.cloudflare.com/add-site")

if __name__ == "__main__":
    main()