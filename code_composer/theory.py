"""
音乐理论模块：音阶与和声预设的程序化生成

提供：
- 音名与半音映射
- Pitch 类型表示音高（音名 + 八度）
- 常见音阶（大调、小调、Dorian、多种五声音阶、Gypsy）生成
- 根据音阶叠置三度生成和弦（triad / seventh）
- 依据罗马数字进程名称生成指定调性的和声进行
"""

from dataclasses import dataclass
from functools import partial
from typing import Callable, Dict, List, NewType, Optional, Tuple


@dataclass(frozen=True)
class Pitch:
    """音高：音名与八度的不可变对象，使用科学记号法（C4=中央C）。"""
    name: str
    octave: int
    
    def __post_init__(self):
        object.__setattr__(self, 'name', Pitch.normalize(self.name))
    
    def __str__(self) -> str:
        """科学记号表示（如 'c4', 'f♯5'）"""
        return f"{self.name.replace('#', '♯')}{self.octave}"
    
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
        """转置指定半音数。例：Pitch('b', 4).transpose(1) → Pitch('c', 5)。"""
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


# 音名集合（小写 + 升号，Alda 兼容）
NOTES_SHARP: List[str] = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
FLAT_TO_SHARP: Dict[str, str] = {'bb': 'a#', 'db': 'c#', 'eb': 'd#', 'gb': 'f#', 'ab': 'g#', 'cb': 'b', 'fb': 'e'}
ENHARMONIC: Dict[str, str] = {'b#': 'c', 'e#': 'f'}


# ===== 音阶 =====

def build_scale(tonic: Pitch, intervals: List[int]) -> ScalePitches:
    """按间隔生成音阶内的 Pitch 序列（带八度）。"""
    pitches: List[Pitch] = [tonic]
    current_pitch = tonic
    
    for step in intervals:
        current_pitch = current_pitch.transpose(step)
        pitches.append(current_pitch)
    
    return ScalePitches(pitches)


# 常见音阶间隔（半音）
SCALE_INTERVALS: Dict[str, List[int]] = {
    'major':           [2, 2, 1, 2, 2, 2, 1],  # Ionian
    'minor':           [2, 1, 2, 2, 1, 2, 2],  # Aeolian（自然小调）
    'dorian':          [2, 1, 2, 2, 2, 1, 2],
    'pentatonic':      [2, 2, 3, 2, 3],        # Anhemitonic pentatonic（大调五声）
    'gypsy_minor':     [2, 1, 3, 1, 1, 3, 1],  # Hungarian minor
    'gypsy_major':     [1, 3, 1, 2, 1, 3, 1],  # Double harmonic major
}


def get_scale(tonic: Pitch, scale: str) -> ScalePitches:
    """获取带八度的音阶序列。"""
    if scale not in SCALE_INTERVALS:
        raise ValueError(f"未知音阶: {scale}")
    return build_scale(tonic, SCALE_INTERVALS[scale])


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
    if scale_name not in SCALE_INTERVALS:
        raise ValueError(f"未知音阶: {scale_name}")
    
    intervals = SCALE_INTERVALS[scale_name]
    tonic_normalized = Pitch.normalize(tonic)
    
    # 从起始音开始：tonic o4
    current_pitch = Pitch(tonic_normalized, 4)
    sequence = [current_pitch]
    
    # 上行两个八度（每个音阶循环一遍）
    for cycle in range(2):
        for interval in intervals:
            current_pitch = current_pitch.transpose(interval)
            sequence.append(current_pitch)
    
    # 顶点是上行序列的最后一个音
    # 下行序列：从倒数第二个开始往回走（不重复顶点）
    descend: List[Pitch] = []
    for i in range(len(sequence) - 2, -1, -1):
        descend.append(sequence[i])
    
    return ScalePitches(sequence + descend)


