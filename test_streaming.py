from async_asgi_testclient import TestClient
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get('/stream')
async def stream():
    def generate():
        for i in range(3):
            yield f"data: chunk {i}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

async def test():
    async with TestClient(app) as client:
        response = await client.get('/stream')
        print('Response type:', type(response))
        print('Status code:', response.status_code)
        print('Content type:', response.headers.get('content-type'))
        print('Text:', response.text)
        
        # Try different iteration methods
        print('\nTrying iter_content:')
        try:
            async for chunk in response.iter_content():
                print(f"Chunk: {chunk}")
        except Exception as e:
            print(f"iter_content error: {e}")
            
        print('\nTrying iter_lines:')
        try:
            async for line in response.iter_lines():
                print(f"Line: {line}")
        except Exception as e:
            print(f"iter_lines error: {e}")

asyncio.run(test()) 