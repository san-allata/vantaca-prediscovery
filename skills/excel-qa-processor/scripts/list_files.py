
import os

print("Current working directory:", os.getcwd())
print("\nAll files in working directory tree:")
for root, dirs, files in os.walk('.'):
    for f in files:
        full = os.path.join(root, f)
        size = os.path.getsize(full)
        print(f"  {full}  ({size} bytes)")
