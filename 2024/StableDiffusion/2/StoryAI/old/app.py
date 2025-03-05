from flask import Flask, render_template, request, jsonify
from diffusers import AutoPipelineForText2Image
from ollama import chat
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

# Function to generate an image from text
def generate_image(prompt):
    image = pipe(prompt=prompt, num_inference_steps=1, guidance_scale=0.0).images[0]
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

# Function to generate a story segment using LLM
def generate_story_segment(theme, context):
    response = chat(model='llama3.2', messages=[{'role': 'user', 'content': f"{theme}\n{context}"}])
    return response['message']['content']

# Route to start and display the story
@app.route("/start_story", methods=["POST"])
def start_story():
    # Retrieve the theme and initial prompt
    data = request.json
    theme = data.get("theme", "A magical forest adventure")
    
    story_steps = []
    context = theme
    story_text = ""
    
    # Generate a multi-step story with images for each part
    for step in range(5):  # Assuming 5 steps for the story
        story_segment = generate_story_segment(theme, story_text)
        story_text += story_segment + " "  # Append new text to context for the next step
        
        # Generate image based on current story segment
        generated_image = generate_image(story_segment)
        
        # Add story text and image to the steps
        story_steps.append({
            "text": story_segment,
            "image": generated_image
        })

    # Generate the final wrap-up
    final_wrap_up = generate_story_segment(theme, story_text + " Please wrap up the story.")
    wrap_up_image = generate_image(final_wrap_up)

    # Add wrap-up to the story steps
    story_steps.append({
        "text": final_wrap_up,
        "image": wrap_up_image
    })

    return jsonify({"story_steps": story_steps})

# Define the main route to serve the HTML page
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
