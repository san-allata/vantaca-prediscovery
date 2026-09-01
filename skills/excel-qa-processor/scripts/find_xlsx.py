
import subprocess

print("Searching entire filesystem for xlsx/docx files (excluding /proc, /sys)...")
try:
    result = subprocess.run(
        ["find", "/", "-iname", "*.xlsx", "-o", "-iname", "*.docx"],
        capture_output=True, text=True, timeout=15
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR (truncated):")
    print(result.stderr[:2000])
except Exception as e:
    print(f"Error: {e}")
