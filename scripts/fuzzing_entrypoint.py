import subprocess
import time
import sys
from threading import Thread

from match_error import match_error
from process_bug import process_bug_handler

# Set a default duration in seconds (1800 seconds for 30 minutes)
default_duration = 3600

# Set the commit, commit before, and duration
duration = int(sys.argv[1]) if sys.argv[1] else default_duration
author = sys.argv[2]
branch = sys.argv[3]
start_time = time.time()

def remove_fuzz_d_error(bug):
    known_errors = ["All elements of display must have some common supertype", "type of left argument to +",
                    "type parameter is not declared in this scope", "Error: the type of this expression is underspecified",
                    "Error: branches of if-then-else have incompatible types", "Error: the two branches of an if-then-else expression must have the same type",
                    "incompatible types", "Unexpected field to assign whose isAssignedVar is not in the environment",
                    "Error: Microsoft.Dafny.UnsupportedInvalidOperationException", "index", "Index"]
    
    filtered_bug = [b for b in bug if not any(error in b for error in known_errors)]
    
    return filtered_bug
if __name__ == "__main__":
    while (time.time() - start_time) < duration:
        # Fuzz until we hit an interesting case
        output = subprocess.run(["timeout", "60", "java", "-jar", "fuzz_d.jar", "fuzz"], capture_output=True, text=True)
        if output.returncode == 0:
            output_dir = output.stdout.split(': ')[-1].strip()
            uuid = output_dir.split('/')[-1]
            bugs = match_error(f"{output_dir}/fuzz-d.log")
            print(bugs)
            # Figure out if we can validate with interpreter
            interpret = False
            threads = []
            for language, bug in bugs.items():
                if language != "miscompilation":
                    bug = remove_fuzz_d_error(bug)
                if bug:
                    t = Thread(target=process_bug_handler, args=(output_dir, language, bug, author, branch, interpret, False, "None"))
                    threads.append(t)
                    t.start()

            # Wait for all threads to finish
            for t in threads:
                t.join()
            if output_dir:
                subprocess.run(["rm", "-rf", output_dir])
        else:
            print("Fuzz-d crashed or timed out")

    sys.exit(0)
