from pathlib import Path
from typing import Optional, List, Union, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, validator
import json
import subprocess
import os

PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipelines"
TERRAFORM_DIR = Path(__file__).resolve().parent.parent / "terraform"

app = FastAPI()

class ProcessorModel(BaseModel):
    type: str
    name: Optional[str] = None
    is_enabled: Optional[bool] = True
    inputs: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class PipelineModel(BaseModel):
    name: str
    filter: Optional[Union[str, Dict]] = None
    processors: Optional[List[ProcessorModel]] = None
    is_enabled: Optional[bool] = True

    @validator("processors", pre=True)
    def _processors_is_list(cls, v):
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("processors must be a list")
        return v


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
    write_pipeline(name, json.loads(payload.json(exclude_none=True)))
    return {"status": "updated", "name": name}


def terraform_apply(pipelines: Optional[List[str]] = None) -> str:
    env = os.environ.copy()
    # Ensure backend is initialized for Consul using env vars
    terraform_init_if_needed(env)
    cmd = ["terraform", "apply", "-auto-approve", "-parallelism=1"]
    if pipelines:
        # Quote for_each keys to match Terraform addressing
        targets = [f"-target=datadog_logs_custom_pipeline.pipeline[\"{p}\"]" for p in pipelines]
        cmd.extend(targets)
    proc = subprocess.run(cmd, cwd=TERRAFORM_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout


def terraform_init_if_needed(env: dict) -> None:
    
    terraform_dir = str(TERRAFORM_DIR)
    need_init = not (TERRAFORM_DIR / ".terraform").exists()
    # Also allow forcing re-init via env
    if env.get("TF_FORCE_INIT") == "1":
        need_init = True
    if not need_init:
        return

    # Expect Consul backend env variables
    address = env.get("CONSUL_HTTP_ADDR")
    backend_path = env.get("CONSUL_BACKEND_PATH")
    scheme = env.get("CONSUL_SCHEME", "http")
    token = env.get("CONSUL_HTTP_TOKEN", "")
    if not address or not backend_path:
        raise RuntimeError(
            "Terraform backend not initialized and CONSUL_HTTP_ADDR/CONSUL_BACKEND_PATH not provided"
        )

    cmd = [
        "terraform", "init",
        f"-backend-config=address={address}",
        f"-backend-config=path={backend_path}",
        f"-backend-config=scheme={scheme}",
        "-backend-config=lock=true",
    ]
    if token:
        cmd.append(f"-backend-config=access_token={token}")
    proc = subprocess.run(cmd, cwd=terraform_dir, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)


def deep_merge(a: Any, b: Any) -> Any:
    """Recursively merge b into a (in place), returning a."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k, v in b.items():
            if k in a:
                a[k] = deep_merge(a[k], v)
            else:
                a[k] = v
        return a
    return b


@app.get("/pipelines/{name}/processors")
def get_processors(name: str):
    data = read_pipeline(name)
    return data.get("processors", [])


@app.put("/pipelines/{name}/processors")
def replace_processors(name: str, processors: List[Dict[str, Any]]):
    data = read_pipeline(name)
    data["processors"] = processors
    write_pipeline(name, data)
    return {"status": "updated", "name": name, "processors_count": len(processors)}


@app.put("/pipelines/{name}/processors/{index}")
def replace_processor(name: str, index: int, processor: Dict[str, Any]):
    data = read_pipeline(name)
    items = data.get("processors", [])
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail="Processor index out of range")
    items[index] = processor
    data["processors"] = items
    write_pipeline(name, data)
    return {"status": "updated", "name": name, "index": index}


@app.patch("/pipelines/{name}/processors/{index}")
def patch_processor(name: str, index: int, patch: Dict[str, Any]):
    data = read_pipeline(name)
    items = data.get("processors", [])
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail="Processor index out of range")
    items[index] = deep_merge(items[index], patch)
    data["processors"] = items
    write_pipeline(name, data)
    return {"status": "patched", "name": name, "index": index}


@app.post("/apply")
def apply(pipelines: Optional[str] = Query(None, description="Comma separated pipeline names")):
    target_list = pipelines.split(",") if pipelines else None
    try:
        output = terraform_apply(target_list)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"output": output}
