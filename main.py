from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import os
import math
import uuid
import requests

app = FastAPI()

# 输出目录（Render不允许写入项目根目录，写入/tmp）
OUTPUT_DIR = "/tmp/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 提供访问已拆分文件的静态文件路径
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")

@app.get("/")
async def root():
    return {"status": "ok", "message": "PDF Split API is running."}

@app.post("/split-pdf")
async def split_pdf(request: Request):
    try:
        data = await request.json()
        file_url = data.get("file")
        ratio = float(data.get("ratio", 0))

        if not file_url or not (0 < ratio < 1):
            return JSONResponse(status_code=400, content={"error": "Invalid input. 'file' must be a valid URL and 'ratio' between 0 and 1."})

        # 下载 PDF 文件
        response = requests.get(file_url)
        if response.status_code != 200:
            return JSONResponse(status_code=400, content={"error": f"Failed to download PDF: status code {response.status_code}"})

        file_bytes = response.content
        reader = PdfReader(BytesIO(file_bytes))
        total_pages = len(reader.pages)
        step = math.floor(total_pages * ratio)

        if step < 1:
            return JSONResponse(status_code=400, content={"error": "Ratio too small, resulting in 0 pages per split."})

        parts = []
        start = 0

        while start < total_pages:
            end = min(start + step, total_pages)
            writer = PdfWriter()
            for i in range(start, end):
                writer.add_page(reader.pages[i])

            unique_id = uuid.uuid4().hex[:8]
            file_name = f"split_part_{len(parts)+1}_{unique_id}.pdf"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            with open(file_path, "wb") as f:
                writer.write(f)

            public_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/files/{file_name}"
            parts.append({
                "part": len(parts) + 1,
                "file_name": file_name,
                "pages": f"{start+1}-{end}",
                "url": public_url
            })

            start = end

        return {"status": "success", "parts": parts}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})