def gen_scale_alda(tonic: str, scale: str, tempo: int = 120) -> str:
    """
    生成音阶的 Alda 乐谱代码（琴键乐器，上行下行）。
    
    示例：piano: (tempo 120) o4 c2 d2 e2 o5 f2 g2 c2 d2 e2 o6 f1 ...
    """
    scale_seq = gen_scale_sequence(tonic, scale)
    
    # 转换为 Alda 片段（仅在八度变化时标记 oN）
    notes: List[str] = []
    current_oct: Optional[int] = None
    for pitch in scale_seq:
        if pitch.octave != current_oct:
            notes.append(f"o{pitch.octave}")
            current_oct = pitch.octave
        notes.append(f"{_note_to_alda(pitch.name)}2")
    
    # 最后回到起点（全音符强调结束）
    notes.append(f"{_note_to_alda(scale_seq[0].name)}1")
    
    return f'piano: (tempo {tempo}) {" ".join(notes)}'


# ===== 和弦与和声进行 =====

def build_chord(root: Pitch, intervals: List[int]) -> Chord:
    """根据根音与半音间隔列表构建和弦（返回 Pitch 对象）。intervals 通常以 0 开头。"""
    pitches: List[Pitch] = []
    for i in intervals:
        pitches.append(root.transpose(i))
    return Chord(pitches)


# 预设和弦构建函数（基于半音间隔）
# 基础三和弦
build_maj = partial(build_chord, intervals=[0, 4, 7])
build_min = partial(build_chord, intervals=[0, 3, 7])
build_dim = partial(build_chord, intervals=[0, 3, 6])
build_aug = partial(build_chord, intervals=[0, 4, 8])

# 挂留和弦
build_sus2 = partial(build_chord, intervals=[0, 2, 7])
build_sus4 = partial(build_chord, intervals=[0, 5, 7])

# 七和弦
build_dom7 = partial(build_chord, intervals=[0, 4, 7, 10])  # 属七
build_maj7 = partial(build_chord, intervals=[0, 4, 7, 11])  # 大七
build_min7 = partial(build_chord, intervals=[0, 3, 7, 10])  # 小七
build_half_dim7 = partial(build_chord, intervals=[0, 3, 6, 10])  # 半减七
build_dim7 = partial(build_chord, intervals=[0, 3, 6, 9])  # 减七

# 变化七和弦
build_7b5 = partial(build_chord, intervals=[0, 4, 6, 10])
build_7sharp5 = partial(build_chord, intervals=[0, 4, 8, 10])

# 九和弦
build_maj9 = partial(build_chord, intervals=[0, 4, 7, 11, 14])
build_min9 = partial(build_chord, intervals=[0, 3, 7, 10, 14])
build_dom9 = partial(build_chord, intervals=[0, 4, 7, 10, 14])
build_7b9 = partial(build_chord, intervals=[0, 4, 7, 10, 13])
build_7sharp9 = partial(build_chord, intervals=[0, 4, 7, 10, 15])

# 十一和弦
build_maj11 = partial(build_chord, intervals=[0, 4, 7, 11, 14, 17])
build_min11 = partial(build_chord, intervals=[0, 3, 7, 10, 14, 17])

# 十三和弦
build_maj13 = partial(build_chord, intervals=[0, 4, 7, 11, 14, 21])
build_min13 = partial(build_chord, intervals=[0, 3, 7, 10, 14, 21])
build_dom13 = partial(build_chord, intervals=[0, 4, 7, 10, 14, 21])

# 附加音和弦
build_add9 = partial(build_chord, intervals=[0, 4, 7, 14])
build_madd9 = partial(build_chord, intervals=[0, 3, 7, 14])
build_add11 = partial(build_chord, intervals=[0, 4, 7, 17])

