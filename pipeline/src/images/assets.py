"""Asset library — global (pipeline/global_assets/) and project-scoped (workspace/assets/).

ID formats:
  Legacy (v1):  G-CHR-001-001          (no role suffix — remains valid)
  New (v2):     G-CHR-001-001-BODY     (with role suffix)

Valid roles: BASE, BODY, FACE, EYES, CTX, PART, COMP, LORA, PROP
One BASE per group is enforced on upload.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_SERVER_ROOT = Path(__file__).parent.parent.parent
_GLOBAL_ASSETS_DIR = _SERVER_ROOT / "global_assets"
_INDEX_FILE = "assets_index.json"

_TYPE_MAP = {
    "characters": "CHR",
    "objects": "OBJ",
    "backgrounds": "BG",
    "speech_bubbles": "BUB",
    "sounds": "SND",
    "music": "MUS",
    "effects": "SFX",
}

VALID_ROLES = {"BASE", "BODY", "FACE", "EYES", "CTX", "PART", "COMP", "LORA", "PROP"}
EXEMPT_ROLES = {"BASE", "LORA"}


def _project_assets_dir(workspace: Path) -> Path:
    return workspace / "assets"


def _assets_dir(workspace: Optional[Path], scope: str) -> Path:
    if scope == "global":
        return _GLOBAL_ASSETS_DIR
    if scope == "project" and workspace:
        return _project_assets_dir(workspace)
    raise ValueError("scope must be 'global' or 'project'; 'project' requires workspace")


def _type_code(top_dir: str) -> str:
    return _TYPE_MAP.get(top_dir.lower(), "SCN")


def _scope_prefix(scope: str) -> str:
    return "G" if scope == "global" else "P"


def _build_index(assets_root: Path, scope: str) -> dict:
    """Rebuild asset index from filesystem, preserving existing meta_map entries."""
    prefix = _scope_prefix(scope)
    idx_path = assets_root / _INDEX_FILE

    # Load existing index to preserve meta_map and group_map
    existing: dict = {}
    if idx_path.exists():
        try:
            existing = json.loads(idx_path.read_text())
        except Exception:
            pass

    existing_meta = existing.get("meta_map", {})
    existing_groups = existing.get("group_map", {})

    # Build reverse map: path → existing_id (to preserve IDs for known files)
    path_to_id: dict[str, str] = {v: k for k, v in existing.get("id_map", {}).items()}

    type_groups: dict[str, int] = {}
    type_group_files: dict[str, list] = {}
    type_group_counters: dict[str, int] = {}
    id_map: dict[str, str] = {}

    # Restore existing group counters from group_map
    for gid, gmeta in existing_groups.items():
        parts = gid.split("-")  # G-CHR-001
        if len(parts) == 3:
            tcode = parts[1]
            gnum = int(parts[2])
            type_group_counters[tcode] = max(type_group_counters.get(tcode, 0), gnum)

    for svg_file in sorted(assets_root.rglob("*.svg")):
        rel = svg_file.relative_to(assets_root)
        rel_str = rel.as_posix()
        parts = rel.parts
        if len(parts) < 2:
            continue
        top = parts[0]
        subdir = parts[1] if len(parts) > 2 else ""
        name = svg_file.stem
        tcode = _type_code(top)
        gkey = f"{tcode}:{top}/{subdir}" if subdir else f"{tcode}:{top}"

        # If this path already has an ID in the existing index, preserve it
        if rel_str in path_to_id:
            id_map[path_to_id[rel_str]] = rel_str
            continue

        if gkey not in type_groups:
            type_group_counters[tcode] = type_group_counters.get(tcode, 0) + 1
            type_groups[gkey] = type_group_counters[tcode]
        gnum = type_groups[gkey]
        flist = type_group_files.setdefault(gkey, [])
        if name not in flist:
            flist.append(name)
        inum = flist.index(name) + 1
        asset_id = f"{prefix}-{tcode}-{gnum:03d}-{inum:03d}"
        id_map[asset_id] = rel_str

    # Also scan for .mp3/.wav/.safetensors files
    for media_ext in ("*.mp3", "*.wav", "*.safetensors"):
        for media_file in sorted(assets_root.rglob(media_ext)):
            rel = media_file.relative_to(assets_root)
            rel_str = rel.as_posix()
            if rel_str in path_to_id:
                id_map[path_to_id[rel_str]] = rel_str
                continue
            parts = rel.parts
            if len(parts) < 2:
                continue
            top = parts[0]
            subdir = parts[1] if len(parts) > 2 else ""
            name = media_file.stem
            # Map sounds/music → MUS, sounds/effects → SFX
            if top == "sounds":
                tcode = _TYPE_MAP.get(subdir.lower(), "SND")
            else:
                tcode = _type_code(top)
            gkey = f"{tcode}:{top}/{subdir}" if subdir else f"{tcode}:{top}"
            if gkey not in type_groups:
                type_group_counters[tcode] = type_group_counters.get(tcode, 0) + 1
                type_groups[gkey] = type_group_counters[tcode]
            gnum = type_groups[gkey]
            flist = type_group_files.setdefault(gkey, [])
            if name not in flist:
                flist.append(name)
            inum = flist.index(name) + 1
            asset_id = f"{prefix}-{tcode}-{gnum:03d}-{inum:03d}"
            id_map[asset_id] = rel_str

    index = {
        "version": "2.0",
        "last_updated": datetime.now().isoformat(),
        "scope": scope,
        "id_map": id_map,
        "meta_map": existing_meta,
        "group_map": existing_groups,
    }
    assets_root.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    return index


def _load_index(assets_root: Path, scope: str) -> dict:
    idx_path = assets_root / _INDEX_FILE
    if idx_path.exists():
        try:
            data = json.loads(idx_path.read_text())
            if "meta_map" not in data:
                data["meta_map"] = {}
            if "group_map" not in data:
                data["group_map"] = {}
            return data
        except Exception:
            pass
    return _build_index(assets_root, scope)


def _save_index(assets_root: Path, index: dict) -> None:
    index["last_updated"] = datetime.now().isoformat()
    (assets_root / _INDEX_FILE).write_text(
        json.dumps(index, indent=2, ensure_ascii=False)
    )


def _get_overuse_thresholds() -> dict:
    """Load overuse thresholds from engines.yaml."""
    try:
        import yaml
        cfg_path = _SERVER_ROOT / "config" / "engines.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        return cfg.get("asset_overuse", {
            "global_warn_threshold": 10,
            "project_warn_threshold": 5,
        })
    except Exception:
        return {"global_warn_threshold": 10, "project_warn_threshold": 5}


def _compute_overuse_warnings(assets: list[dict], meta_map: dict) -> list[dict]:
    """Return overuse warnings for assets exceeding thresholds."""
    thresholds = _get_overuse_thresholds()
    global_thresh = thresholds.get("global_warn_threshold", 10)
    project_thresh = thresholds.get("project_warn_threshold", 5)
    warnings = []
    for a in assets:
        asset_id = a["id"]
        meta = meta_map.get(asset_id, {})
        role = meta.get("role", "")
        if role in EXEMPT_ROLES:
            continue
        global_uses = meta.get("global_uses", 0)
        project_uses = meta.get("project_uses", 0)
        if global_uses > global_thresh:
            warnings.append({
                "asset_id": asset_id,
                "name": a.get("name", ""),
                "global_uses": global_uses,
                "project_uses": project_uses,
                "reason": f"global_uses > threshold ({global_thresh})",
            })
        elif project_uses > project_thresh:
            warnings.append({
                "asset_id": asset_id,
                "name": a.get("name", ""),
                "global_uses": global_uses,
                "project_uses": project_uses,
                "reason": f"project_uses > threshold ({project_thresh})",
            })
    return warnings


def list_assets(workspace: Optional[Path] = None, scope: str = "", category: str = "") -> dict:
    """List assets. scope='global'|'project'|'' (both)."""
    results: list[dict] = []
    all_meta: dict[str, dict] = {}

    scopes_to_check = []
    if scope in ("global", ""):
        scopes_to_check.append(("global", _GLOBAL_ASSETS_DIR))
    if scope in ("project", "") and workspace:
        scopes_to_check.append(("project", _project_assets_dir(workspace)))

    for s, assets_root in scopes_to_check:
        if not assets_root.exists():
            continue
        index = _load_index(assets_root, s)
        meta_map = index.get("meta_map", {})
        all_meta.update(meta_map)
        for asset_id, rel_path in index.get("id_map", {}).items():
            cat = "/".join(Path(rel_path).parts[:-1])
            if category and not (cat == category or cat.startswith(category + "/")):
                continue
            full_path = assets_root / rel_path
            meta = meta_map.get(asset_id, {})
            results.append({
                "id": asset_id,
                "name": Path(rel_path).stem,
                "category": cat,
                "scope": s,
                "path": f"{'global_assets' if s == 'global' else 'assets'}/{rel_path}",
                "exists": full_path.exists(),
                "role": meta.get("role", ""),
                "compatible_groups": meta.get("compatible_groups", []),
                "global_uses": meta.get("global_uses", 0),
                "project_uses": meta.get("project_uses", 0),
                "last_used": meta.get("last_used", None),
            })

    categories: dict[str, list] = {}
    for a in results:
        categories.setdefault(a["category"], []).append(a["id"])

    overuse_warnings = _compute_overuse_warnings(results, all_meta)

    return {
        "assets": results,
        "total": len(results),
        "categories": categories,
        "overuse_warnings": overuse_warnings,
    }


def search_assets(
    workspace: Optional[Path] = None,
    query: str = "",
    asset_type: str = "",
    scope: str = "",
    role: str = "",
    semantic: str = "",
    emotion: str = "",
    category: str = "",
) -> dict:
    """Search assets by name/ID/type/role/semantic tags/emotion tags."""
    full = list_assets(workspace=workspace, scope=scope, category=category)
    all_assets = full["assets"]
    all_meta: dict[str, dict] = {}
    for s, assets_root_p in [("global", _GLOBAL_ASSETS_DIR)] + (
        [("project", _project_assets_dir(workspace))] if workspace else []
    ):
        if assets_root_p.exists():
            idx = _load_index(assets_root_p, s)
            all_meta.update(idx.get("meta_map", {}))

    # Build semantic/emotion tag sets from space/comma-separated input
    sem_terms = [t.strip().lower() for t in semantic.replace(",", " ").split() if t.strip()]
    emo_terms = [t.strip().lower() for t in emotion.replace(",", " ").split() if t.strip()]

    if not query and not asset_type and not role and not sem_terms and not emo_terms:
        return {
            "assets": all_assets,
            "total": len(all_assets),
            "overuse_warnings": full["overuse_warnings"],
        }

    q = query.lower()
    matched = []
    for a in all_assets:
        if asset_type and not a["id"].split("-")[1:2] == [asset_type.upper()]:
            continue
        if role and a.get("role", "").upper() != role.upper():
            continue
        if q and q not in a["name"].lower() and q not in a["id"].lower():
            continue
        meta = all_meta.get(a["id"], {})
        if sem_terms:
            tags = [t.lower() for t in meta.get("semantic_tags", [])]
            if not any(term in tags for term in sem_terms):
                continue
        if emo_terms:
            tags = [t.lower() for t in meta.get("emotion_tags", [])]
            if not any(term in tags for term in emo_terms):
                continue
        matched.append(a)

    overuse_warnings = _compute_overuse_warnings(matched, all_meta)
    return {"assets": matched, "total": len(matched), "overuse_warnings": overuse_warnings}


def _next_role_seq(index: dict, group_id: str, role: str) -> int:
    """Return the next sequence number for (group_id, role) pair."""
    prefix = group_id  # e.g. G-CHR-001
    suffix = f"-{role}"
    existing_seqs = []
    for asset_id in index.get("id_map", {}):
        if asset_id.startswith(prefix + "-") and asset_id.endswith(suffix):
            # G-CHR-001-003-BODY → parts[3] = "003"
            parts = asset_id.split("-")
            if len(parts) == 5:
                try:
                    existing_seqs.append(int(parts[3]))
                except ValueError:
                    pass
    return max(existing_seqs, default=0) + 1


def _derive_group_id(assets_root: Path, scope: str, category: str) -> tuple[str, str]:
    """Return (group_id, type_code) for a category path."""
    prefix = _scope_prefix(scope)
    parts = Path(category).parts
    top = parts[0] if parts else "objects"
    subdir = parts[1] if len(parts) > 1 else ""
    tcode = _type_code(top)

    index = _load_index(assets_root, scope)
    group_map: dict = index.get("group_map", {})

    gkey = f"{tcode}:{top}/{subdir}" if subdir else f"{tcode}:{top}"
    # Find existing group for this gkey
    for gid, gmeta in group_map.items():
        if gmeta.get("gkey") == gkey:
            return gid, tcode

    # Assign new group number
    existing_nums = []
    for gid in group_map:
        parts_id = gid.split("-")  # G-CHR-001
        if len(parts_id) == 3 and parts_id[1] == tcode:
            try:
                existing_nums.append(int(parts_id[2]))
            except ValueError:
                pass
    next_num = max(existing_nums, default=0) + 1
    group_id = f"{prefix}-{tcode}-{next_num:03d}"
    return group_id, tcode


def upload_asset(
    workspace: Optional[Path],
    category: str,
    name: str,
    svg_content: str,
    scope: str = "project",
    role: str = "CTX",
    compatible_groups: Optional[list] = None,
    description: str = "",
    semantic_tags: Optional[list] = None,
    emotion_tags: Optional[list] = None,
    visual_energy: float = 0.5,
    attention_weight: float = 0.5,
) -> dict:
    """Upload an SVG (or .safetensors for LORA) asset, auto-generate ID with role suffix."""
    role = role.upper()
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")

    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    meta_map: dict = index.setdefault("meta_map", {})
    group_map: dict = index.setdefault("group_map", {})

    group_id, tcode = _derive_group_id(assets_root, scope, category)

    # Enforce one BASE per group
    if role == "BASE":
        for asset_id, meta in meta_map.items():
            if meta.get("role") == "BASE" and asset_id.startswith(group_id + "-"):
                raise ValueError(
                    f"Group {group_id} already has a BASE asset ({asset_id}). "
                    "Only one BASE per group is allowed."
                )

    # Determine file extension
    if role == "LORA":
        ext = ".safetensors"
    else:
        ext = ".svg"

    target_dir = assets_root / category
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{name}{ext}"
    file_path.write_text(svg_content, encoding="utf-8")

    # Assign role-sequenced ID
    seq = _next_role_seq(index, group_id, role)
    asset_id = f"{group_id}-{seq:03d}-{role}"

    rel = (Path(category) / f"{name}{ext}").as_posix()
    index["id_map"][asset_id] = rel

    # Update group map
    if group_id not in group_map:
        parts_cat = Path(category).parts
        top = parts_cat[0] if parts_cat else "objects"
        subdir = parts_cat[1] if len(parts_cat) > 1 else ""
        gkey = f"{tcode}:{top}/{subdir}" if subdir else f"{tcode}:{top}"
        group_name = parts_cat[-1] if parts_cat else category
        group_map[group_id] = {
            "name": group_name,
            "gkey": gkey,
            "base_id": None,
            "lora_id": None,
        }

    if role == "BASE":
        group_map[group_id]["base_id"] = asset_id
    elif role == "LORA":
        group_map[group_id]["lora_id"] = asset_id

    # Store metadata
    meta_map[asset_id] = {
        "role": role,
        "group_id": group_id,
        "name": name,
        "description": description,
        "semantic_tags": semantic_tags or [],
        "emotion_tags": emotion_tags or [],
        "visual_energy": visual_energy,
        "attention_weight": attention_weight,
        "compatible_groups": compatible_groups or [],
        "global_uses": 0,
        "project_uses": 0,
        "projects_count": 0,
        "last_used": None,
        "created_at": datetime.now().isoformat(),
    }

    _save_index(assets_root, index)

    return {
        "id": asset_id,
        "group_id": group_id,
        "role": role,
        "path": f"{'global_assets' if scope == 'global' else 'assets'}/{rel}",
        "category": category,
        "name": name,
        "scope": scope,
    }


def delete_asset(workspace: Optional[Path], asset_id: str) -> dict:
    """Delete an asset by ID."""
    scope = "global" if asset_id.startswith("G-") else "project"
    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    rel_path = index.get("id_map", {}).get(asset_id)
    if not rel_path:
        raise FileNotFoundError(f"Asset ID '{asset_id}' not found")
    full_path = assets_root / rel_path
    if full_path.exists():
        full_path.unlink()
    # Remove from maps
    index["id_map"].pop(asset_id, None)
    index.get("meta_map", {}).pop(asset_id, None)
    _save_index(assets_root, index)
    return {"deleted": asset_id, "path": rel_path}


def resolve_asset_path(asset_path: str, workspace: Optional[Path] = None) -> Path:
    """Resolve an asset path string to an absolute Path."""
    if asset_path.startswith("global_assets/"):
        full = (_SERVER_ROOT / asset_path).resolve()
        if not str(full).startswith(str(_SERVER_ROOT)):
            raise ValueError("Asset path traversal not allowed")
        return full
    if asset_path.startswith("assets/") and workspace:
        full = (workspace / asset_path).resolve()
        if not str(full).startswith(str(workspace.resolve())):
            raise ValueError("Asset path traversal not allowed")
        return full
    for base in [_GLOBAL_ASSETS_DIR, _SERVER_ROOT / "assets"]:
        candidate = (base / asset_path).resolve()
        if candidate.exists():
            return candidate
    full = (_GLOBAL_ASSETS_DIR / asset_path).resolve()
    if not str(full).startswith(str(_GLOBAL_ASSETS_DIR)):
        raise ValueError("Asset path traversal not allowed")
    return full


def resolve_asset_by_id(asset_id: str, workspace: Optional[Path] = None) -> Path:
    """Resolve an asset ID to an absolute Path."""
    scope = "global" if asset_id.startswith("G-") else "project"
    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    rel_path = index.get("id_map", {}).get(asset_id)
    if not rel_path:
        raise FileNotFoundError(f"Asset ID '{asset_id}' not found in index")
    return assets_root / rel_path


def increment_asset_uses(
    asset_id: str,
    workspace: Optional[Path] = None,
    global_inc: int = 1,
    project_inc: int = 1,
) -> None:
    """Increment global_uses and project_uses for an asset, update last_used."""
    scope = "global" if asset_id.startswith("G-") else "project"
    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    meta_map = index.setdefault("meta_map", {})
    if asset_id not in meta_map:
        meta_map[asset_id] = {
            "role": "",
            "global_uses": 0,
            "project_uses": 0,
            "last_used": None,
        }
    meta_map[asset_id]["global_uses"] = meta_map[asset_id].get("global_uses", 0) + global_inc
    meta_map[asset_id]["project_uses"] = meta_map[asset_id].get("project_uses", 0) + project_inc
    meta_map[asset_id]["last_used"] = datetime.now().isoformat()
    _save_index(assets_root, index)


def get_asset_stats(asset_id: str, workspace: Optional[Path] = None) -> dict:
    """Return file size, existence info, and usage counters for an asset ID."""
    scope = "global" if asset_id.startswith("G-") else "project"
    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    rel_path = index.get("id_map", {}).get(asset_id)
    if not rel_path:
        return {"asset_id": asset_id, "found": False}
    full_path = assets_root / rel_path
    meta = index.get("meta_map", {}).get(asset_id, {})

    thresholds = _get_overuse_thresholds()
    return {
        "asset_id": asset_id,
        "found": True,
        "path": rel_path,
        "exists": full_path.exists(),
        "size_bytes": full_path.stat().st_size if full_path.exists() else 0,
        "role": meta.get("role", ""),
        "group_id": meta.get("group_id", ""),
        "global_uses": meta.get("global_uses", 0),
        "project_uses": meta.get("project_uses", 0),
        "last_used": meta.get("last_used", None),
        "compatible_groups": meta.get("compatible_groups", []),
        "global_threshold": thresholds.get("global_warn_threshold", 10),
        "project_threshold": thresholds.get("project_warn_threshold", 5),
    }


def save_comp_asset(
    group_id: str,
    name: str,
    png_data: bytes,
    workspace: Optional[Path] = None,
    scope: str = "global",
) -> dict:
    """Save a composited PNG result as a COMP asset and register it."""
    assets_root = _assets_dir(workspace, scope)
    index = _load_index(assets_root, scope)
    meta_map = index.setdefault("meta_map", {})

    seq = _next_role_seq(index, group_id, "COMP")
    asset_id = f"{group_id}-{seq:03d}-COMP"

    # Determine directory from group_map
    group_map = index.get("group_map", {})
    group_meta = group_map.get(group_id, {})
    gkey = group_meta.get("gkey", "")
    # gkey format: "CHR:characters/crowd"
    if ":" in gkey:
        cat_path = gkey.split(":", 1)[1]
    else:
        cat_path = "objects/composed"
    comp_dir = assets_root / cat_path / "composed"
    comp_dir.mkdir(parents=True, exist_ok=True)
    file_path = comp_dir / f"{name}.png"
    file_path.write_bytes(png_data)

    rel = (Path(cat_path) / "composed" / f"{name}.png").as_posix()
    index["id_map"][asset_id] = rel
    meta_map[asset_id] = {
        "role": "COMP",
        "group_id": group_id,
        "name": name,
        "global_uses": 0,
        "project_uses": 0,
        "last_used": None,
        "created_at": datetime.now().isoformat(),
    }
    _save_index(assets_root, index)

    return {
        "id": asset_id,
        "path": f"{'global_assets' if scope == 'global' else 'assets'}/{rel}",
        "group_id": group_id,
        "name": name,
    }


def generate_asset_svg(
    engine,
    workspace: Optional[Path],
    prompt: str,
    negative_prompt: str,
    save_as: str,
    scope: str = "project",
) -> dict:
    """Generate PNG via image engine and optionally trace to SVG."""
    import shutil
    import tempfile

    from src.entities.prompts import FramePrompt

    fp = FramePrompt(
        frame_id=0, scene_id=0, start=0.0, end=1.0, duration=1.0,
        prompt=f"flat design, flat vector art, {prompt}",
        negative_prompt=negative_prompt or "realistic, photo, complex shading",
    )

    assets_root = _assets_dir(workspace, scope) if save_as else None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        png_src = engine.generate(fp, tmp_path)

        if save_as and assets_root:
            final_png = (assets_root / save_as).with_suffix(".png")
            final_png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png_src, final_png)
            png_result = str(final_png)
        else:
            final_png = tmp_path / "generated.png"
            shutil.copy2(png_src, final_png)
            png_result = str(png_src)

        svg_result = None
        svg_hint = ""
        try:
            import vtracer
            svg_out = Path(png_result).with_suffix(".svg")
            vtracer.convert_image_to_svg_py(
                str(final_png), str(svg_out), colormode="color", filter_speckle=4
            )
            svg_result = str(svg_out)
            svg_hint = f"SVG saved: {svg_out.name}. "
            if save_as and assets_root:
                _build_index(assets_root, scope)
        except (ImportError, Exception):
            svg_hint = "vtracer not available — SVG tracing skipped. "

    return {
        "png_path": png_result,
        "svg_path": svg_result,
        "prompt_used": fp.prompt,
        "svg_hint": svg_hint,
    }
