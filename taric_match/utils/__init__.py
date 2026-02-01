"""工具函数"""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = Path(os.environ.get(
        "XDG_CONFIG_HOME",
        Path.home() / ".config"
    )) / "taric-match"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_cache_dir() -> Path:
    """获取缓存目录"""
    cache_dir = Path(os.environ.get(
        "XDG_CACHE_HOME",
        Path.home() / ".cache"
    )) / "taric-match"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
