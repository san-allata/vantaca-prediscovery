
import os

print("CWD:", os.getcwd())
print("\n--- Listing CWD parent and common dirs ---")
for d in [".", "..", "/tmp", "/", os.path.expanduser("~")]:
    try:
        print(f"\n{d}:")
        for entry in os.listdir(d):
            print(f"   {entry}")
    except Exception as e:
        print(f"   [error] {e}")

print("\n--- Environment variables containing 'FILE' or 'INPUT' or 'DOC' ---")
for k, v in os.environ.items():
    if any(s in k.upper() for s in ["FILE", "INPUT", "DOC", "PATH"]):
        print(f"  {k} = {v}")
