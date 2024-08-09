import asyncio
import os
import subprocess
import shutil

async def reduction(processing=False, output_dir=None, language=None, interpret=False):
    # Reduce the test case
    try:
        print("Reducing...")
        os.makedirs(f"{output_dir}creduce-{language}", exist_ok=True)
        shutil.copy(f"{output_dir}main.dfy", f"{output_dir}creduce-{language}/main.dfy")
        shutil.copy(f"{output_dir}{language}-interestingness_test.sh", f"{output_dir}creduce-{language}/{language}-interestingness_test.sh")
        process = await asyncio.create_subprocess_shell(f"./{language}-interestingness_test.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=f"{output_dir}creduce-{language}")
        await process.communicate()
        print(f"interestingness_test returns: {process.returncode}")
        process = await asyncio.create_subprocess_shell("creduce --not-c --n 4 --no-default-passes --add-pass pass_lines 1 0 " + f"{language}-interestingness_test.sh " + f"main.dfy", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=f"{output_dir}creduce-{language}")
        stdout, stderr = await process.communicate()
        print(f"creduce stdout: {stdout.decode()}")
        print(f"creduce stderr: {stderr.decode()}")
        process = await asyncio.create_subprocess_shell("java -jar perses.jar --input-file " + f"{output_dir}creduce-{language}/main.dfy --test-script " + f"{output_dir}creduce-{language}/{language}-interestingness_test.sh --output-dir " + f"{output_dir}reduced_{language}/", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        print(f"perses stdout: {stdout.decode()}")
        print(f"perses stderr: {stderr.decode()}")
        if process.returncode != 0:
            print("Reduction Failed (might be creduce's fault)")
            process = await asyncio.create_subprocess_shell("java -jar perses.jar --input-file " + f"{output_dir}main.dfy --test-script " + f"{output_dir}{language}-interestingness_test.sh --output-dir " + f"{output_dir}reduced_{language}/", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            print(f"perses stdout: {stdout.decode()}")
            print(f"perses stderr: {stderr.decode()}")
        if process.returncode != 0:
            print("Reduction Failed (not creduce's fault)")
            if not processing:
                return 0
            else:
                os.makedirs(f"{output_dir}reduced_{language}", exist_ok=True)
                subprocess.run(["cp", f"{output_dir}main.dfy", f"{output_dir}reduced_{language}/main.dfy"], check=True)
            
        print("Validating the reduced program")
        if interpret:
            process = await asyncio.create_subprocess_shell("java -jar fuzz_d.jar validate " + f"{output_dir}reduced_{language}/main.dfy --interpret --language " + language, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        else:
            process = await asyncio.create_subprocess_shell("java -jar fuzz_d.jar validate " + f"{output_dir}reduced_{language}/main.dfy --language " + language, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        print("Reduction complete")
        return 1
    except asyncio.CancelledError:
        process.terminate()
        print("Reduction cancelled")
        return 0