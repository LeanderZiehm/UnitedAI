from flask import Flask, render_template, request, jsonify
from diffusers import AutoPipelineForText2Image
import torch
from PIL import Image
import io
import base64

# Initialize the Flask app
app = Flask(__name__)

# modelName = "stabilityai/sd-turbo"
modelName = "stabilityai/sdxl-turbo"

# Load the text-to-image model
pipe = AutoPipelineForText2Image.from_pretrained(modelName, torch_dtype=torch.float16, variant="fp16")
pipe.to("cuda")

def generate_image(prompt):
    # Generate the image based on the prompt
    image = pipe(prompt=prompt, num_inference_steps=1, guidance_scale=0.0).images[0]
    
    # Save the image to a byte buffer
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    
    # Encode the image to base64
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

# Define the route for generating images
@app.route("/generate", methods=["POST"])
def generate():
    # Get the prompt from the JSON request
    data = request.json
    prompt = data.get("prompt", "")

    # Generate the image if prompt is not empty
    if prompt:
        generated_image = generate_image(prompt)
        return jsonify({"image": generated_image})
    
    return jsonify({"error": "No prompt provided"}), 400

# Define the main route to serve the HTML page
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

