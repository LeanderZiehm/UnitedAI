from flask import Flask, request, jsonify, send_file
from diffusers import StableDiffusionPipeline
import matplotlib.pyplot as plt
import torch
from io import BytesIO

app = Flask(__name__)
model_id1 = "dreamlike-art/dreamlike-diffusion-1.0"
pipe = StableDiffusionPipeline.from_pretrained(model_id1, torch_dtype=torch.float16, use_safetensors=True)
pipe = pipe.to("cuda")


@app.route('/generateImage', methods=['POST'])
def generateImage():
    data = request.get_json()
    prompt = data['prompt']
    parameters ={'num_inference_steps': 10, 'negative_prompt': 'ugly, distorted, low quality','num_images_per_prompt': 1}

    image = pipe(prompt,**parameters).images[0]

    img_buffer = BytesIO()
    image.save(img_buffer, format='PNG')
    img_buffer.seek(0)  # Rewind the buffer to the beginning

    return send_file(img_buffer, mimetype='image/png')

@app.route('/', methods=['GET'])
def hello():
    return "Hello World"


if __name__ == '__main__':
    app.run(debug=True)
