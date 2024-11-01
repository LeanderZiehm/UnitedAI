import requests
from PIL import Image
import os
import re
import time

url = 'http://127.0.0.1:5000/generateImage'



def main():
    while True:
        inputPrompt = input("prompt: ")
        requestGenerateImage(inputPrompt)




def requestGenerateImage(prompt= "Galaxy",parameters = None): 
        data = {
            "prompt": prompt,
            "parameters": parameters
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            
            base_filename = sanitize_filename(prompt)
            filename = get_unique_filename(base_filename, ".png")

            with open(filename, "wb") as f:
                f.write(response.content)
            
            print(f"Image saved as {filename}")

            img = Image.open(filename)
            img.show()
        else:
            print(f"Failed to get image. Status code: {response.status_code}")



















def sanitize_filename(prompt):
    
    return re.sub(r'[\\/*?:"<>|]', '_', prompt)

def get_unique_filename(base_name, extension):
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        if not os.path.exists(filename):
            return filename
        counter += 1


if __name__ == '__main__':
    main()


