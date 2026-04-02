from __future__ import annotations

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


def get_plugin_data_dir(plugin_name: str = PLUGIN_NAME) -> Path:
    if get_astrbot_data_path is not None:
        return get_astrbot_data_path() / "plugin_data" / plugin_name
    return ROOT_DIR / ".plugin_data_fallback" / plugin_name


def get_storage_paths(plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    base = get_plugin_data_dir(plugin_name)
    return {
        "plugin_data_dir": base,
        "luck_data_file": base / "luck_data.json",
        "fate_cards_file": base / "cards_config.json",
        "func_cards_file": base / "func_cards.json",
        "sign_in_texts_file": base / "sign_in_texts.json",
        "runtime_config_file": base / "webui_runtime_config.json",
        "fate_assets_dir": base / "cards",
        "func_assets_dir": base / "func_cards",
        "func_cards_template_file": CONFIG_DIR / "func_cards.json",
        "legacy_luck_data_file": LEGACY_DATA_DIR / "luck_data.json",
        "legacy_fate_cards_file": CONFIG_DIR / "cards_config.json",
        "legacy_func_cards_file": CONFIG_DIR / "func_cards.json",
        "legacy_sign_in_texts_file": CONFIG_DIR / "sign_in_texts.json",
        "legacy_runtime_config_file": CONFIG_DIR / "webui_runtime_config.json",
        "legacy_fate_assets_dir": LEGACY_ASSETS_DIR / "cards",
        "legacy_func_assets_dir": LEGACY_ASSETS_DIR / "func_cards",
    }


def ensure_plugin_data_dirs(plugin_name: str = PLUGIN_NAME) -> Path:
    paths = get_storage_paths(plugin_name)
    for key in ("plugin_data_dir", "fate_assets_dir", "func_assets_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
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


def migrate_legacy_storage(plugin_name: str = PLUGIN_NAME) -> dict[str, Path]:
    paths = get_storage_paths(plugin_name)
    ensure_plugin_data_dirs(plugin_name)

    _copy_file_if_needed(paths["legacy_luck_data_file"], paths["luck_data_file"])
    _copy_file_if_needed(paths["legacy_fate_cards_file"], paths["fate_cards_file"])
    _copy_file_if_needed(paths["legacy_func_cards_file"], paths["func_cards_file"])
    _copy_file_if_needed(paths["legacy_sign_in_texts_file"], paths["sign_in_texts_file"])
    _copy_file_if_needed(paths["legacy_runtime_config_file"], paths["runtime_config_file"])
    _copy_dir_if_needed(paths["legacy_fate_assets_dir"], paths["fate_assets_dir"])
    _copy_dir_if_needed(paths["legacy_func_assets_dir"], paths["func_assets_dir"])

    return paths
