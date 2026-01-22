"""
音乐理论模块：音阶与和声预设的程序化生成

提供：
- 音名与半音映射
- Pitch 类型表示音高（音名 + 八度）
- 常见音阶（大调、小调、Dorian、多种五声音阶、Gypsy）生成
- 根据音阶叠置三度生成和弦（triad / seventh）
- 依据数字和弦标记生成指定调性的和声进行
"""

import re
from dataclasses import dataclass, field
from functools import partial
from typing import Callable, Dict, List, NewType, Optional, Tuple


# 音名集合（小写 + 升号，Alda 兼容）
NOTES_SHARP: List[str] = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
FLAT_TO_SHARP: Dict[str, str] = {'bb': 'a#', 'db': 'c#', 'eb': 'd#', 'gb': 'f#', 'ab': 'g#', 'cb': 'b', 'fb': 'e'}
ENHARMONIC: Dict[str, str] = {'b#': 'c', 'e#': 'f'}


@dataclass(frozen=True)
class ScaleDegree:
    """音阶度数：数字(1+) + 变音记号。支持 1-7 表示音阶内度数，8+ 表示跨八度（如 9=2+12, 11=4+12, 13=6+12）。
    
    示例：
        ScaleDegree(1, 0)   -> 1（主音）
        ScaleDegree(3, -1)  -> ♭3
        ScaleDegree(4, 1)   -> ♯4
        ScaleDegree(9, 0)   -> 9（= 2 高一八度，用于和弦扩展）
    """
    number: int        # 1-7 为音阶内，8+ 表示跨八度（9=2+12, 11=4+12, 13=6+12）
    accidental: int    # -1=♭, 0=自然, 1=♯
    
    def to_semitones(self) -> int:
        """转换为相对主音的半音数（基于大调音阶）。"""
        # 大调音阶基础半音数: 1=0, 2=2, 3=4, 4=5, 5=7, 6=9, 7=11
        major_semitones = [0, 2, 4, 5, 7, 9, 11]
        
        if self.number <= 7:
            base = major_semitones[self.number - 1]
        else:
            # 9, 11, 13 等：映射到 2, 4, 6，再加 12 半音
            base_degree = ((self.number - 1) % 7) + 1
            octave_offset = (self.number - 1) // 7
            base = major_semitones[base_degree - 1] + 12 * octave_offset
        
        return base + self.accidental
    
    def __str__(self) -> str:
        """显示为 '1', '♭3', '♯4', '9', '♭13' 等。"""
        acc_str = ''
        if self.accidental == -1:
            acc_str = '♭'
        elif self.accidental == 1:
            acc_str = '♯'
        return f"{acc_str}{self.number}"
    
    @staticmethod
    def parse(s: str) -> 'ScaleDegree':
        """从字符串解析度数，如 '1', 'b3', '#4', '♭3', '♯4', '9', '♭13'。"""
        s = s.strip()
        accidental = 0
        if s.startswith('♭') or s.startswith('b'):
            accidental = -1
            s = s[1:]
        elif s.startswith('♯') or s.startswith('#'):
            accidental = 1
            s = s[1:]
        number = int(s)
        if number < 1:
            raise ValueError(f"度数必须 >= 1: {number}")
        return ScaleDegree(number, accidental)


# 便捷构造函数
def deg(number: int, accidental: int = 0) -> ScaleDegree:
    """快捷创建度数。deg(1), deg(3, -1), deg(4, 1)。"""
    return ScaleDegree(number, accidental)


