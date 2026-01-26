"""
配置加载器模块

从YAML配置文件加载音阶、节奏、和弦进行、风格等定义，
替代原有的硬编码预设。
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

from .theory import ScaleDegree
from .rhythms import RhythmPattern
from .motif import MotifEntry
from .bass import BassPattern
from .styles import Style


# 配置文件根目录（模块级常量）
_CONFIG_DIR = Path(__file__).parent.parent / "config"

# 缓存（模块级变量）
_cache: dict[str, Any] = {}


def _load_yaml(relative_path: str) -> dict[str, Any]:
    """加载YAML文件（带缓存）"""
    if relative_path in _cache:
        return _cache[relative_path]
    
    file_path = _CONFIG_DIR / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    _cache[relative_path] = data
    return data


# ===== 音阶加载 =====

class ScaleEntry(BaseModel):
    """音阶配置文件条目格式"""
    name: str | None = None
    description: str | None = None
    degrees: list[ScaleDegree]


class ScaleLib(BaseModel):
    """整个音阶库的格式"""
    scales: dict[str, ScaleEntry]


def load_scales() -> dict[str, list[ScaleDegree]]:
    """加载音阶库"""
    data = _load_yaml("scales.yml")
    scale_lib = ScaleLib.model_validate(data).scales
    return { n: s.degrees for n, s in scale_lib.items() }


# ===== 节奏加载 =====

class RhythmLib(BaseModel):
    """整个音阶库的格式"""

    patterns: dict[str, RhythmPattern]

    @field_validator("patterns", mode="before")
    @classmethod
    def patterns_validator(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return { str(k): v for k, v in data.items() }
        else:
            raise ValueError(f"Invalid Rhythm Library: {data} should be a mapping from rhythm name to the pattern")


def load_rhythm_patterns(time_sig: str) -> dict[str, RhythmPattern]:
    """加载节奏型库"""
    if time_sig == '4/4':
        filename = "rhythms/patterns_4beat.yml"
    elif time_sig == '3/4':
        filename = "rhythms/patterns_3beat.yml"
    else:
        raise ValueError(f"不支持的拍号: {time_sig}")
    
    data = _load_yaml(filename)
    rhythm_lib = RhythmLib.model_validate(data).patterns
    return rhythm_lib


# ===== 和弦进行加载 =====

class ProgressionEntry(BaseModel):
    name: str
    description: str | None = None


class ProgressionLib(BaseModel):
    progressions: dict[str, ProgressionEntry]


def load_progressions(progression: str) -> dict[str, str]:
    """加载和弦进行库"""
    progression_file = f"progressions/{progression}.yml"
    data = _load_yaml(progression_file)
    progression_lib = ProgressionLib.model_validate(data)
    return { k : v.name for k, v in progression_lib.progressions.items() }


def load_multiple_progressions(progression_sources: list[str]) -> dict[str, str]:
    """加载多个和弦进行库并合并"""
    all_progressions = {}
    for source in progression_sources:
        progressions = load_progressions(source)
        all_progressions.update(progressions)
    return all_progressions


def list_available_progression_libs() -> list[str]:
    """列出所有可用的风格名称"""
    progressions_dir = _CONFIG_DIR / "progressions"
    if not progressions_dir.exists():
        return []
    return [
        f.stem for f in progressions_dir.glob("*.yml")
        if f.is_file()
    ]


# ===== 动机模板库加载 =====

class MotifLib(BaseModel):
    """整个音阶库的格式"""
    motifs: dict[str, MotifEntry]


def load_motifs() -> dict[str, MotifEntry]:
    """加载动机模板库"""
    data = _load_yaml("motifs.yml")
    return MotifLib.model_validate(data).motifs


# ===== 低音模板库加载 =====

class BassLib(BaseModel):
    bass: dict[str, BassPattern]

def load_bass_patterns(time_signature: str) -> dict[str, BassPattern]:
    """加载节奏型库"""
    if time_signature == '4/4':
        filename = "bass/patterns_4beat.yml"
    elif time_signature == '3/4':
        filename = "bass/patterns_3beat.yml"
    else:
        raise ValueError(f"不支持的拍号: {time_signature}")
    
    data = _load_yaml(filename)
    return BassLib.model_validate(data).bass


def list_available_bass_patterns() -> list[str]:
    """列出所有可用的低音模式名称，不论拍号"""    
    return list(set(load_bass_patterns("4/4").keys())
        .union(set(load_bass_patterns("3/4").keys())))


# ===== 风格加载 =====

def list_available_styles() -> list[str]:
    """列出所有可用的风格名称"""
    styles_dir = _CONFIG_DIR / "styles"
    if not styles_dir.exists():
        return []
    
    return [
        f.stem for f in styles_dir.glob("*.yml")
        if f.is_file()
    ]


def load_style(style_name: str) -> Style:
    """加载风格配置"""
    data = _load_yaml(f"styles/{style_name}.yml")
    return Style.model_validate(data)
