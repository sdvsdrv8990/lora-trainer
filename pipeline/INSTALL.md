# Installation Guide

---

## Quick Start (CPU / no GPU)

```bash
cd pipeline
python3.10 -m venv venv
source venv/bin/activate
pip install -e "."
python main.py start
```

This starts the MCP server with the stub image engine (1×1 placeholder PNGs) and espeak TTS. No GPU required.

---

## Step 2: Compositing (PIL + CairoSVG)

SVG layer compositing requires Pillow and cairosvg:

```bash
pip install -e ".[compositing]"
# Installs: Pillow, cairosvg, lxml
```

**Verify:**
```bash
python -c "from PIL import Image; import cairosvg; print('compositing ok')"
```

On Fedora/RHEL, cairosvg requires system Cairo:
```bash
sudo dnf install cairo cairo-devel gobject-introspection-devel
```

---

## Step 3: PNG → SVG Tracing (vtracer)

Tracing generated PNGs to SVG for the asset library:

```bash
pip install -e ".[tracing]"
# Installs: vtracer
```

---

## Step 4: Image Generation — NVIDIA / CUDA

```bash
pip install -e ".[generation]"
# Installs: diffusers, accelerate, transformers

# PyTorch with CUDA (check pytorch.org for your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

Set the engine profile in `config/engines.yaml`:
```yaml
image:
  profile: "sdxl_base"
```

---

## Step 4: Image Generation — AMD / ROCm

Tested on RDNA 2 (RX 6000 series) and RDNA 3 (RX 7000 series).

### 1. Install ROCm

```bash
# Fedora/RHEL
sudo dnf install rocm-hip-sdk rocm-opencl-sdk

# Ubuntu
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_*.deb
sudo apt install ./amdgpu-install_*.deb
sudo amdgpu-install --usecase=rocm
sudo usermod -aG video,render $USER
# Log out and back in
```

### 2. Install PyTorch for ROCm

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
```

### 3. Install diffusers

```bash
pip install -e ".[generation]"
```

### 4. Set GFX override

The HSA_OVERRIDE_GFX_VERSION environment variable is required:

| GPU family | Override value |
|---|---|
| RDNA 2 (RX 6000) | `10.3.0` |
| RDNA 3 (RX 7000) | `11.0.0` |

Add to `start.sh` or your shell profile:
```bash
export HSA_OVERRIDE_GFX_VERSION=10.3.0   # RDNA 2
# or
export HSA_OVERRIDE_GFX_VERSION=11.0.0   # RDNA 3
```

The pipeline server reads `config/engines.yaml` which includes `device: "rocm"` in the diffusers profiles.

### 5. Verify GPU detection

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

On ROCm, `torch.cuda.is_available()` returns `True` when the setup is correct.

### 6. Switch to ROCm profile

```yaml
# config/engines.yaml
image:
  profile: "sd15_deliberate"   # or sdxl_base
```

Or via MCP tool:
```
pipeline_switch_engine_profile(profile_id="sd15_deliberate")
```

---

## Step 5: Transcription (faster-whisper)

```bash
pip install faster-whisper
```

Always runs on CPU (`device="cpu"`, `compute_type="int8"`). No GPU path currently.

---

## Step 6: Cloudflare Tunnel (remote Claude.ai access)

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

# Terminal 1 — server
cd pipeline && source venv/bin/activate && python main.py start

# Terminal 2 — tunnel
cloudflared tunnel --url http://localhost:8765
```

Copy the tunnel URL (e.g. `https://random-name.trycloudflare.com`) and set:
```bash
export VIDPIPE_PUBLIC_URL="https://random-name.trycloudflare.com"
```

Then restart the server. The OAuth discovery endpoint becomes available at:
```
https://random-name.trycloudflare.com/.well-known/oauth-protected-resource/mcp
```

Add the tunnel URL as a custom integration in Claude.ai.

---

## Step 7: Free Audio Import (Freesound)

`pipeline_search_free_audio` and `pipeline_save_free_audio` require a Freesound API key.

1. Register at freesound.org and create an API application.
2. Copy your API key into `config/audio_sources.yaml`:

```yaml
freesound:
  api_key: "your_api_key_here"
  base_url: "https://freesound.org/apiv2"

pixabay:
  api_key: ""          # optional — not yet integrated
  base_url: "https://pixabay.com/api"

jamendo:
  api_key: ""          # optional — not yet integrated
  base_url: "https://api.jamendo.com/v3.0"
```

Without a key, `pipeline_search_free_audio` returns `{"ok": false, "error": "freesound api_key not configured"}`.

---

## Full Install (all features)

```bash
pip install -e ".[compositing,tracing,generation]"
pip install faster-whisper
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
```

---

## Checking the MCP server

After starting, verify with the MCP SDK:
```bash
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def check():
    async with streamablehttp_client('http://localhost:8765/mcp') as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Tools: {len(tools.tools)}')
            for t in tools.tools:
                print(f'  {t.name}')

asyncio.run(check())
"
```

Expected: 83 tools listed.
