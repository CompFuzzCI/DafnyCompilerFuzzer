import asyncio
import requests
import os
import boto3
import botocore
import time

async def bisection(file_dir, author, branch):
    # Dispatch GitHub workflow using GitHub API
    owner = "CompFuzzCI"
    repo = "DafnyCompilerFuzzer"
    workflow_id = "bisect.yaml"
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"
    }
    payload = {
        "ref": "main",
        "inputs": {
            "path": f"{file_dir}",
            "author": f"{author}",
            "branch": f"{branch}"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 204:
        print("Workflow dispatched successfully.")
    else:
        print("Failed to dispatch workflow.")

    key = os.path.join(*file_dir.split('/')[3:])
    s3_bucket = "compfuzzci"
    s3_key = f"{key}bisect_result.txt"
        
    s3_client = boto3.client('s3')
    print(f"Checking S3 for result file: {s3_key}")
    start_time = time.time()
    while True:
        # Check if result file is in S3
        try:
            s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            print("Result file found in S3.")
            # Download the object from S3
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return content.split('\n')
            # Perform further actions here
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                await asyncio.sleep(5)
            else:
                print("An error occurred while checking S3:", e)
        
        # Check if 30 minutes have passed
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1800:
            print("Timeout: 30 minutes have passed.")
            break