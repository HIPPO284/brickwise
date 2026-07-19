import json
from pathlib import Path
from .hashing import sha256_file
def manifest_for(path:Path,**meta):
    stat=path.stat()
    return {"manifest_version":"1.0","local_path":str(path),"sha256":sha256_file(path),
            "byte_size":stat.st_size,"processing_steps":[],"parent_assets":[],
            "generated_by_tool_version":"brickwise-ml-foundation/0.1.0",**meta}
def write_manifest(path:Path,out:Path,**meta):
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(manifest_for(path,**meta),indent=2,sort_keys=True)+"\n")
