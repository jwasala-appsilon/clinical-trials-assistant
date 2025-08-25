import os

from chainlit.utils import mount_chainlit
from fastapi import FastAPI, Request

server_url = os.environ.get("CONNECT_SERVER")
guid = os.environ.get("CONNECT_CONTENT_GUID")
root_path = f"/content/{guid}" if guid else ""

app = FastAPI(root_path=root_path)


@app.get("/debug-headers")
async def debug_headers(request: Request):
    return dict(request.headers)


@app.get("/app")
def read_main():
    return {"message": "Hello World from main app"}


mount_chainlit(app=app, target="clinical_trials_assistant/chainlit.py", path=f"/")
