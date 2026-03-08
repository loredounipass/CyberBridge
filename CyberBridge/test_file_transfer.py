import sys
import os
import base64

# Add client dir to path
sys.path.insert(0, os.path.abspath("client"))

import main as client_main

# Create a dummy file
test_content = b"Hello World!"
test_file = "test_upload.txt"
with open(test_file, "wb") as f:
    f.write(test_content)

# Test Upload Logic (Client receives base64 and writes file)
b64_data = base64.b64encode(test_content).decode()
upload_dest = "uploaded_test.txt"
if os.path.exists(upload_dest):
    os.remove(upload_dest)

print("Testing upload...")
success = client_main._upload_file(upload_dest, b64_data)
if success and os.path.exists(upload_dest):
    with open(upload_dest, "rb") as f:
        content = f.read()
    if content == test_content:
        print("Upload logic works correctly.")
    else:
        print("Upload content mismatch.")
else:
    print("Upload failed.")

# Test Download Logic (Client reads file and returns base64)
print("Testing download...")
download_b64 = client_main._download_file(upload_dest)
if download_b64:
    decoded = base64.b64decode(download_b64)
    if decoded == test_content:
        print("Download logic works correctly.")
    else:
        print("Download content mismatch.")
else:
    print("Download failed.")

# Clean up
if os.path.exists(test_file):
    os.remove(test_file)
if os.path.exists(upload_dest):
    os.remove(upload_dest)