@dataclass(frozen=True)
class Pitch:
    """音高：音名与八度的不可变对象，使用科学记号法（C4=中央C）。"""
    name: str
    octave: int
    index: int = field(init=False)
    
    def __post_init__(self):
        object.__setattr__(self, 'name', Pitch.normalize(self.name))
        object.__setattr__(self, 'index', Pitch.note_index(self.name))
    
    def __str__(self) -> str:
        """科学记号表示（如 'c4', 'f♯5'）"""
        return f"{self.name.replace('#', '♯')}{self.octave}"
    
    def __eq__(self, other) -> bool:
        """只允许 Pitch 之间的比较"""
        if not isinstance(other, Pitch):
            return False
        return self.index == other.index and self.octave == other.octave
    
    @staticmethod
    def normalize(note: str) -> str:
        """规范化音名，接受升号与常见降号（转为升号）。"""
        n = note.strip().lower()
        if n in FLAT_TO_SHARP:
            n = FLAT_TO_SHARP[n]
        elif n in ENHARMONIC:
            n = ENHARMONIC[n]
        if n not in NOTES_SHARP:
            raise ValueError(f"无效音名: {note}")
        return n
    
    @staticmethod
    def note_index(note: str) -> int:
        """获取音名在 NOTES_SHARP 中的索引。"""
        return NOTES_SHARP.index(Pitch.normalize(note))
    
    def transpose(self, semitones: int) -> 'Pitch':
        """转置指定半音数。支持正负值."""
        current_idx = Pitch.note_index(self.name)
        new_idx = current_idx + semitones

        octave_shift = new_idx // 12
        note_idx = new_idx % 12

        return Pitch(NOTES_SHARP[note_idx], self.octave + octave_shift)


# 类型别名：区分音阶序列与和弦，避免误用
ScaleNotes = NewType('ScaleNotes', List[str])  # 仅音名的音阶
ScalePitches = NewType('ScalePitches', List[Pitch])  # 带八度的音阶序列
Chord = NewType('Chord', List[Pitch])  # 同时发声的一组音
Progression = NewType('Progression', List[Tuple[str, Chord]])  # 进行：标记 + 和弦


# ===== 音阶 =====

# 音阶定义加载（延迟加载，避免循环导入）
_SCALE_DEGREES_CACHE: Optional[Dict[str, List[ScaleDegree]]] = None


def _get_scale_degrees() -> Dict[str, List[ScaleDegree]]:
    """获取音阶度数定义（带缓存）"""
    global _SCALE_DEGREES_CACHE
    if _SCALE_DEGREES_CACHE is None:
        from .config_loader import load_scales
        _SCALE_DEGREES_CACHE = load_scales()
    return _SCALE_DEGREES_CACHE


def degrees_to_intervals(degrees: List[ScaleDegree]) -> List[int]:
    """将度数列表转换为半音间隔列表（用于构建音阶序列）。
    
    示例：
        [deg(1), deg(2), deg(3)] -> [2, 2] (1->2: 2半音, 2->3: 2半音)
    """
    if not degrees:
        return []
    
    intervals: List[int] = []
    prev_semitones = degrees[0].to_semitones()
    
    for degree in degrees[1:]:
        curr_semitones = degree.to_semitones()
        interval = curr_semitones - prev_semitones
        intervals.append(interval)
        prev_semitones = curr_semitones
    
    return intervals


def build_scale(tonic: Pitch, intervals: List[int]) -> ScalePitches:
    """按间隔生成音阶内的 Pitch 序列（带八度）。"""
    pitches: List[Pitch] = [tonic]
    current_pitch = tonic
    
    for step in intervals:
        current_pitch = current_pitch.transpose(step)
        pitches.append(current_pitch)
    
    return ScalePitches(pitches)


def get_scale(tonic: Pitch, scale: str) -> ScalePitches:
    """获取带八度的音阶序列。"""
    scale_degrees = _get_scale_degrees()
    if scale not in scale_degrees:
        raise ValueError(f"未知音阶: {scale}")
    intervals = degrees_to_intervals(scale_degrees[scale])
    return build_scale(tonic, intervals)


def _note_to_alda(note_name: str) -> str:
    """将音符名称转换为 Alda 格式（# → +，b → -）"""
    if note_name == 'b':
        return 'b'
    result = note_name.replace('#', '+')
    if len(result) > 1 and result.endswith('b'):
        result = result[:-1] + '-'
    return result


