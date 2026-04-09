from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests, os, zipfile, uuid

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")

OUTPUT = "output"
INPUT = "input"
os.makedirs(OUTPUT, exist_ok=True)
os.makedirs(INPUT, exist_ok=True)

concepts = [
    ("Ảnh chính", "dark spotlight"),
    ("Sản phẩm", "white studio"),
    ("Tính năng", "tech glow"),
    ("Kích thước", "minimal layout"),
    ("Lắp xe", "motorcycle scene"),
    ("Close-up", "macro lighting"),
    ("Lifestyle", "daily life"),
    ("So sánh", "comparison layout"),
    ("CTA", "sale banner")
]

features = [
    "CNC CAO CẤP",
    "CHỐNG RUNG",
    "LẮP MỌI LOẠI XE",
    "SIÊU BỀN"
]

def remove_bg(input_path, output_path):
    with open(input_path, 'rb') as f:
        r = requests.post(
            "https://api.remove.bg/v1.0/removebg",
            files={'image_file': f},
            headers={'X-Api-Key': REMOVE_BG_KEY},
        )
    with open(output_path, "wb") as out:
        out.write(r.content)

def generate_bg(prompt, path):
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt + ", product background",
        size="1024x1024"
    )
    img = requests.get(result.data[0].url).content
    with open(path, "wb") as f:
        f.write(img)

def draw_text(img, title):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 45)
    except:
        font = ImageFont.load_default()

    draw.text((50, 40), title, font=font, fill="red")

    for i, f in enumerate(features):
        draw.text((50, 100+i*50), f, font=font, fill="white")

def combine(product, bg, out, text):
    bg = Image.open(bg).resize((1024,1024))
    sp = Image.open(product).convert("RGBA").resize((600,600))

    bg.paste(sp, (212,212), sp)
    draw_text(bg, text)
    bg.save(out, quality=95)

@app.post("/process")
async def process(files: list[UploadFile] = File(...), name: str = Form(...)):
    job_id = str(uuid.uuid4())
    job_folder = f"{OUTPUT}/{job_id}"
    os.makedirs(job_folder, exist_ok=True)

    all_images = []

    for file in files:
        input_path = f"{INPUT}/{file.filename}"

        with open(input_path, "wb") as f:
            f.write(await file.read())

        removed = f"{job_folder}/clean.png"
        remove_bg(input_path, removed)

        for i, (title, prompt) in enumerate(concepts):
            bg = f"{job_folder}/bg_{i}.png"
            out = f"{job_folder}/{file.filename}_{i}.png"

            generate_bg(prompt, bg)
            combine(removed, bg, out, f"{title}\n{name}")

            all_images.append(out)

    zip_path = f"{job_folder}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for img in all_images:
            zipf.write(img, os.path.basename(img))

    return FileResponse(zip_path, filename="shopee_images.zip")
