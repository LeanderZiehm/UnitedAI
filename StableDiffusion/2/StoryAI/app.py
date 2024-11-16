from flask import Flask, render_template, request, jsonify, Response
from diffusers import AutoPipelineForText2Image
from ollama import chat
import torch
from PIL import Image
import io
import base64
import json
import time

app = Flask(__name__)

modelName = "stabilityai/sdxl-turbo"
pipe = AutoPipelineForText2Image.from_pretrained(modelName, torch_dtype=torch.float16, variant="fp16")
pipe.to("cuda")

story_text = ""

def generate_image(prompt):
    image = pipe(prompt=prompt, num_inference_steps=1, guidance_scale=0.0).images[0]
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def generate_story_segment(theme, context):
    response = chat(model='llama3.2', messages=[{'role': 'user', 'content': f"{theme}\n{context}"}])
    return response['message']['content']

@app.route("/start_story", methods=["POST"])
def start_story():
    global story_text
    data = request.json
    theme = data.get("theme", "A magical forest adventure")
    context = theme
    story_text = ""
    
    
    def generate_steps():
        global story_text
        for step in range(5):
            story_segment = generate_story_segment(theme, story_text)
            story_text += story_segment + " "
            
            yield json.dumps({"text": story_segment}) + "\n"  # Send the text segment first
            
            generated_image = generate_image(story_segment)
            yield json.dumps({"image": generated_image}) + "\n"  # Send the image once done

        final_wrap_up = generate_story_segment(theme, story_text + " Please wrap up the story.")
        yield json.dumps({"text": final_wrap_up}) + "\n"
        
        wrap_up_image = generate_image(final_wrap_up)
        yield json.dumps({"image": wrap_up_image}) + "\n"

    return Response(generate_steps(), content_type='application/json')

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