def gen_scale_sequence(tonic: str, scale: str) -> ScalePitches:
    """
    生成测试音阶序列：上行两个八度再下行。
    返回 Pitch 对象列表，可直接用于 Alda 渲染。
    
    按照国际标准，C 是每个八度的起始：
    - C4 → B4 是八度 4
    - C5 → B5 是八度 5
    
    算法：
    1. 获取音阶的半音间隔
    2. 从起始音开始，按照间隔依次往前走半音
    3. 使用 transpose 自动处理八度切换
    """
    scale_name = scale.lower()
    tonic_normalized = Pitch.normalize(tonic)
    tonic_pitch = Pitch(tonic_normalized, 4)
    
    # 一次获取音阶（单个八度），再整体上移 12 半音得到下一八度
    base_scale = get_scale(tonic_pitch, scale_name)
    upper_scale = [p.transpose(12) for p in base_scale]
    
    # 拼接：o4 上行一遍 + o5 上行一遍 + 顶点 + o5 下行 + o4 下行 + 回到主音
    sequence: List[Pitch] = []
    sequence.extend(base_scale)
    sequence.extend(upper_scale)
    sequence.extend([tonic_pitch.transpose(24)] * 2)
    sequence.extend(reversed(upper_scale))
    sequence.extend(reversed(base_scale))
    
    return ScalePitches(sequence)


def gen_scale_alda(tonic: str, scale: str, tempo: int = 120) -> str:
    """
    生成音阶的 Alda 乐谱代码（琴键乐器，上行下行）。
    
    示例：piano: (tempo 120) o4 c4 d4 e4 o5 f4 g4 c4 d4 e4 ...
    """
    scale_seq = gen_scale_sequence(tonic, scale)
    
    # 转换为 Alda 片段（仅在八度变化时标记 oN）
    notes: List[str] = []
    current_oct: Optional[int] = None
    for pitch in scale_seq:
        if pitch.octave != current_oct:
            notes.append(f"o{pitch.octave}")
            current_oct = pitch.octave
        notes.append(f"{_note_to_alda(pitch.name)}4")
    
    return f'piano: (tempo {tempo}) {" ".join(notes)}'


# ===== 和弦与和声进行 =====

def build_chord(root: Pitch, chord_degrees: List[ScaleDegree]) -> Chord:
    """根据根音与度数列表构建和弦（支持 9/11/13 扩展）。"""
    pitches: List[Pitch] = []
    for sd in chord_degrees:
        pitches.append(root.transpose(sd.to_semitones()))
    return Chord(pitches)


# 预设和弦构建函数（基于度数）
# 基础三和弦
build_maj = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5)
])
build_min = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5)
])
build_dim = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5, -1)
])
build_aug = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5, 1)
])

# 挂留和弦
build_sus2 = partial(build_chord, chord_degrees=[
    deg(1), deg(2), deg(5)
])
build_sus4 = partial(build_chord, chord_degrees=[
    deg(1), deg(4), deg(5)
])

# 七和弦
build_dom7 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7, -1)
])  # 属七
build_maj7 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7)
])  # 大七
build_min7 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5), deg(7, -1)
])  # 小七
build_half_dim7 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5, -1), deg(7, -1)
])  # 半减七
build_dim7 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5, -1), deg(7, -2)
])  # 减七

# 变化七和弦
build_7b5 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5, -1), deg(7, -1)
])
build_7sharp5 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5, 1), deg(7, -1)
])

# 九和弦
build_maj9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7), deg(9)
])
build_min9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5), deg(7, -1), deg(9)
])
build_dom9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7, -1), deg(9)
])
build_7b9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7, -1), deg(9, -1)
])
build_7sharp9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7, -1), deg(9, 1)
])

# 十一和弦
build_maj11 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7), deg(9), deg(11)
])
build_min11 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5), deg(7, -1), deg(9), deg(11)
])

