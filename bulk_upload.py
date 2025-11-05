
import os
import requests
import argparse

def upload_images(onedrive_path, endpoint_url, api_key):
    """
    Traverses the onedrive directory, finds all images, and uploads them
    to the specified endpoint.
    """
    person_id_counter = 1
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json"
    }

    for root, _, files in os.walk(onedrive_path):
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(root, filename)
                person_id = f"kis-{person_id_counter:05d}"

                print(f"Uploading {image_path} with person_id: {person_id}")

                with open(image_path, 'rb') as f:
                    files = {'images': (filename, f, 'image/jpeg')}
                    data = {'person_id': person_id}
                    try:
                        response = requests.post(endpoint_url, files=files, data=data, headers=headers)
                        response.raise_for_status()
                        print(f"Successfully uploaded {filename}. Server response: {response.json()}")
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to upload {filename}. Error: {e}")

                person_id_counter += 1
                if person_id_counter > 10000:
                    print("Reached the maximum person_id limit of 10000.")
                    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk upload images to the identity service.")
    parser.add_argument("--endpoint", default="http://localhost:8800/register-upload",
                        help="The URL of the upload endpoint.")
    parser.add_argument("--api-key", default="YOUR_API_KEY_HERE",
                        help="The API key for authorization.")
    args = parser.parse_args()

    onedrive_directory = os.path.join(os.path.dirname(__file__), 'onedrive')
    upload_images(onedrive_directory, args.endpoint, args.api_key)
