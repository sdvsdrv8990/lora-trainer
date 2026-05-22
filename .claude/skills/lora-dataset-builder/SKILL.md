---
name: lora-dataset-builder
description: Use when changing lora-trainer dataset preparation, image discovery, caption generation, trigger words, repeat directories, or kohya dataset layout.
---

# lora-dataset-builder

## Dataset Contract

Kohya expects:

```text
dataset/
└── {repeats}_{trigger}/
    ├── 0001.png
    ├── 0001.txt
    ├── 0002.jpg
    └── 0002.txt
```

Each caption file should include the trigger word. Existing captions are preserved and prefixed
with the trigger if missing.

## Supported Inputs

Supported image extensions are `.png`, `.jpg`, `.jpeg`, `.webp`, and `.bmp`.

## Change Rules

- Never mutate the user's original image folder.
- Copy into `.work/dataset`.
- Keep file names deterministic.
- Add or update tests in `tests/test_dataset.py` for any layout or caption behavior change.
