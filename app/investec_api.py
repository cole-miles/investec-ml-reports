import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
import time

load_dotenv()

CLIENT_ID = os.getenv("INVESTEC_CLIENT_ID")
CLIENT_SECRET = os.getenv("INVESTEC_CLIENT_SECRET")
API_KEY = os.getenv("INVESTEC_API_KEY")  # Get the API key from .env
API_URL = os.getenv("INVESTEC_API_URL", "https://openapi.investec.com")

def get_access_token():
    url = f"{API_URL}/identity/v2/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-api-key": API_KEY  # Include the API key here
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "accounts balances transactions"
    }

    # Debug print
    print("Attempting to get access token...")
    print(f"Using Client ID: {CLIENT_ID[:4]}..." if CLIENT_ID else "No Client ID found!")
    print(f"Using Client Secret: {CLIENT_SECRET[:4]}..." if CLIENT_SECRET else "No Client Secret found!")

    response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))

    # Debug print
    print(f"Token Response Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error Response: {response.text}")

    response.raise_for_status()
    token = response.json()["access_token"]
    print("Successfully got access token!")
    return token

def get_account_id(access_token):
    url = f"{API_URL}/za/pb/v1/accounts"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'x-api-key': API_KEY  # Include the API key here
    }

    # Debug print
    print("\nAttempting to get account ID...")
    print(f"Using token: {access_token[:10]}...")

    response = requests.get(url, headers=headers)

    # Debug print
    print(f"Account Response Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error Response: {response.text}")

    response.raise_for_status()
    return response.json()["data"]["accounts"][0]["accountId"]

def get_transactions(account_id, access_token):
    # Set date range for full history
    from_date = "2000-01-01"  # Or your account's actual opening date
    to_date = datetime.today().strftime("%Y-%m-%d")

    url = f"{API_URL}/za/pb/v1/accounts/{account_id}/transactions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": API_KEY
    }

    # Parameters for full history and DEBIT transactions
    base_params = {
        "type": "DEBIT",
        "fromDate": from_date,
        "toDate": to_date
    }

    # First, get total pages
    print("Fetching total number of pages...")
    first_page_params = {**base_params, "page": 1}
    response = requests.get(url, headers=headers, params=first_page_params)
    response.raise_for_status()
    total_pages = response.json()["data"].get("totalPages", 1)
    print(f"Total pages to fetch: {total_pages}")

    all_transactions = []

    # Use tqdm for progress bar
    with tqdm(total=total_pages, desc="Fetching pages") as pbar:
        for page in range(1, total_pages + 1):
            try:
                params = {**base_params, "page": page}
                response = requests.get(url, headers=headers, params=params)

                if response.status_code == 401:
                    print("\nToken expired, refreshing...")
                    access_token = get_access_token()
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = requests.get(url, headers=headers, params=params)

                response.raise_for_status()
                data = response.json()["data"]
                transactions = data.get("transactions", [])
                all_transactions.extend(transactions)

                pbar.update(1)
                pbar.set_postfix({"Transactions": len(all_transactions)})

                # Optional: small delay to avoid rate limits
                time.sleep(0.1)

            except Exception as e:
                print(f"\nError fetching page {page}: {str(e)}")
                raise

    print(f"\nFetched a total of {len(all_transactions)} transactions")
    return all_transactions

if __name__ == "__main__":
    try:
        token = get_access_token()
        account_id = get_account_id(token)
        print(f"\nFirst account ID: {account_id}")
        transactions = get_transactions(account_id, token)
        print("\nTransactions:", transactions)
    except Exception as e:
        print(f"\nError: {e}")