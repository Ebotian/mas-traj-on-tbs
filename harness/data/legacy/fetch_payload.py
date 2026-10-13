import os
import shutil
import time

from huggingface_hub import snapshot_download

REPO = "harborframework/terminal-bench-science-lfs"
REV = "7343cfce483a6efa58977d0c8494a1cefb301ccf"
PATTERN = "tumor-immune-interface/input/*"
DST = "/home/ebt/harbor-runs/dataset-build/payload"

os.makedirs(DST, exist_ok=True)
for attempt in range(1, 41):
    try:
        p = snapshot_download(
            REPO,
            repo_type="dataset",
            revision=REV,
            allow_patterns=PATTERN,
            max_workers=1,
        )
        src = os.path.join(p, "tumor-immune-interface", "input")
        if os.path.isdir(DST):
            shutil.rmtree(DST)
        shutil.copytree(src, DST)
        print("DONE ->", DST, flush=True)
        break
    except Exception as e:
        print(f"attempt {attempt} failed: {type(e).__name__}: {e}", flush=True)
        time.sleep(3)
else:
    raise SystemExit("all attempts failed")
