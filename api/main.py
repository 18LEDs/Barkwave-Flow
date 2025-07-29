from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import json
import subprocess
import os

PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipelines"
TERRAFORM_DIR = Path(__file__).resolve().parent.parent / "terraform"

app = FastAPI()

class PipelineModel(BaseModel):
    name: str
    filter: str
    # Additional fields can be added as needed.


def pipeline_path(name: str) -> Path:
    return PIPELINE_DIR / f"{name}.json"


def write_pipeline(name: str, data: dict):
    path = pipeline_path(name)
    with path.open("w") as f:
        json.dump(data, f, indent=2)


def read_pipeline(name: str) -> dict:
    path = pipeline_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    with path.open() as f:
        return json.load(f)


@app.get("/pipelines")
def list_pipelines() -> dict:
    items = {}
    for file in PIPELINE_DIR.glob("*.json"):
        with file.open() as f:
            items[file.stem] = json.load(f)
    return items


@app.put("/pipelines/{name}")
def update_pipeline(name: str, payload: PipelineModel):
    write_pipeline(name, payload.dict())
    return {"status": "updated", "name": name}


def terraform_apply(pipelines: Optional[List[str]] = None) -> str:
    env = os.environ.copy()
    cmd = ["terraform", "apply", "-auto-approve"]
    if pipelines:
        targets = [f"-target=datadog_logs_custom_pipeline.pipeline[{p}]" for p in pipelines]
        cmd.extend(targets)
    proc = subprocess.run(cmd, cwd=TERRAFORM_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout


@app.post("/apply")
def apply(pipelines: Optional[str] = Query(None, description="Comma separated pipeline names")):
    target_list = pipelines.split(",") if pipelines else None
    try:
        output = terraform_apply(target_list)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"output": output}
