"""
配置加载器模块

从YAML配置文件加载音阶、节奏、和弦进行、风格等定义，
替代原有的硬编码预设。
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any
import yaml

from .theory import ScaleDegree
from .rhythms import RhythmPattern
from .motif import MotifWeight


# 配置文件根目录（模块级常量）
_CONFIG_DIR = Path(__file__).parent.parent / "config"

# 缓存（模块级变量）
_cache: Dict[str, Any] = {}


def _load_yaml(relative_path: str) -> Dict:
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

def load_scales() -> Dict[str, List[ScaleDegree]]:
    """加载音阶库"""
    data = _load_yaml("scales.yml")
    scales_dict = {}
    
    for scale_name, scale_info in data['scales'].items():
        degrees = []
        for degree_data in scale_info['degrees']:
            number, accidental = degree_data
            degrees.append(ScaleDegree(number, accidental))
        scales_dict[scale_name] = degrees
    
    return scales_dict


# ===== 节奏加载 =====

def load_rhythm_patterns(time_signature: str) -> Dict[str, RhythmPattern]:
    """加载节奏型库"""
    if time_signature == '4/4':
        filename = "rhythms/patterns_4beat.yml"
    elif time_signature == '3/4':
        filename = "rhythms/patterns_3beat.yml"
    else:
        raise ValueError(f"不支持的拍号: {time_signature}")
    
    data = _load_yaml(filename)
    patterns = {}
    
    for pattern_name, pattern_info in data['patterns'].items():
        durations = pattern_info['durations']
        accents = pattern_info['accents']
        patterns[pattern_name] = (durations, accents)
    
    return patterns


# ===== 和弦进行加载 =====

def load_progressions(progression_file: str) -> Dict[str, str]:
    """加载和弦进行库"""
    data = _load_yaml(progression_file)
    progressions = {}
    
    for prog_key, prog_info in data['progressions'].items():
        progressions[prog_key] = prog_info['name']
    
    return progressions


def load_multiple_progressions(progression_sources: List[str]) -> Dict[str, str]:
    """加载多个和弦进行库并合并"""
    all_progressions = {}
    for source in progression_sources:
        progressions = load_progressions(source)
        all_progressions.update(progressions)
    return all_progressions

# ===== 动机模板库加载 =====

def load_motifs() -> Dict[str, Dict[str, Any]]:
    """加载动机模板库"""
    data = _load_yaml("motifs.yml")
    return data["motifs"]

# ===== 风格加载 =====

def load_style(style_name: str) -> Dict[str, Any]:
    """加载风格配置"""
    return _load_yaml(f"styles/{style_name}.yml")


def get_style_rhythm_weights(style_name: str) -> List[Tuple[int, str]]:
    """获取风格的节奏权重列表"""
    style_config = load_style(style_name)
    rhythm_weights = []
    
    for entry in style_config['rhythm_weights']:
        weight = entry['weight']
        pattern = entry['pattern']
        rhythm_weights.append((weight, pattern))
    
    return rhythm_weights


def get_style_motif_weights(style_name: str) -> List[MotifWeight]:
    """获取风格的动机权重列表 (motif_name)"""
    style_config = load_style(style_name)
    motif_weights = []
    for entry in style_config['motif_weights']:
        weight = entry['weight']
        motif_name = entry['type']
        motif_weights.append((weight, motif_name))
    return motif_weights


def get_style_progressions(style_name: str) -> Dict[str, str]:
    """获取风格可用的和弦进行"""
    style_config = load_style(style_name)
    sources = style_config.get('progression_sources', [])
    return load_multiple_progressions(sources)


def list_available_styles() -> List[str]:
    """列出所有可用的风格名称"""
    styles_dir = _CONFIG_DIR / "styles"
    if not styles_dir.exists():
        return []
    
    return [
        f.stem for f in styles_dir.glob("*.yml")
        if f.is_file()
    ]