# 十三和弦
build_maj13 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7), deg(9), deg(13)
])
build_min13 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5), deg(7, -1), deg(9), deg(13)
])
build_dom13 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(7, -1), deg(9), deg(13)
])

# 附加音和弦
build_add9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(9)
])
build_madd9 = partial(build_chord, chord_degrees=[
    deg(1), deg(3, -1), deg(5), deg(9)
])
build_add11 = partial(build_chord, chord_degrees=[
    deg(1), deg(3), deg(5), deg(11)
])

# 级数符号到构建函数的映射（可复用）
CHORD_BUILDERS: Dict[str, Callable[[Pitch], Chord]] = {
    'maj': build_maj,
    'min': build_min,
    'dim': build_dim,
    'aug': build_aug,
    'sus2': build_sus2,
    'sus4': build_sus4,
    '7': build_dom7,
    'dom7': build_dom7,  # 别名：更明确的属七和弦标记
    'maj7': build_maj7,
    'min7': build_min7,
    'm7b5': build_half_dim7,
    'dim7': build_dim7,
    '7b5': build_7b5,
    '7#5': build_7sharp5,
    'maj9': build_maj9,
    'min9': build_min9,
    '9': build_dom9,
    '7b9': build_7b9,
    '7#9': build_7sharp9,
    'maj11': build_maj11,
    'min11': build_min11,
    'maj13': build_maj13,
    'min13': build_min13,
    '13': build_dom13,
    'add9': build_add9,
    'madd9': build_madd9,
    'add11': build_add11,
}


def find_pitch_for_degree(
    target_degree: ScaleDegree,
    tonic: Pitch,
    scale_pitches: ScalePitches,
    scale_degrees: List[ScaleDegree]
) -> Pitch:
    """在音阶中找到对应度数的音高。
    
    如果音阶中有该度数，返回对应的音高。
    如果音阶中没有该度数（如五声音阶中的 II），从主音直接计算。
    
    参数：
        target_degree: 目标度数（如 deg(2) 表示 II 级）
        tonic: 主音
        scale_pitches: 音阶中的音高列表
        scale_degrees: 音阶的度数列表
    
    返回：
        对应的 Pitch 对象
    """
    # 尝试在音阶中找到精确匹配
    for i, deg in enumerate(scale_degrees):
        if deg == target_degree:
            return scale_pitches[i]
    
    # 如果找不到（比如五声音阶中的 II），从主音直接计算
    semitones = target_degree.to_semitones()
    return tonic.transpose(semitones)


def parse_progression_token(tok: str) -> Tuple[ScaleDegree, Callable[[Pitch], Chord]]:
    """解析和弦进行符号。支持数字格式：
    - 简单数字：1, 6, 4（默认大三和弦 maj）
    - 带升降号的数字：b6, #4（升降号后跟数字）
    - 带和弦类型：1maj, 6min, 4maj7, b6dim7, #4sus4
    - 示例：1-6maj-4-5dim-b3min7-#7aug
    """
    t = tok.strip()
    
    # 使用正则表达式解析：[升降号]数字[和弦类型]
    # 例如: b6maj7 -> ('b', '6', 'maj7')
    match = re.match(r'^([b#♭♯]?)(\d+)(.*)$', t)
    if not match:
        raise ValueError(f"无效的和弦符号: {t}")
    
    accidental_str, degree_str, modifier = match.groups()
    
    # 解析升降号
    accidental = 0
    if accidental_str in ('b', '♭'):
        accidental = -1
    elif accidental_str in ('#', '♯'):
        accidental = 1
    
    # 解析度数
    degree_number = int(degree_str)
    
    # 创建 ScaleDegree 对象
    scale_degree = deg(degree_number, accidental)
    
    # 确定构建函数的键
    if not modifier:
        # 无修饰符：默认大三和弦
        builder_key = 'maj'
    else:
        # 修饰符直接查表（maj7, maj9, min, dim, aug, sus4 等）
        builder_key = modifier
    
    # 从 CHORD_BUILDERS 获取构建函数
    if builder_key not in CHORD_BUILDERS:
        raise ValueError(f"未知的和弦类型: {builder_key}")
    builder = CHORD_BUILDERS[builder_key]
    return (scale_degree, builder)