# 级数符号到构建函数的映射（可复用）
CHORD_BUILDERS: Dict[str, Callable[[Pitch], Chord]] = {
    'maj': build_maj,
    'min': build_min,
    'dim': build_dim,
    'aug': build_aug,
    'sus2': build_sus2,
    'sus4': build_sus4,
    '7': build_dom7,
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


def parse_progression_token(tok: str) -> Tuple[int, Callable[[Pitch], Chord]]:
    """解析罗马数字符号（如 I, vi, V7），返回(级数索引, 构建函数)。
    
    大写表示大三和弦，小写表示小三和弦。
    修饰符从 CHORD_BUILDERS 表中查找。
    """
    t = tok.strip()
    
    # 提取罗马数字部分
    roman = ''.join([c for c in t if c.upper() in 'IVX' or c.lower() in 'ivx'])
    
    # 提取修饰符（除去罗马数字）
    modifier = t.replace(roman, '').strip()
    
    # 映射罗马数字到级数索引
    degree_map = {
        'i': 0, 'ii': 1, 'iii': 2, 'iv': 3, 'v': 4, 'vi': 5, 'vii': 6,
        'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4, 'VI': 5, 'VII': 6,
    }
    degree = degree_map.get(roman, 0)
    is_major = roman.isupper() if roman else True
    
    # 确定构建函数的键
    if not modifier:
        # 无修饰符：大三或小三
        builder_key = 'maj' if is_major else 'min'
    elif modifier == '7':
        # 特殊情况：7 根据大小写选择 dom7 或 min7
        builder_key = '7' if is_major else 'min7'
    else:
        # 其他修饰符直接查表（maj7, maj9, sus4 等）
        builder_key = modifier
    
    # 从 CHORD_BUILDERS 获取构建函数
    builder = CHORD_BUILDERS.get(builder_key, build_maj if is_major else build_min)
    return (degree, builder)


def gen_progression(tonic: Pitch, scale: str, progression_name: str) -> Progression:
    """基于音阶与罗马数字进行生成和弦。"""
    # 获取基础音阶（一个八度）
    scale_pitches = get_scale(tonic, scale)
    
    tokens = progression_name.split('_')
    chords: List[Tuple[str, Chord]] = []
    
    for tok in tokens:
        degree, builder = parse_progression_token(tok)
        # degree 已经是 0-6，直接用作索引
        root = scale_pitches[degree]
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

SCALE_PROGRESSIONS: Dict[str, Dict[str, str]] = {
    'major': {
        'I_vi_IV_V': '流行进行（1-6-4-5）',
        'I_V_IV_vi': '常见进行（1-5-4-6）',
        'IV_V_iii_vi_ii_V_I': '帕赫贝尔卡农进行',
        'I_IV_V_IV': '摇滚进行',
        'vi_IV_I_V': '抒情进行',
    },
    'minor': {
        'i_VI_III_VII': '自然小调进行',
        'i_iv_v_i': '基础小调进行',
        'i_VI_VII_i': '悲伤进行',
        'i_III_VII_VI': '史诗进行',
        'i_iv_VII_III': '哥特进行',
    },
    'dorian': {
        'i_IV_i_IV': '多利亚摇摆',
        'i_ii_IV_V': '多利亚经典',
        'i_IV_VII_i': '多利亚回环',
        'ii_V_i_IV': '多利亚爵士',
    },
    'pentatonic': {
        'I_vi_ii_I': '宫商角宫',
        'I_III_IV_I': '五声简约',
        'I_II_IV_V': '中国风',
        'I_IV_V_I': '民谣进行',
    },
    'gypsy_minor': {
        'i_II_V_i': '吉普赛基础',
        'i_VII_VI_VII': '吉普赛回旋',
        'i_II_III_i': '匈牙利式',
        'VI_VII_i_II': '东欧风情',
    },
    'gypsy_major': {
        'I_II_III_I': '双和声行进',
        'I_bII_VII_I': '中东风格',
        'I_V_VI_VII': '神秘进行',
    },
}

# 爵士专用和声进行（适用于多种音阶）
JAZZ_PROGRESSIONS: Dict[str, str] = {
    'II_V_I': '经典爵士 Bebop',
    'VI_ii_V_I': '扩展 Standard',
    'Imaj7_vi7_ii7_V7': '现代爵士',
    'ii7_V7_Imaj7_vi7': '转位爵士',
}


def get_available_progressions(scale: str, style: str = 'default') -> Dict[str, str]:
    """获取指定音阶与风格下的可用和声进行。"""
    base_progressions = SCALE_PROGRESSIONS.get(scale, SCALE_PROGRESSIONS['major']).copy()
    if style == 'jazz':
        base_progressions.update(JAZZ_PROGRESSIONS)
    return base_progressions


def get_default_progression(scale: str, style: str = 'default') -> str:
    """获取指定音阶与风格的默认和声进行名称。"""
    progressions = get_available_progressions(scale, style)
    return list(progressions.keys())[0]
