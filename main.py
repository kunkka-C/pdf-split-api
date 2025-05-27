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

# 创建输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 挂载静态文件服务，供访问拆分后的 PDF 文件
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")


@app.post("/split-pdf")
async def split_pdf(request: Request):
    try:
        data = await request.json()
        file = data.get("file")
        ratio = float(data.get("ratio", 0))

        if not file or not (0 < ratio < 1):
            return JSONResponse(status_code=400, content={"error": "invalid input"})

        # 下载原始 PDF 文件
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

            # 临时文件名
            unique_id = uuid.uuid4().hex[:8]
            file_name = f"split_part_{len(parts) + 1}_{unique_id}.pdf"
            file_path = os.path.join(OUTPUT_DIR, file_name)

            # 保存到本地
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
        return JSONResponse(status_code=500, content={"error": str(e)})