def gen_progression(tonic: Pitch, scale: str, progression_name: str) -> Progression:
    """基于音阶与和弦进行生成和弦。
    
    进行格式：用 - 分隔的和弦符号，如 "1-6maj-4-5dim-b3"
    """
    # 获取基础音阶和度数列表
    scale_pitches = get_scale(tonic, scale)
    scale_degrees = _get_scale_degrees()
    scale_degrees_list = scale_degrees[scale]
    
    tokens = progression_name.split('-')
    chords: List[Tuple[str, Chord]] = []
    
    for tok in tokens:
        if not tok.strip():
            continue
        scale_degree, builder = parse_progression_token(tok)
        # 使用新逻辑：根据度数找到对应的音高
        root = find_pitch_for_degree(scale_degree, tonic, scale_pitches, scale_degrees_list)
        chord_pitches = builder(root)
        chords.append((tok, chord_pitches))
    
    return Progression(chords)


def gen_progression_alda(tonic: str, scale: str, progression_name: str, tempo: int = 120) -> str:
    """生成指定和声进行的 Alda 代码（用 / 连接和弦内各音），自动处理八度切换。"""
    tonic_pitch = Pitch(tonic, 4)
    chords = gen_progression(tonic_pitch, scale, progression_name)
    parts: List[str] = [f"(tempo {tempo}) o4"]
    current_octave: int = 4
    
    for _, pitches in chords:
        chord_notes: List[str] = []
        for p in pitches:
            # 处理八度变化：将 > 或 < 作为音符前缀
            octave_prefix = ''
            while current_octave < p.octave:
                octave_prefix += '>'
                current_octave += 1
            while current_octave > p.octave:
                octave_prefix += '<'
                current_octave -= 1
            chord_notes.append(octave_prefix + _note_to_alda(p.name) + '1')
        
        alda_chord = '/'.join(chord_notes)
        parts.append(alda_chord)
    
    return f"piano: {' '.join(parts)}"


# ===== 和声进行风格库 =====

# 和弦进行加载（延迟加载）
_PROGRESSIONS_CACHE: Optional[Dict[str, Dict[str, str]]] = None


def _get_all_progressions() -> Dict[str, Dict[str, str]]:
    """获取所有和弦进行（按音阶分类，带缓存）"""
    global _PROGRESSIONS_CACHE
    if _PROGRESSIONS_CACHE is None:
        from .config_loader import load_progressions
        _PROGRESSIONS_CACHE = {
            'major': load_progressions('progressions/major.yml'),
            'minor': load_progressions('progressions/minor.yml'),
            'dorian': load_progressions('progressions/dorian.yml'),
            'pentatonic': load_progressions('progressions/pentatonic.yml'),
            'minor_pentatonic': load_progressions('progressions/pentatonic.yml'),  # 共用五声
            'gypsy_minor': load_progressions('progressions/gypsy.yml'),
            'gypsy_major': load_progressions('progressions/gypsy.yml'),
            'jazz': load_progressions('progressions/jazz.yml'),
        }
    return _PROGRESSIONS_CACHE


def get_available_progressions(scale: str, style: str = 'default') -> Dict[str, str]:
    """获取指定音阶与风格下的可用和声进行。"""
    all_progressions = _get_all_progressions()
    base_progressions = all_progressions.get(scale, all_progressions['major']).copy()
    if style == 'jazz':
        base_progressions.update(all_progressions['jazz'])
    return base_progressions


def get_default_progression(scale: str, style: str = 'default') -> str:
    """获取指定音阶与风格的默认和声进行名称。"""
    progressions = get_available_progressions(scale, style)
    return list(progressions.keys())[0]
