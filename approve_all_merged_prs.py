#!/usr/bin/env python3
"""Approve all merged PRs in dcoya/nemo that lack approval."""

import requests
import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.environ["BITBUCKET_USERNAME"]
TOKEN = os.environ["BITBUCKET_API_TOKEN_WRITE"]
REPO = "dcoya/nemo"
BASE_URL = f"https://api.bitbucket.org/2.0/repositories/{REPO}"
AUTH = (USERNAME, TOKEN)

approved_count = 0
skipped_count = 0
failed_count = 0
already_approved = 0
total_processed = 0

url = f"{BASE_URL}/pullrequests?state=MERGED&pagelen=50"
page = 0

while url:
    page += 1
    print(f"\n--- Page {page} ---")
    resp = requests.get(url, auth=AUTH)
    if resp.status_code != 200:
        print(f"Error fetching PRs: {resp.status_code} {resp.text}")
        break

    data = resp.json()
    prs = data.get("values", [])

    for pr in prs:
        pr_id = pr["id"]
        title = pr["title"][:60]
        total_processed += 1

        # Check if already approved by anyone
        participants = pr.get("participants", [])
        has_my_approval = any(
            p.get("approved") and p.get("user", {}).get("account_id") == "712020:bd8d8776-13eb-45f7-8b2f-18149860ec0f"
            for p in participants
        )

        if has_my_approval:
            already_approved += 1
            continue

        # Approve
        approve_url = f"{BASE_URL}/pullrequests/{pr_id}/approve"
        r = requests.post(approve_url, auth=AUTH)

        if r.status_code == 200:
            approved_count += 1
            print(f"  ✓ #{pr_id}: {title}")
        elif r.status_code == 409:
            # Already approved
            already_approved += 1
        else:
            failed_count += 1
            print(f"  ✗ #{pr_id}: {r.status_code} - {r.text[:100]}")

        # Small delay to avoid rate limiting
        time.sleep(0.2)

    url = data.get("next")
    print(f"  Progress: {total_processed} processed, {approved_count} approved, {already_approved} already approved, {failed_count} failed")

print(f"\n=== DONE ===")
print(f"Total processed: {total_processed}")
print(f"Newly approved: {approved_count}")
print(f"Already approved: {already_approved}")
print(f"Failed: {failed_count}")
