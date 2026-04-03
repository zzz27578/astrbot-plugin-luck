from __future__ import annotations

import json
import shutil
from pathlib import Path

try:
    from astrbot.core.utils.astrbot_path import get_astrbot_data_path  # type: ignore
except Exception:  # pragma: no cover - 旧版本/脱离 AstrBot 环境时兜底
    get_astrbot_data_path = None


PLUGIN_NAME = "luck_rank"
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
LEGACY_DATA_DIR = ROOT_DIR / "data"
LEGACY_ASSETS_DIR = ROOT_DIR / "assets"
DEFAULT_PROFILE_NAME = "default"


def get_plugin_data_dir(plugin_name: str = PLUGIN_NAME) -> Path:
    if get_astrbot_data_path is not None:
        return Path(get_astrbot_data_path()) / "plugin_data" / plugin_name
    return ROOT_DIR / ".plugin_data_fallback" / plugin_name


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_base_storage_paths(plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    base = get_plugin_data_dir(plugin_name)
    return {
        "plugin_data_dir": base,
        "profiles_dir": base / "profiles",
        "group_data_dir": base / "group_data",
        "legacy_dir": base / "legacy",
        "group_profile_map_file": base / "group_profile_map.json",
        "legacy_luck_data_file": LEGACY_DATA_DIR / "luck_data.json",
        "legacy_fate_cards_file": CONFIG_DIR / "cards_config.json",
        "legacy_func_cards_file": CONFIG_DIR / "func_cards.json",
        "legacy_sign_in_texts_file": CONFIG_DIR / "sign_in_texts.json",
        "legacy_runtime_config_file": CONFIG_DIR / "webui_runtime_config.json",
        "legacy_fate_assets_dir": LEGACY_ASSETS_DIR / "cards",
        "legacy_func_assets_dir": LEGACY_ASSETS_DIR / "func_cards",
    }


def get_profile_storage_paths(profile_name: str = DEFAULT_PROFILE_NAME, plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    base_paths = get_base_storage_paths(plugin_name)
    profile_dir = base_paths["profiles_dir"] / profile_name
    return {
        **base_paths,
        "profile_name": Path(profile_name),
        "profile_dir": profile_dir,
        "fate_cards_file": profile_dir / "cards_config.json",
        "func_cards_file": profile_dir / "func_cards.json",
        "sign_in_texts_file": profile_dir / "sign_in_texts.json",
        "runtime_config_file": profile_dir / "webui_runtime_config.json",
        "fate_assets_dir": profile_dir / "cards",
        "func_assets_dir": profile_dir / "func_cards",
        "func_cards_template_file": CONFIG_DIR / "func_cards.json",
    }


def get_group_storage_paths(group_id: str, plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    base_paths = get_base_storage_paths(plugin_name)
    group_dir = base_paths["group_data_dir"] / str(group_id)
    return {
        **base_paths,
        "group_id": Path(str(group_id)),
        "group_dir": group_dir,
        "luck_data_file": group_dir / "luck_data.json",
    }


def ensure_plugin_data_dirs(plugin_name: str = PLUGIN_NAME) -> Path:
    paths = get_base_storage_paths(plugin_name)
    for key in ("plugin_data_dir", "profiles_dir", "group_data_dir", "legacy_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
    map_file = paths["group_profile_map_file"]
    if not map_file.exists():
        _write_json(map_file, {})
    return paths["plugin_data_dir"]


def _copy_file_if_needed(src: Path, dst: Path):
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_dir_if_needed(src: Path, dst: Path):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == ".gitkeep":
            continue
        target = dst / item.name
        if item.is_dir():
            _copy_dir_if_needed(item, target)
        elif not target.exists():
            shutil.copy2(item, target)


def ensure_profile_dirs(profile_name: str = DEFAULT_PROFILE_NAME, plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    paths = get_profile_storage_paths(profile_name, plugin_name)
    ensure_plugin_data_dirs(plugin_name)
    for key in ("profile_dir", "fate_assets_dir", "func_assets_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def ensure_group_dirs(group_id: str, plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    paths = get_group_storage_paths(group_id, plugin_name)
    ensure_plugin_data_dirs(plugin_name)
    paths["group_dir"].mkdir(parents=True, exist_ok=True)
    return paths


def get_group_profile_map(plugin_name: str = PLUGIN_NAME) -> dict[str, str]:
    base_paths = get_base_storage_paths(plugin_name)
    return _read_json(base_paths["group_profile_map_file"], {}) or {}


def save_group_profile_map(data: dict[str, str], plugin_name: str = PLUGIN_NAME):
    base_paths = get_base_storage_paths(plugin_name)
    _write_json(base_paths["group_profile_map_file"], data)


def bind_group_to_profile(group_id: str, profile_name: str, plugin_name: str = PLUGIN_NAME):
    mapping = get_group_profile_map(plugin_name)
    mapping[str(group_id)] = profile_name
    save_group_profile_map(mapping, plugin_name)


def ensure_default_profile(plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    paths = ensure_profile_dirs(DEFAULT_PROFILE_NAME, plugin_name)
    _copy_file_if_needed(paths["legacy_fate_cards_file"], paths["fate_cards_file"])
    _copy_file_if_needed(paths["legacy_func_cards_file"], paths["func_cards_file"])
    _copy_file_if_needed(paths["legacy_sign_in_texts_file"], paths["sign_in_texts_file"])
    _copy_file_if_needed(paths["legacy_runtime_config_file"], paths["runtime_config_file"])
    _copy_dir_if_needed(paths["legacy_fate_assets_dir"], paths["fate_assets_dir"])
    _copy_dir_if_needed(paths["legacy_func_assets_dir"], paths["func_assets_dir"])
    return paths


def get_or_create_group_profile(group_id: str, plugin_name: str = PLUGIN_NAME) -> str:
    ensure_default_profile(plugin_name)
    mapping = get_group_profile_map(plugin_name)
    group_key = str(group_id)
    profile_name = mapping.get(group_key)
    if not profile_name:
        profile_name = DEFAULT_PROFILE_NAME
        mapping[group_key] = profile_name
        save_group_profile_map(mapping, plugin_name)
    ensure_profile_dirs(profile_name, plugin_name)
    return profile_name


def get_runtime_context(group_id: str, plugin_name: str = PLUGIN_NAME) -> dict[str, Path | str]:
    profile_name = get_or_create_group_profile(group_id, plugin_name)
    group_paths = ensure_group_dirs(group_id, plugin_name)
    profile_paths = ensure_profile_dirs(profile_name, plugin_name)
    return {
        **group_paths,
        **profile_paths,
        "active_group_id": str(group_id),
        "active_profile_name": profile_name,
    }


def migrate_legacy_storage(plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    ensure_plugin_data_dirs(plugin_name)
    default_paths = ensure_default_profile(plugin_name)
    base_paths = get_base_storage_paths(plugin_name)
    legacy_global_file = base_paths["legacy_dir"] / "legacy_global_luck_data.json"
    _copy_file_if_needed(base_paths["legacy_luck_data_file"], legacy_global_file)
    return {
        **base_paths,
        **default_paths,
        "legacy_global_luck_data_file": legacy_global_file,
    }
