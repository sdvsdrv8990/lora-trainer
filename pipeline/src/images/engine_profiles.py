import json
from pathlib import Path

import yaml

from src.entities.engine_profile import EngineProfile

_PROFILES_DIR_KEY = "profiles_dir"
_PROFILE_KEY = "profile"
_DEFAULT_PROFILES_DIR = "config/image_engines"

_BASE_DIR = Path(__file__).parent.parent.parent


def _get_profiles_dir(engines_cfg: dict) -> Path:
    image_cfg = engines_cfg.get("image", {})
    profiles_dir = image_cfg.get(_PROFILES_DIR_KEY, _DEFAULT_PROFILES_DIR)
    return (_BASE_DIR / profiles_dir).resolve()


def get_active_profile_id(engines_cfg: dict) -> str:
    return engines_cfg.get("image", {}).get(_PROFILE_KEY, "stub")


def load_profile(engines_cfg: dict, profile_id: str) -> EngineProfile:
    profiles_dir = _get_profiles_dir(engines_cfg)
    profile_path = profiles_dir / f"{profile_id}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{profile_id}' not found in {profiles_dir}")
    return EngineProfile.model_validate(json.loads(profile_path.read_text()))


def list_profiles(engines_cfg: dict) -> list[dict]:
    profiles_dir = _get_profiles_dir(engines_cfg)
    active = get_active_profile_id(engines_cfg)
    if not profiles_dir.exists():
        return []
    result = []
    for f in sorted(profiles_dir.glob("*.json")):
        try:
            profile = EngineProfile.model_validate(json.loads(f.read_text()))
            result.append({
                "id": f.stem,
                "name": profile.name,
                "engine": profile.engine,
                "model_id": profile.model_id,
                "active": f.stem == active,
            })
        except Exception:
            pass
    return result


def switch_profile(engines_yaml_path: Path, profile_id: str, engines_cfg: dict) -> dict:
    """Update engines.yaml active profile and mutate engines_cfg in-place."""
    profiles_dir = _get_profiles_dir(engines_cfg)
    profile_path = profiles_dir / f"{profile_id}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{profile_id}' not found")
    profile = EngineProfile.model_validate(json.loads(profile_path.read_text()))

    cfg = yaml.safe_load(engines_yaml_path.read_text())
    if "image" not in cfg:
        cfg["image"] = {}
    cfg["image"][_PROFILE_KEY] = profile_id
    cfg["image"]["engine"] = profile.engine
    engines_yaml_path.write_text(yaml.dump(cfg, allow_unicode=True, default_flow_style=False))

    engines_cfg.setdefault("image", {})[_PROFILE_KEY] = profile_id
    engines_cfg["image"]["engine"] = profile.engine

    return {
        "active_profile": profile_id,
        "profile_name": profile.name,
        "engine": profile.engine,
    }
