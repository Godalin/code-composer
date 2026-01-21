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
from typing import List, Tuple


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


# 音名集合（小写 + 升号，Alda 兼容）
NOTES_SHARP: List[str] = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
FLAT_TO_SHARP = {'bb': 'a#', 'db': 'c#', 'eb': 'd#', 'gb': 'f#', 'ab': 'g#', 'cb': 'b', 'fb': 'e'}
ENHARMONIC = {'b#': 'c', 'e#': 'f'}


def build_scale(tonic: str, intervals: List[int]) -> List[str]:
    """按间隔生成音阶内的音名序列。"""
    t = Pitch.normalize(tonic)
    notes = [t]
    idx = Pitch.note_index(t)
    for step in intervals:
        idx = (idx + step) % 12
        notes.append(NOTES_SHARP[idx])
    return notes


# 常见音阶间隔（半音）
SCALE_INTERVALS = {
    'major':           [2, 2, 1, 2, 2, 2, 1],  # Ionian
    'minor':           [2, 1, 2, 2, 1, 2, 2],  # Aeolian（自然小调）
    'dorian':          [2, 1, 2, 2, 2, 1, 2],
    'pentatonic':      [2, 2, 3, 2, 3],        # Anhemitonic pentatonic（大调五声）
    'gypsy_minor':     [2, 1, 3, 1, 1, 3, 1],  # Hungarian minor
    'gypsy_major':     [1, 3, 1, 2, 1, 3, 1],  # Double harmonic major
}


def get_scale(tonic: str, scale: str) -> List[str]:
    if scale not in SCALE_INTERVALS:
        raise ValueError(f"未知音阶: {scale}")
    return build_scale(tonic, SCALE_INTERVALS[scale])


def build_chord(scale_notes: List[str], degree: int, seventh: bool = False) -> List[str]:
    """基于音阶叠置三度生成和弦（triad 或 seventh）。degree 为 0 基。"""
    n = len(scale_notes)
    # 使用音阶内“叠置三度”（隔一个级数）
    chord = [scale_notes[degree % n],
             scale_notes[(degree + 2) % n],
             scale_notes[(degree + 4) % n]]
    if seventh:
        chord.append(scale_notes[(degree + 6) % n])
    return chord


def parse_progression_token(tok: str) -> Tuple[int, bool]:
    """解析罗马数字（如 I, vi, V7, Imaj7），返回（级数索引，是否七和弦）。"""
    t = tok.strip()
    seventh = ('7' in t)
    # 取罗马数字部分（去掉后缀）
    roman = ''.join([c for c in t if c.upper() in 'IVX' or c.lower() in 'ivx'])
    mapping = {
        'i': 0, 'ii': 1, 'iii': 2, 'iv': 3, 'v': 4, 'vi': 5, 'vii': 6,
        'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4, 'VI': 5, 'VII': 6,
    }
    if roman not in mapping:
        # 对于五声音阶等，可能出现 III、IV、V 等；若解析失败，默认 I
        degree = 0
    else:
        degree = mapping[roman]
    return degree, seventh


# 各音阶的常用和声进行
SCALE_PROGRESSIONS = {
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
JAZZ_PROGRESSIONS = {
    'II_V_I': '经典爵士 Bebop',
    'VI_ii_V_I': '扩展 Standard',
    'Imaj7_vi7_ii7_V7': '现代爵士',
    'ii7_V7_Imaj7_vi7': '转位爵士',
}


def get_available_progressions(scale: str, style: str = 'default') -> dict:
    """获取指定音阶与风格下的可用和声进行。"""
    base_progressions = SCALE_PROGRESSIONS.get(scale, SCALE_PROGRESSIONS['major']).copy()
    
    # Jazz 风格额外添加爵士进行
    if style == 'jazz':
        base_progressions.update(JAZZ_PROGRESSIONS)
    
    return base_progressions


def get_default_progression(scale: str, style: str = 'default') -> str:
    """获取指定音阶与风格的默认和声进行名称。"""
    progressions = get_available_progressions(scale, style)
    # 返回第一个
    return list(progressions.keys())[0]


def generate_progression(tonic: str, scale: str, progression_name: str) -> List[Tuple[str, List[str]]]:
    """基于音阶与进程名称生成（和弦名，占位）与和弦内音集合。"""
    scale_notes = get_scale(tonic, scale)
    tokens = progression_name.split('_')
    chords: List[Tuple[str, List[str]]] = []
    for tok in tokens:
        degree, seventh = parse_progression_token(tok)
        chord_notes = build_chord(scale_notes, degree, seventh=seventh)
        chords.append((tok, chord_notes))
    return chords


def _note_to_alda(note_name: str) -> str:
    """将音符名称转换为 Alda 格式（# → +，b → -）"""
    if note_name == 'b':
        return 'b'
    result = note_name.replace('#', '+')
    if len(result) > 1 and result.endswith('b'):
        result = result[:-1] + '-'
    return result


def generate_scale_sequence(tonic: str, scale: str) -> List[Pitch]:
    """
    生成测试音阶序列：上行两个八度再下行。
    返回 Pitch 对象列表，可直接用于 Alda 渲染。
    
    按照国际标准，C 是每个八度的起始：
    - C4 → B4 是八度 4
    - C5 → B5 是八度 5
    
    算法：
    1. 获取音阶的半音间隔
    2. 从起始音开始，按照间隔依次往前走半音
    3. 使用 transpose_pitch 自动处理八度切换
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
    descend = []
    for i in range(len(sequence) - 2, -1, -1):
        descend.append(sequence[i])
    
    return sequence + descend


def generate_scale_alda(tonic: str, scale: str, tempo: int = 120) -> str:
    """
    生成音阶的 Alda 乐谱代码（琴键乐器，上行下行）。
    
    示例：piano: (tempo 120) o4 c2 d2 e2 o5 f2 g2 c2 d2 e2 o6 f1 ...
    """
    scale_seq = generate_scale_sequence(tonic, scale)
    
    # 转换为 Alda 片段（仅在八度变化时标记 oN）
    notes = []
    current_oct = None
    for pitch in scale_seq:
        if pitch.octave != current_oct:
            notes.append(f"o{pitch.octave}")
            current_oct = pitch.octave
        notes.append(f"{_note_to_alda(pitch.name)}2")
    
    # 最后回到起点（全音符强调结束）
    notes.append(f"{_note_to_alda(scale_seq[0].name)}1")
    
    return f'piano: (tempo {tempo}) {" ".join(notes)}'
