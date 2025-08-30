import requests

# Change this to your actual backend URL
BACKEND_URL = "http://localhost:5000/upload-entry"

# Path to the test image (update this path to your test image)
IMAGE_PATH = "1E.jpg"

def test_upload_entry():
    with open(IMAGE_PATH, "rb") as img_file:
        files = {"image": img_file}
        response = requests.post(BACKEND_URL, files=files)
        print("Status Code:", response.status_code)
        print("Response:", response.json())

if __name__ == "__main__":
    test_upload_entry()
