import os
import shutil
import subprocess
import requests
import boto3
import hashlib
import asyncio
from interestingness_test_gen import generate_interestingness_test
from reduction import reduction
from bisection import bisection

# Get the task id
ECS_CONTAINER_METADATA_URI_V4 = os.environ.get('ECS_CONTAINER_METADATA_URI_V4')
response = requests.get(f"{ECS_CONTAINER_METADATA_URI_V4}/task")
TASK_ID = response.json()["TaskARN"].split("/")[-1]
# Set the S3 folder
S3_folder = "s3://compfuzzci/tmp/" + TASK_ID

# Create an S3 resource object
s3 = boto3.resource('s3')

def hash_bug(bug):
    # Hash bug data and make a folder for it in location/language/
    sorted_bug = sorted(bug)
    concatenated_bug = ''.join(sorted_bug)
    hashed_bug = hashlib.md5(concatenated_bug.encode()).hexdigest()
    return hashed_bug

def is_duplicate(branch="master", language= "dafny", hashed_bug=""):
    # Define the S3 bucket and prefix
    bucket_name = "compfuzzci"
    prefix = f"bugs/{branch}/{language}/{hashed_bug}"

    # List objects in the S3 bucket with the specified prefix
    print(f"Checking if {prefix} exists")
    response = s3.meta.client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if response.get('Contents'):
        return True

    return False

async def process_bug(output_dir, language, bug, author, branch, interpret, processing=False, issue_no="None"):

    async def handle_bisection_reduction():
        reduction_task = asyncio.create_task(reduction(processing, output_dir, language, interpret))
        bisection_result = await bisection(f"{S3_folder}/{language}/", author, branch)
        print(f"Bisection result arrived: Location={bisection_result[0]}, First bad commit={bisection_result[1]}")
        if bisection_result[1] == "duplicated":
            print("Bug is duplicated. Cancelling reduction task.")
            return 0
        elif language == "miscompilation" and is_duplicate(bisection_result[0], language, bisection_result[1]):
            reduction_task.cancel()
            try:
                await reduction_task
            except asyncio.CancelledError:
                print("Bug is duplicated. Reduction task cancelled.")
            return 0
        else:
            print("Waiting for reduction")
            await reduction_task
            print("Reduction result arrived")
            return bisection_result
    
    # this check only pass if bug is not duplicate anywhere.
    if language != "miscompilation":
        hashed_bug = hash_bug(bug)
    else:
        hashed_bug = bug

    if not processing:
            output_dir += "/"

    if not (is_duplicate("master", language, hashed_bug) or is_duplicate(branch, language, hashed_bug)):
        print("Found interesting case in " + language)

        generate_interestingness_test(output_dir, interpret, bug, language)

        if not processing:
            os.makedirs(f"{language}-tmp", exist_ok=True)
            shutil.copy(f"{output_dir}main.dfy", f"{language}-tmp/main.dfy")
            shutil.copy(f"{output_dir}{language}-interestingness_test.sh", f"{language}-tmp/{language}-interestingness_test.sh")
            process = await asyncio.create_subprocess_shell(f"./{language}-interestingness_test.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=f"{language}-tmp")
            await process.communicate()
            os.remove(f"{language}-tmp/main.dfy")
            print(f"interestingness_test returns: {process.returncode}")
            if process.returncode != 0:
                return 0

        # Copy interestingness test, fuzz_d.log, main.dfy to folder for the task in S3
        os.makedirs(f"tmp/{language}", exist_ok=True)
        subprocess.run(["cp", f"{output_dir}{language}-interestingness_test.sh", f"tmp/{language}/interestingness_test.sh"], check=True)
        subprocess.run(["cp", f"{output_dir}main.dfy", f"tmp/{language}/main.dfy"], check=True)

        with open(f"tmp/{language}/data.txt", 'w') as f:
            f.write(f"{language}\n")
            f.write(f"{hashed_bug}\n")
            f.write(f"{processing}\n")
        f.close()
        subprocess.run(["aws", "s3", "cp", f"tmp/{language}/", f"{S3_folder}/{language}/", "--recursive"], check=True)
        subprocess.run(["rm", "-rf", f"tmp/{language}"], check=True)

        result = await handle_bisection_reduction()
        if not result:
            s3.Bucket('compfuzzci').objects.filter(Prefix=f"{TASK_ID}/{language}").delete()
            return 0
        else:
            location = result[0]
            first_bad_commit = result[1]

        # Copy reduced program, fuzz-d.log to S3
        print("Copying reduced program and output to S3")
        os.makedirs(f"tmp/{language}", exist_ok=True)
        subprocess.run(["cp", f"{output_dir}main.dfy", f"tmp/{language}/original.dfy"], check=True)
        subprocess.run(["cp", f"{output_dir}fuzz-d.log", f"tmp/{language}/original_fuzz-d.log"], check=True)
        subprocess.run(["cp", f"{output_dir}reduced_{language}/main.dfy", f"tmp/{language}/reduced.dfy"], check=True)
        subprocess.run(["cp", f"{output_dir}reduced_{language}/fuzz-d.log", f"tmp/{language}/reduced_fuzz-d.log"], check=True)

        if issue_no == "None":
            result_foldername = f"s3://compfuzzci/bugs-to-be-processed/pull_request-{location}-{language}-{TASK_ID}/"
        else:
            result_foldername = f"s3://compfuzzci/bugs-to-be-processed/issue-{issue_no}-{location}-{language}-{TASK_ID}/"
        subprocess.run(["aws", "s3", "cp", f"tmp/{language}/", result_foldername, "--recursive"], check=True)

        with open(f"tmp/{language}/data.txt", 'w') as f:
            f.write(f"Location: {location}\n")
            f.write(f"Bad commit: {first_bad_commit}\n")
            f.write(f"Language: {language}\n")
            f.write(f"Bug: {hashed_bug}\n")
            f.write(f"Issue number: {issue_no}\n")
        f.close()

        subprocess.run(["aws", "s3", "cp", f"tmp/{language}/data.txt", f"{result_foldername}data.txt"], check=True)

        subprocess.run(["rm", "-rf", f"tmp/{language}/"], check=True)

        # Remove the temp folder
        print("Removing temp folder")
        s3.Bucket('compfuzzci').objects.filter(Prefix=f"{TASK_ID}/{language}").delete()
        print("Done")
        return 0
    else:
        print(f"Not interesting: Duplicate or known error in {language}")
        return 0

def process_bug_handler(output_dir, language, bug, author, branch, interpret, processing, issue_no):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_bug(output_dir, language, bug, author, branch, interpret, processing, issue_no))
    finally:
        loop.close()