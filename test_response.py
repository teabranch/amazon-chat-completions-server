from async_asgi_testclient import TestClient
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.get('/')
async def root():
    return {'message': 'hello'}

async def test():
    async with TestClient(app) as client:
        response = await client.get('/')
        print('Response type:', type(response))
        print('All methods:', [m for m in dir(response) if not m.startswith('_')])
        print('Iter methods:', [m for m in dir(response) if 'iter' in m])

asyncio.run(test()) 