#!/bin/bash
set -euo pipefail

echo "=== LoRA Trainer Setup for AMD/ROCm ==="

python3.10 --version || { echo "ERROR: Python 3.10 required"; exit 1; }

python3.10 -m venv venv
source venv/bin/activate

pip install --upgrade pip wheel

if [ ! -d "sd-scripts" ]; then
    git clone https://github.com/kohya-ss/sd-scripts.git
fi

cd sd-scripts
pip install -r requirements.txt
cd ..

pip uninstall torch torchvision torchaudio -y || true
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3

pip install -e ".[dev]"

TOKENIZER_FILE="sd-scripts/library/sdxl_train_util.py"
if [ -f "$TOKENIZER_FILE" ]; then
    sed -i 's|TOKENIZER1_PATH = .*|TOKENIZER1_PATH = "openai/clip-vit-large-patch14"|' "$TOKENIZER_FILE"
    sed -i 's|TOKENIZER2_PATH = .*|TOKENIZER2_PATH = "openai/clip-vit-large-patch14"|' "$TOKENIZER_FILE"
    echo "Tokenizer fix applied"
fi

echo
echo "Configure accelerate now. Recommended answers:"
echo "- distributed training: No"
echo "- machine count: 1"
echo "- mixed precision: fp16"
echo
accelerate config || true

echo "Setup complete."
echo "Run: source venv/bin/activate && python train.py --images ./images --dry-run"
