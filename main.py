from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import math
import uuid
import requests

app = FastAPI()

@app.post("/split-pdf")
async def split_pdf(request: Request):
    try:
        data = await request.json()
        file = data.get("file")
        ratio = float(data.get("ratio", 0))

        if not file or not (0 < ratio < 1):
            return JSONResponse(status_code=400, content={"error": "invalid input"})

        # 下载 PDF
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

            output_io = BytesIO()
            writer.write(output_io)
            writer.close()
            output_io.seek(0)

            parts.append({
                "part": len(parts) + 1,
                "file_name": f"split_part_{len(parts) + 1}.pdf",
                "pages": f"{start + 1}-{end}"
            })

            start = end

        return {"status": "success", "parts": parts}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ✅ 添加以下内容，Render 部署才会监听 8080 端口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
