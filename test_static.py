import os

static_path = os.path.join("app", "static")
print(f"Static path: {static_path}")
print(f"Exists: {os.path.exists(static_path)}")

if os.path.exists(static_path):
    files = os.listdir(static_path)
    print(f"Files in static: {files}")
else:
    print("Static folder not found!")