"""
音乐理论模块：音阶与和声预设的程序化生成

提供：
- 音名与半音映射
- 常见音阶（大调、小调、Dorian、多种五声音阶、Gypsy）生成
- 根据音阶叠置三度生成和弦（triad / seventh）
- 依据罗马数字进程名称生成指定调性的和声进行
"""

from typing import List, Tuple


# 统一使用小写加升号的音名集合（与 Alda 兼容）
NOTES_SHARP: List[str] = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']

FLAT_TO_SHARP = {
    'db': 'c#', 'eb': 'd#', 'gb': 'f#', 'ab': 'g#', 'bb': 'a#',
    'cb': 'b', 'fb': 'e', 'eb': 'd#',
}

ENHARMONIC = {
    'b#': 'c', 'e#': 'f', 'a#': 'a#', 'd#': 'd#', 'g#': 'g#', 'c#': 'c#', 'f#': 'f#'
}


def normalize_note(note: str) -> str:
    n = note.strip().lower()
    if n in ENHARMONIC:
        n = ENHARMONIC[n]
    if 'b' in n and len(n) == 2 and n.endswith('b'):
        n = FLAT_TO_SHARP.get(n, n)
    if n not in NOTES_SHARP:
        # 回退：仅取首字母（如传入 C 或 c），其余忽略
        n = n[0]
        if n not in [x[0] for x in NOTES_SHARP]:
            raise ValueError(f"未知音名: {note}")
        # 映射到自然音
        mapping = {'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e', 'f': 'f', 'g': 'g'}
        n = mapping[n]
    return n


def index_of(note: str) -> int:
    return NOTES_SHARP.index(normalize_note(note))


def transpose(note: str, semitones: int) -> str:
    idx = index_of(note)
    return NOTES_SHARP[(idx + semitones) % 12]


def build_scale(tonic: str, intervals: List[int]) -> List[str]:
    """按照半音间隔生成音阶。intervals 为各级之间的半音距离。"""
    t = normalize_note(tonic)
    notes = [t]
    idx = index_of(t)
    for step in intervals:
        idx = (idx + step) % 12
        notes.append(NOTES_SHARP[idx])
    # 对于五声音阶等，最后一个音可能回到主音，保留以利于叠置计算
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
