#!/usr/bin/env python3
"""
Generate large dataset files in datasets/ for performance testing.
This writes repeating ASCII data in chunks to avoid high memory.

Files created:
- 100MB.txt
- 200MB.txt
- 400MB.txt
- 800MB.txt

Run from the HyPas-B directory:
python generate_large_datasets.py
"""
from pathlib import Path

sizes_mb = [100, 200, 400, 600, 800]
out_dir = Path('datasets')
out_dir.mkdir(parents=True, exist_ok=True)

# Use the provided 1KB file as the repeating block. This avoids inventing synthetic data
# and produces realistic (copied) content for each large file.
source_file = out_dir / '1KB.txt'
if not source_file.exists():
    raise SystemExit(f"Source file not found: {source_file}. Please place the 1KB template at {source_file}")

content = source_file.read_bytes()
chunk_len = len(content)
if chunk_len == 0:
    raise SystemExit(f"Source file {source_file} is empty")

for mb in sizes_mb:
    path = out_dir / f"{mb}MB.txt"
    target_bytes = mb * 1024 * 1024
    repeats = target_bytes // chunk_len
    remainder = target_bytes % chunk_len

    print(f"Creating {path} ({mb} MB): chunk={chunk_len} bytes, repeats={repeats}, remainder={remainder} bytes")
    written = 0
    with path.open('wb') as f:
        # write full repeats in a loop to avoid building a huge in-memory buffer
        for i in range(repeats):
            f.write(content)
            written += chunk_len
            # occasional progress update for long runs
            if repeats >= 10 and (i + 1) % (max(1, repeats // 10)) == 0:
                pct = int((i + 1) / repeats * 100)
                print(f"  {pct}% ({(i+1)*chunk_len // (1024*1024)} MB) written...")

        # write remainder (partial chunk) if needed
        if remainder:
            f.write(content[:remainder])
            written += remainder

    # final sanity print
    print(f"Wrote {written} bytes ({written / (1024*1024):.2f} MB) to {path}")

print("Done.")
