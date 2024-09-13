import re
import subprocess
import sys
from threading import Thread
import requests
from match_error import match_error
from process_bug import process_bug_handler
import requests

# Set the commit, commit before, and duration
issue_no = sys.argv[1]
UNWANTED_LABELS = [r'kind: language development speed', r'misc: \[.*\]']



def write_code_to_file(code):
    with open ('main.dfy', 'w') as f:
        f.write(code)
    f.close()

def extract_code_from_issue_body(issue_no):
    url = f"https://api.github.com/repos/dafny-lang/dafny/issues/{issue_no}"
    response = requests.get(url)
    
    if response.status_code == 200:
        issue_body = response.json()['body']
        labels = [label['name'] for label in response.json()['labels']]
    else:
        print(f"Failed to retrieve issues: {response.status_code}")

    code = ""
    if any(label in UNWANTED_LABELS for label in labels):
        print(f"Skipping issue {issue_no} due to unwanted labels")
        return code
    
    if '```dafny' in issue_body and not re.search(r'[dD]afny (resolve|verify|format|doc|measure-complexity|server|test|generate-tests|find-dead-code|audit|merge-coverage-reports)', issue_body):
        code = issue_body.split('```dafny')[1].split('```')[0]
    else:
        print(f"Skipping issue {issue_no} due to no dafny code block or unrelated command")

    return code
    
if __name__ == "__main__":
    print(f"Processing issue {issue_no}")
    code = extract_code_from_issue_body(issue_no)
    if code:
        write_code_to_file(code)
    else:
        sys.exit(0)
    # Figure out if we can validate with interpreter
    interpret = True
    result = subprocess.call(["java", "-jar", "fuzz_d.jar", "interpret", "main.dfy"])
    if result == 1:
        interpret = False
    print("Interpret: ", interpret)
    
    if interpret:
        subprocess.call(["java", "-jar", "fuzz_d.jar", "validate", "main.dfy", "--interpret"])
    else:
        subprocess.call(["java", "-jar", "fuzz_d.jar", "validate", "main.dfy"])

    bugs = match_error("fuzz-d.log")
    print(bugs)
    threads = []
    for language, bug in bugs.items():
        if bug:
            t = Thread(target=process_bug_handler, args=("", language, bug, "dafny-lang", "master", interpret, True, issue_no))
            threads.append(t)
            t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    sys.exit(0)
