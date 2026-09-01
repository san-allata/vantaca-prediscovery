
import subprocess, time, os

time.sleep(2)
print("CWD listing again after short delay:")
print(os.listdir("."))

print("\nFull find for any file modified in last 10 minutes under /tmp and /home:")
try:
    result = subprocess.run(
        ["find", "/tmp", "/home", "-type", "f", "-newermt", "-10 minutes"],
        capture_output=True, text=True, timeout=15
    )
    print(result.stdout)
    print(result.stderr[:1000])
except Exception as e:
    print(f"Error: {e}")

print("\nChecking mount points:")
try:
    result = subprocess.run(["mount"], capture_output=True, text=True, timeout=10)
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")
