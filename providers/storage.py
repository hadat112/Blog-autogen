import requests
import os
import tempfile

class StorageProvider:
    def download_image(self, url):
        """
        Downloads an image from a URL to a temporary file.
        :param url: URL of the image.
        :return: Path to the temporary file.
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create a temporary file
        suffix = os.path.splitext(url)[1]
        if not suffix:
            suffix = ".png" # Default to png if no extension found
        
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_path

    def cleanup(self, path):
        """
        Deletes a file if it exists.
        """
        if os.path.exists(path):
            os.remove(path)
