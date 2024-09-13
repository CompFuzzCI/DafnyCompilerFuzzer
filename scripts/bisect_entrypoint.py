import os
import subprocess
import sys
import boto3

if __name__ == "__main__":
    file_folder=sys.argv[1]
    author=sys.argv[2]
    branch=sys.argv[3]
    #Set up dafny
    s3 = boto3.resource('s3')

    #download the file
    subprocess.run(["aws", "s3", "cp", f"{file_folder}", f"/compfuzzci", "--recursive"], check=True)
    subprocess.run(["chmod", "+x", "/compfuzzci/interestingness_test.sh"], check=True)
    # Read branch, language, main_commit, hashed bug
    with open("/compfuzzci/data.txt", 'r') as f:
        language = f.readline().strip()
        hashed_bug = f.readline().strip()
        processing = f.readline().strip()

    main_commit = subprocess.check_output(["git", "rev-parse", "master"], cwd='dafny').decode().strip()
    branch_commit = subprocess.check_output(["git", "rev-parse", branch], cwd='dafny').decode().strip()
    subprocess.run(["git", "checkout", "master"], check=True, cwd='dafny')
    if processing == "False":  
        location = branch
        # Get the location of the bug
        print("Checking if bug is on master")
        if subprocess.call(["./bisect_script.sh", main_commit]):
            print("Bug is on master")
            location = "master"
        else:
            print("Bug is on branch")
    else:
        location = "master"

    first_bad_commit = "undetermined"
    manual_investigation = False
    if location == "master":
        #This is the last point that fuzz-d program guarantee to work
        last_good_commit = "8a5a5945d6eefc552bdc39a3868dd34bb38a49d4"
        result = subprocess.call(["./bisect_script.sh", last_good_commit])
        if result:
            print("Bug needs manual investigation")
            manual_investigation = True
                
        if not manual_investigation:
            # Get the latest commit on the current branch
            print("Bisecting on master")
            # Start the bisect process
            subprocess.run(["git", "bisect", "start", main_commit, last_good_commit, "--no-checkout"], check=True, cwd='dafny')

            # Start the subprocess
            process = subprocess.Popen(
                ["git", "bisect", "run", "/compfuzzci/bisect_script.sh"],
                cwd='dafny',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Read and print the output in real time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if ' is the first bad commit' in output:
                        first_bad_commit = output.replace(' is the first bad commit', '')
                    print(output.strip())

            # Capture the remaining output (if any)
            stderr = process.communicate()[1]
            if stderr:
                print(stderr.strip())

            return_code = process.returncode

    elif language == "miscompilation" and first_bad_commit == "undetermined":
            subprocess.run(["git", "checkout", branch_commit], check=True, cwd='dafny')
            result = subprocess.run(["git", "merge-base", main_commit, branch_commit], cwd='dafny', capture_output=True, text=True)
            last_good_commit = result.stdout.strip()
            print("Checking the branch's last merge base with master")
            result = subprocess.call(["./bisect_script.sh", last_good_commit])
            if result:
                print("Branch out of date. Bug has already been fixed on master")
                first_bad_commit = "deplicated"
            else:
                print("Bug is introduced in the branch")
                print(f"Bisecting on {location}")
                # Start the bisect process
                subprocess.run(["git", "bisect", "start", branch_commit, last_good_commit, "--no-checkout"], check=True, cwd='dafny')
                            
                # Start the subprocess
                process = subprocess.Popen(
                    ["git", "bisect", "run", "/compfuzzci/bisect_script.sh"],
                    cwd='dafny',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Read and print the output in real time
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        if ' is the first bad commit' in output:
                            first_bad_commit = output.replace(' is the first bad commit', '')
                        print(output.strip())

                # Capture the remaining output (if any)
                stderr = process.communicate()[1]
                if stderr:
                    print(stderr.strip())

    else:
        subprocess.run(["git", "checkout", branch_commit], check=True, cwd='dafny')
        last_good_commit = subprocess.check_output(["git", "merge-base", main_commit, branch_commit], cwd='dafny').decode().strip()
        print("Checking the branch's last merge base with master")
        result = subprocess.call(["./bisect_script.sh", last_good_commit])
        if result:
            print("Branch out of date. Bug has already been fixed on master")
            first_bad_commit = "deplicated"
        else:
            first_bad_commit = "undetermined"


    with open("bisect_result.txt", 'w') as file_obj:
        file_obj.write(f"{location}\n")
        file_obj.write(f"{first_bad_commit}\n")

    subprocess.run(["aws", "s3", "cp", "bisect_result.txt", f"{file_folder}bisect_result.txt"], check=True)