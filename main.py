from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import os
import math
import uuid
import requests
import traceback  # ✅ 记得导入

app = FastAPI()

# ✅ 推荐 Render 中用 /tmp/output
OUTPUT_DIR = "/tmp/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")


@app.post("/split-pdf")
async def split_pdf(request: Request):
    try:
        data = await request.json()
        file = data.get("file")
        ratio = float(data.get("ratio", 0))

        if not file or not (0 < ratio < 1):
            return JSONResponse(status_code=400, content={"error": "invalid input"})

        response = requests.get(file)
        if response.status_code != 200:
            return JSONResponse(status_code=400, content={"error": "failed to download PDF"})

        file_bytes = response.content
        reader = PdfReader(BytesIO(file_bytes))
        total_pages = len(reader.pages)
        step = math.floor(total_pages * ratio)

        if step < 1:
            return JSONResponse(status_code=400, content={"error": "ratio too small"})

        parts = []
        start = 0

        while start < total_pages:
            end = min(start + step, total_pages)
            writer = PdfWriter()
            for i in range(start, end):
                writer.add_page(reader.pages[i])

            unique_id = uuid.uuid4().hex[:8]
            file_name = f"split_part_{len(parts) + 1}_{unique_id}.pdf"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            with open(file_path, "wb") as f:
                writer.write(f)

            parts.append({
                "part": len(parts) + 1,
                "file_name": file_name,
                "pages": f"{start + 1}-{end}",
                "url": f"https://pdf-split-api-hch8.onrender.com/files/{file_name}"
            })

            start = end

        return {"status": "success", "parts": parts}

    except Exception as e:
        traceback.print_exc()  # ✅ 打印堆栈到 Render 日志中
        return JSONResponse(status_code=500, content={"error": str(e)})
