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

if __name__ == "__main__":
    subprocess.run(["./setup_dafny.sh", author, branch], check=True)
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
