"""

代码到音乐编译系统 - Code Composer

架构概览：
- 支持多语言前端：C（frontend/c.py）、Python（frontend/python.py）
- 统一的 token 接口：frontend/lexer.py 定义 TokenType, Token, BaseLexer
- 音乐生成引擎：Composer 类将 token 流转换为 C 大调钢琴乐谱
- 输出格式：Alda（一个强大的音乐编程语言）

工作流程：
1. 源代码 → 语言前端 → Token 流
2. Token 流 → 谱曲器 → Alda 乐谱
3. Alda 乐谱 → Alda 播放器 → 音频输出
"""

import subprocess
import os
import random
from typing import List, Tuple, Optional, Dict, cast

from .frontend import Token, TokenType, compile_c_code, compile_python_code


class Style:
    """
    音乐风格定义
    
    包含：
    - 节奏型集合和权重
    - 和声进行
    - 特殊标记（如爵士蓝调音符等）
    """
    
    def __init__(
        self,
        name: str,
        bar_patterns: List[List[str]],
        bar_pattern_weights: List[int],
        chord_progressions: Dict[str, List[Tuple[str, List[str]]]],
        blue_notes: bool = False,  # 是否使用爵士蓝调音符
    ):
        """
        初始化风格
        
        参数：
            name: 风格名称
            bar_patterns: 节奏型列表
            bar_pattern_weights: 节奏型权重列表
            chord_progressions: 和声进行字典
            blue_notes: 是否在爵士风格中使用蓝调音符
        """
        self.name = name
        self.bar_patterns = bar_patterns
        self.bar_pattern_weights = bar_pattern_weights
        self.chord_progressions = chord_progressions
        self.blue_notes = blue_notes
        
        if len(bar_patterns) != len(bar_pattern_weights):
            raise ValueError(
                f"节奏型数量 ({len(bar_patterns)}) "
                f"与权重数量 ({len(bar_pattern_weights)}) 不匹配"
            )


class Composer:
    """
    谱曲器：将 token 流转换成 C 大调钢琴 Alda 曲
    
    架构说明：
    - 以固定长度的乐句（phrase）为单位组织音乐
    - 每个乐句包含 n 个小节，每个小节对应一个 token
    - 每个乐句内使用一个确定的和声进行
    - 最终形成 m 个完整的乐句
    - 每个小节只使用当前小节对应和弦的内音
    """

    # ========== C 大调常用和声进行 ==========
    # 格式：[(和弦名, 内音集合), ...]
    CHORD_PROGRESSIONS = {
        # 流行音乐进行（1-6-4-5）
        'I_vi_IV_V': [
            ('C', ['c', 'e', 'g']),      # I 度
            ('Am', ['a', 'c', 'e']),     # vi 度
            ('F', ['f', 'a', 'c']),      # IV 度
            ('G', ['g', 'b', 'd']),      # V 度
        ],
        # 常见进行（1-5-4-6）
        'I_V_IV_vi': [
            ('C', ['c', 'e', 'g']),      # I 度
            ('G', ['g', 'b', 'd']),      # V 度
            ('F', ['f', 'a', 'c']),      # IV 度
            ('Am', ['a', 'c', 'e']),     # vi 度
        ],
        # 帕赫贝尔卡农进行（4-5-3-6-2-5-1）
        'IV_V_iii_vi_ii_V_I': [
            ('F', ['f', 'a', 'c']),      # IV 度
            ('G', ['g', 'b', 'd']),      # V 度
            ('Em', ['e', 'g', 'b']),     # iii 度
            ('Am', ['a', 'c', 'e']),     # vi 度
            ('Dm', ['d', 'f', 'a']),     # ii 度
            ('G', ['g', 'b', 'd']),      # V 度
            ('C', ['c', 'e', 'g']),      # I 度
        ],
        # 爵士进行（Cmaj7-Am7-Dm7-G7）
        'Imaj7_vi7_ii7_V7': [
            ('Cmaj7', ['c', 'e', 'g', 'b']),
            ('Am7', ['a', 'c', 'e', 'g']),
            ('Dm7', ['d', 'f', 'a', 'c']),
            ('G7', ['g', 'b', 'd', 'f']),
        ],
    }

    # ========== C 大调音阶 ==========
    C_MAJOR_SCALE = ['c', 'd', 'e', 'f', 'g', 'a', 'b']

    # ========== 旋律动机类型 ==========
    # 在和弦内生成具有方向性的旋律
    MOTIF_TYPES = [
        'ascending',    # 上行：逐步上升
        'descending',   # 下行：逐步下降
        'arch',         # 拱形：先上后下
        'valley',       # 谷形：先下后上
        'repeat',       # 重复：停留在同一音
    ]

    # ========== 预定义风格 ==========
    @staticmethod
    def _create_default_style() -> Style:
        """创建默认（现代）风格"""
        bar_patterns = [
            # ===== 基础节奏 =====
            ['4', '4', '4', '4'],    # 四个四分音符（最基础）
            ['2', '4', '4'],         # 一个二分 + 两个四分
            ['4', '2', '4'],         # 四分 + 二分 + 四分
            ['2', '2'],              # 两个二分音符
            ['1'],                   # 一个全音符
            ['4', '4', '2'],         # 两个四分 + 一个二分
            
            # ===== 八分音符节奏 =====
            ['8', '8', '8', '8', '8', '8', '8', '8'],  # 8个八分音符（流畅）
            ['8', '8', '4', '4', '4'],                  # 两个八分 + 三个四分
            ['4', '8', '8', '4', '4'],                  # 四分 + 两个八分 + 两个四分
            ['8', '8', '8', '8', '4', '4'],            # 四个八分 + 两个四分
            ['4', '4', '8', '8', '8', '8'],            # 两个四分 + 四个八分
            ['4', '8', '8', '8', '8', '4'],            # 四分 + 四个八分 + 四分
            ['8', '8', '8', '8', '2'],                  # 四个八分 + 一个二分
            ['2', '8', '8', '8', '8'],                  # 二分 + 四个八分
            ['8', '8', '4', '8', '8', '4'],            # 八分-八分-四分-八分-八分-四分（经典摇滚）
            
            # ===== 十六分音符节奏 =====
            ['16', '16', '16', '16', '8', '8', '4', '4'],  # 四个十六分 + 两个八分 + 两个四分
            ['4', '16', '16', '16', '16', '8', '8', '4'],  # 四分 + 四个十六分 + 两个八分 + 四分
            ['8', '16', '16', '8', '16', '16', '4', '4'],  # 八分-两个十六-八分-两个十六-两个四分
            ['16', '16', '16', '16', '16', '16', '16', '16', '4', '4'],  # 8个十六分 + 两个四分
            
            # ===== 三连音节奏（用6表示四分三连音，用12表示八分三连音）=====
            ['6', '6', '6', '6', '6', '6'],            # 6个四分三连音（2小节的三连音）
            ['12', '12', '12', '12', '12', '12', '12', '12', '12', '12', '12', '12'],  # 12个八分三连音
            ['6', '6', '6', '4', '4'],                  # 三个四分三连音 + 两个四分
            ['4', '6', '6', '6', '4'],                  # 四分 + 三个四分三连音 + 四分
            
            # ===== 切分节奏（syncopation）=====
            ['8', '4', '8', '4', '4'],                  # 八分-四分-八分-两个四分（切分）
            ['4', '8', '4', '8', '4'],                  # 四分-八分-四分-八分-四分（切分）
            ['8', '8', '4', '8', '8', '4'],            # 切分节奏（强拍在弱位）
        ]
        
        weights = [
            # Basic patterns (0-5)
            1, 1, 2, 2, 1, 2,
            # Eighth note patterns (6-14)
            5, 4, 4, 5, 5, 4, 4, 5, 4,
            # Sixteenth note patterns (15-18)
            7, 6, 7, 6,
            # Triplet patterns (19-22)
            3, 2, 3, 2,
            # Syncopation patterns (23-25)
            7, 6, 7,
        ]
        
        chord_progs = Composer.CHORD_PROGRESSIONS
        
        return Style(
            name='default',
            bar_patterns=bar_patterns,
            bar_pattern_weights=weights,
            chord_progressions=chord_progs,
            blue_notes=False,
        )
    
    @staticmethod
    def _create_jazz_style() -> Style:
        """创建爵士风格"""
        # 爵士风格使用 swing 节奏（2/3 1/3 分割）和大量三连音
        bar_patterns = [
            # ===== Swing 节奏（三连音） =====
            # 映射：'6' = 2/3拍（四分三连音），'12' = 1/3拍（八分三连音）
            ['6', '6', '6', '6', '6', '6'],            # 6个四分三连音 = 4拍（经典 swing）
            ['12', '12', '12', '12', '12', '12', '12', '12', '12', '12', '12', '12'],  # 12个八分三连音 = 4拍
            ['6', '6', '6', '4', '4'],                  # 三个四分三连音 + 两个四分 = 4拍
            ['4', '6', '6', '6', '4'],                  # 四分 + 三个四分三连音 + 四分 = 4拍
            # 经典摇摆八分音型：长-短配对，每拍一组，共4拍
            ['6', '12', '6', '12', '6', '12', '6', '12'],  # 长短配对 ×4 = 4拍
            ['12', '6', '12', '6', '12', '6', '12', '6'],  # 反向长短配对 ×4 = 4拍
            # 两拍一组的交替（每组2拍），共两组组成一小节
            ['6', '12', '12', '6', '6', '12', '12', '6'],  # [长短短长] ×2 = 4拍
            ['12', '6', '6', '12', '12', '6', '6', '12'],  # [短长长短] ×2 = 4拍
            # 两拍摇摆 + 两个四分（稳定强拍）
            ['6', '12', '6', '12', '4', '4'],              # 2拍摇摆 + 2个四分 = 4拍
            ['4', '4', '6', '12', '6', '12'],              # 2个四分 + 2拍摇摆 = 4拍
            
            # ===== 爵士切分节奏（syncopation） =====
            ['8', '4', '8', '4', '4'],                  # 八分-四分-八分-两个四分（爵士切分）
            ['4', '8', '4', '8', '4'],                  # 四分-八分-四分-八分-四分（爵士切分）
            ['8', '8', '4', '8', '8', '4'],            # 切分节奏（强拍在弱位）
            
            # ===== 爵士八分音符节奏 =====
            ['8', '8', '8', '8', '8', '8', '8', '8'],  # 8个八分音符（流畅摇摆）
            ['8', '8', '4', '4', '4'],                  # 两个八分 + 三个四分
            ['4', '8', '8', '4', '4'],                  # 四分 + 两个八分 + 两个四分
            
            # ===== 爵士十六分音符节奏 =====
            ['16', '16', '16', '16', '8', '8', '4', '4'],  # 四个十六分 + 两个八分 + 两个四分
            ['4', '16', '16', '16', '16', '8', '8', '4'],  # 四分 + 四个十六分 + 两个八分 + 四分
            
            # ===== 爵士基础节奏（较少） =====
            ['2', '2'],              # 两个二分音符
            ['4', '4', '4', '4'],    # 四个四分音符
            ['2', '4', '4'],         # 一个二分 + 两个四分
        ]
        
        weights = [
            # Swing/Triplet patterns (0-9) - 提升权重（更常出现）
            9, 9, 8, 8, 9, 9, 8, 8, 9, 9,
            # Syncopation patterns (10-12) - 保持较高（切分感）
            7, 7, 7,
            # Eighth note patterns (13-15) - 降低连续等节奏（尤其纯八分）
            2, 4, 3,
            # Sixteenth note patterns (16-17) - 适中（用于装饰）
            5, 5,
            # Basic patterns (18-20) - 显著降低（均匀节奏）
            1, 1, 1,
        ]
        
        # 爵士风格使用自己的和声进行
        jazz_progressions = {
            'II_V_I': [
                ('Dm7', ['d', 'f', 'a', 'c']),      # ii-7
                ('G7', ['g', 'b', 'd', 'f']),       # V7
                ('Cmaj7', ['c', 'e', 'g', 'b']),    # Imaj7
            ],
            'VI_ii_V_I': [
                ('Am7', ['a', 'c', 'e', 'g']),      # vi-7
                ('Dm7', ['d', 'f', 'a', 'c']),      # ii-7
                ('G7', ['g', 'b', 'd', 'f']),       # V7
                ('Cmaj7', ['c', 'e', 'g', 'b']),    # Imaj7
            ],
            'Imaj7_vi7_ii7_V7': Composer.CHORD_PROGRESSIONS['Imaj7_vi7_ii7_V7'],
            # 加入默认风格的和声进行
            'I_vi_IV_V': Composer.CHORD_PROGRESSIONS['I_vi_IV_V'],
            'I_V_IV_vi': Composer.CHORD_PROGRESSIONS['I_V_IV_vi'],
            'IV_V_iii_vi_ii_V_I': Composer.CHORD_PROGRESSIONS['IV_V_iii_vi_ii_V_I'],
        }
        
        return Style(
            name='jazz',
            bar_patterns=bar_patterns,
            bar_pattern_weights=weights,
            chord_progressions=jazz_progressions,
            blue_notes=True,  # 爵士风格使用蓝调音符
        )
    
    # 所有可用风格
    STYLES: Dict[str, Optional[Style]] = {
        'default': None,  # 延迟初始化
        'jazz': None,     # 延迟初始化
    }

    def __init__(
        self,
        chord_progression: str = 'I_vi_IV_V',
        octave: int = 4,
        tempo: int = 120,
        bars_per_phrase: int = 4,
        style: str = 'default',
        bass_arpeggio: str = 'block',
        seed: Optional[int] = None,
    ):
        """
        初始化谱曲器
        
        参数：
            chord_progression: 和声进行名称（见 CHORD_PROGRESSIONS）
            octave: 基础八度（默认 4，钢琴中间 C）
            tempo: 速度（BPM）
            bars_per_phrase: 每个乐句包含的小节数（默认 4）
            style: 音乐风格 ('default' 或 'jazz')
            bass_arpeggio: 低音分解和弦模式 ('block', 'double', 'follow', 'arpeggio', 'pendulum')
            seed: 随机数种子（用于复现结果）
        """
        # 延迟初始化风格
        if Composer.STYLES['default'] is None:
            Composer.STYLES['default'] = Composer._create_default_style()
            Composer.STYLES['jazz'] = Composer._create_jazz_style()
        
        if style not in Composer.STYLES:
            raise ValueError(
                f"未知的风格: {style}。"
                f"可用风格: {list(Composer.STYLES.keys())}"
            )
        
        # 选择风格
        self.style: Style = cast(Style, Composer.STYLES[style])
        
        # 验证和声进行
        if chord_progression not in self.style.chord_progressions:
            raise ValueError(
                f"风格 '{style}' 中未知的和声进行: {chord_progression}。"
                f"可用进行: {list(self.style.chord_progressions.keys())}"
            )
        
        self.progression = self.style.chord_progressions[chord_progression]
        self.progression_name = chord_progression
        self.style_name = style
        self.octave = octave
        self.tempo = tempo
        self.bars_per_phrase = bars_per_phrase
        self.bass_arpeggio = bass_arpeggio
        self.prng = random.Random(seed)
        self._last_pattern_idx: Optional[int] = None

    def _get_motif_notes(
        self,
        chord_notes: List[str],
        num_notes: int,
        motif_type: Optional[str] = None,
    ) -> List[Tuple[str, int]]:
        """
        根据动机类型生成旋律音符序列
        
        参数：
            chord_notes: 当前小节对应和弦的内音集合（音符名，如 ['c', 'e', 'g']）
            num_notes: 需要生成的音符数
            motif_type: 动机类型（如不指定则随机选择）
        
        返回：
            (音符名, 八度) 元组列表，例如 [('c', 4), ('e', 4), ('g', 4)]
        """
        if motif_type is None:
            motif_type = self.prng.choice(self.MOTIF_TYPES)

        # 如果是爵士风格且启用蓝调音符，扩展可用音符
        available_notes = list(chord_notes)
        if self.style.blue_notes:
            # 在爵士中加入常见的蓝调音符
            # C 大调的蓝调音符：♭3 (d#/eb), ♭5 (f#/gb), ♭7 (a#/bb)
            blue_note_map = {
                'c': ['d#', 'f#'],     # ♭3, ♭5
                'd': ['f'],            # ♭3
                'e': ['f#', 'g#'],     # ♭2, ♭3
                'f': ['g#', 'a#'],     # ♭3, ♭5
                'g': ['a#'],           # ♭3
                'a': ['b#', 'd#'],     # ♭2, ♭3
                'b': ['d#'],           # ♭2
            }
            # 将蓝调音符加入可用音符，但概率较低
            extended_notes = []
            for note in available_notes:
                extended_notes.append(note)
                if note in blue_note_map:
                    extended_notes.extend(blue_note_map[note])
            available_notes = extended_notes

        notes = []
        base_octave = self.octave

        if motif_type == 'ascending':
            # 上行：逐步使用和弦内的更高音符
            for i in range(num_notes):
                note_idx = (i * 2) % len(available_notes)
                octave = base_octave + (i * 2 // len(available_notes))
                octave = max(2, min(6, octave))  # 限制在有效八度范围
                notes.append((available_notes[note_idx], octave))

        elif motif_type == 'descending':
            # 下行：逐步使用更低的音
            for i in range(num_notes):
                note_idx = (len(available_notes) - 1 - i) % len(available_notes)
                octave = base_octave - (i // len(available_notes))
                octave = max(2, min(6, octave))
                notes.append((available_notes[note_idx], octave))

        elif motif_type == 'arch':
            # 拱形：先上升后下降
            mid = num_notes // 2
            for i in range(num_notes):
                if i < mid:
                    # 前半段上升
                    note_idx = (i * 2) % len(available_notes)
                    octave = base_octave
                else:
                    # 后半段下降
                    note_idx = ((num_notes - i) * 2) % len(available_notes)
                    octave = base_octave
                notes.append((available_notes[note_idx], octave))

        elif motif_type == 'valley':
            # 谷形：先下降后上升
            mid = num_notes // 2
            for i in range(num_notes):
                if i < mid:
                    # 前半段下降
                    note_idx = (len(available_notes) - 1 - i) % len(available_notes)
                    octave = base_octave
                else:
                    # 后半段上升
                    note_idx = (i - mid) % len(available_notes)
                    octave = base_octave
                notes.append((available_notes[note_idx], octave))

        elif motif_type == 'repeat':
            # 重复：停留在同一个音
            note = self.prng.choice(available_notes)
            for _ in range(num_notes):
                notes.append((note, base_octave))

        return notes

    def _generate_bass_bar(
        self,
        chord_notes: List[str],
        pattern: List[str],
    ) -> str:
        """
        生成低音区小节，支持多种分解和弦模式
        
        参数：
            chord_notes: 和弦内音列表 ['c', 'e', 'g']
            pattern: 旋律的节奏模式 ['8', '4', '8', ...] 用于同步
        
        返回：
            Alda 格式的低音小节字符串
        """
        bass_octave = self.octave - 1
        
        if not chord_notes:
            return f"(vol 80) o{bass_octave} r1"
        
        # ===== 柱式和弦（block）: 整小节单个和弦 =====
        if self.bass_arpeggio == 'block':
            root = chord_notes[0]
            others = "/".join(chord_notes[1:]) if len(chord_notes) > 1 else ""
            chord = f"(vol 80) o{bass_octave} {root}1"
            if others:
                chord += f"/{others}"
            return chord
        
        # ===== 双重柱式（double）: 两个半音符柱式和弦 =====
        elif self.bass_arpeggio == 'double':
            root = chord_notes[0]
            others = "/".join(chord_notes[1:]) if len(chord_notes) > 1 else ""
            chord = f"(vol 80) o{bass_octave} {root}2"
            if others:
                chord += f"/{others}"
            return f"{chord} {chord}"
        
        # ===== 跟随旋律节奏（follow）: 低音和弦跟随旋律节奏 =====
        elif self.bass_arpeggio == 'follow':
            bass_parts = []
            current_octave = bass_octave
            chord_len = len(chord_notes)
            
            for idx, duration in enumerate(pattern):
                # 按顺序循环使用和弦内音
                note = chord_notes[idx % chord_len]
                
                if idx == 0:
                    # 第一个音强调
                    bass_parts.append(f"(vol 85) {note}{duration}")
                else:
                    bass_parts.append(f"(vol 75) {note}{duration}")
            
            return f"o{bass_octave} " + " ".join(bass_parts)
        
        # ===== 分解和弦（arpeggio）: 依次弹奏和弦内音 =====
        elif self.bass_arpeggio == 'arpeggio':
            bass_parts = []
            chord_len = len(chord_notes)
            # 计算需要多少个音符来填充一个小节
            # 简化：平均分配成 8 个音符（8 个八分音符）
            notes_per_bar = 8
            note_duration = '8'  # 八分音符
            
            for i in range(notes_per_bar):
                note = chord_notes[i % chord_len]
                if i == 0:
                    bass_parts.append(f"(vol 85) {note}{note_duration}")
                else:
                    bass_parts.append(f"(vol 75) {note}{note_duration}")
            
            return f"o{bass_octave} " + " ".join(bass_parts)
        
        # ===== 钟摆分解（pendulum）: 根-五度-根-五度 =====
        elif self.bass_arpeggio == 'pendulum':
            if len(chord_notes) < 2:
                # 如果和弦只有一个音，退回到 block
                root = chord_notes[0]
                return f"(vol 80) o{bass_octave} {root}1"
            
            root = chord_notes[0]
            fifth = chord_notes[1]  # 通常是五度音
            # 两个半音符来回
            return f"(vol 80) o{bass_octave} {root}2 {fifth}2"
        
        # 默认: block
        else:
            root = chord_notes[0]
            others = "/".join(chord_notes[1:]) if len(chord_notes) > 1 else ""
            chord = f"(vol 80) o{bass_octave} {root}1"
            if others:
                chord += f"/{others}"
            return chord

    def _generate_bar(
        self,
        chord_name: str,
        chord_notes: List[str],
        bar_idx: int,
    ) -> Tuple[str, List[str]]:
        """
        为单个小节生成音符序列
        
        每个小节的特点：
        - 4/4 拍子，总长 4 个四分音符时值
        - 只使用当前小节对应和弦的内音
        - 使用动机模板生成具有方向性的旋律
        - 第一个音符加重音（vol 95），其余正常音量（vol 80）
        
        参数：
            chord_name: 和弦名称（如 'C', 'Am' 等）
            chord_notes: 和弦内音列表
            bar_idx: 小节在全曲中的位置（用于选择节奏模板）
        
        返回：
            (旋律_Alda字符串, 节奏模式)
        """
        # 使用加权随机选择节奏模板，避免过多重复
        if len(self.style.bar_patterns) > 1:
            choices = list(range(len(self.style.bar_patterns)))
            weights = list(self.style.bar_pattern_weights)
            
            # 如果上一个节奏型存在，降低其权重（避免连续重复）
            if self._last_pattern_idx is not None and len(choices) > 1:
                # 将上一个节奏型的权重设为 0，这样就不会被选中
                weights[self._last_pattern_idx] = 0
            
            # 使用加权随机选择
            # 权重高的节奏型（复杂、有趣）出现频率更高
            pattern_idx = self.prng.choices(choices, weights=weights, k=1)[0]
        else:
            pattern_idx = 0
        
        pattern = self.style.bar_patterns[pattern_idx]
        self._last_pattern_idx = pattern_idx

        # 根据节奏模板计算需要的音符数
        num_notes = len(pattern)
        
        # 生成符合和弦的旋律音符 (音符名, 八度) 元组列表
        motif_notes = self._get_motif_notes(chord_notes, num_notes)
        
        # 组合音符和节奏，使用正确的 Alda 语法
        bar_parts = []
        current_octave = None
        
        for note_idx, duration in enumerate(pattern):
            note_name, octave = motif_notes[note_idx]
            
            # 如果八度变化，添加八度标记
            if octave != current_octave:
                bar_parts.append(f"o{octave}")
                current_octave = octave
            
            # 第一个音符加重音
            if note_idx == 0:
                bar_parts.append(f"(vol 95) {note_name}{duration}")
            else:
                bar_parts.append(f"(vol 80) {note_name}{duration}")
        
        return " ".join(bar_parts), pattern

    def compose_from_tokens(self, tokens: List[Token]) -> Tuple[str, dict]:
        """
        从 token 流生成完整钢琴乐曲
        
        架构：
        1. 将 token 流按 bars_per_phrase 分组成多个乐句
        2. 每个乐句按进行顺序循环使用一个和声进行
        3. 每个小节对应一个 token，只使用对应和弦的内音
        4. 生成 Alda 格式的有效乐谱
        
        参数：
            tokens: Token 对象列表（来自编译器）
        
        返回：
            (alda_score, metadata)
            - alda_score: Alda 格式的乐谱字符串
            - metadata: 包含乐谱元数据的字典
        """
        # 过滤掉 EOF token
        relevant_tokens = [t for t in tokens if t.type != TokenType.EOF]
        
        if not relevant_tokens:
            # token 为空时的默认乐谱
            return "piano:\n  o4 c1", {"phrases": 0, "bars": 0, "tokens": 0}

        num_tokens = len(relevant_tokens)
        # 计算乐句数
        num_phrases = (num_tokens + self.bars_per_phrase - 1) // self.bars_per_phrase
        
        melody_bars = []
        bass_bars = []
        bar_global_idx = 0
        
        # 为每个乐句生成音符
        for phrase_idx in range(num_phrases):
            # 在当前乐句中生成小节
            phrase_start = phrase_idx * self.bars_per_phrase
            phrase_end = min(phrase_start + self.bars_per_phrase, num_tokens)

            for token_idx in range(phrase_start, phrase_end):
                # 根据当前小节在乐句中的位置选择进行中的和弦
                step_in_phrase = (token_idx - phrase_start) % len(self.progression)
                chord_name, chord_notes = self.progression[step_in_phrase]

                # 为当前 token 生成一个小节（旋律）
                bar, pattern = self._generate_bar(chord_name, chord_notes, bar_global_idx)
                melody_bars.append(bar)

                # 生成低音小节（使用分解和弦模式）
                bass_bar = self._generate_bass_bar(chord_notes, pattern)
                bass_bars.append(bass_bar)
                bar_global_idx += 1

        # 生成 Alda 格式的乐谱
        # 使用 Alda 声部（Voices）在同一钢琴部分中同时进行
        alda_score = (
            f"piano:\n"
            f"  (tempo {self.tempo})\n"
            f"  V1: " + "\n  V1: ".join(melody_bars) + "\n"
            f"  V2: " + "\n  V2: ".join(bass_bars)
        )
        
        metadata = {
            "phrases": num_phrases,
            "bars": len(melody_bars),
            "tokens": num_tokens,
            "bars_per_phrase": self.bars_per_phrase,
            "progression": self.progression_name,
            "tempo": self.tempo,
        }
        
        return alda_score, metadata


def generate_piano_composition(
    c_source: str,
    chord_progression: str = 'I_vi_IV_V',
    tempo: int = 120,
    bars_per_phrase: int = 4,
    output_file: Optional[str] = None,
    export_midi: bool = False,
    midi_file: Optional[str] = None,
    export_mp3: bool = False,
    mp3_file: Optional[str] = None,
    style: str = 'default',
    bass_arpeggio: str = 'block',
    seed: Optional[int] = None,
) -> Tuple[str, dict]:
    """
    从 C 源码生成钢琴 Alda 曲
    
    工作流程：
    1. 使用 C 编译器将源码转换为 token 流
    2. 使用谱曲器将 token 按照和声进行转换为乐谱
    3. 可选地保存到 Alda、MIDI、MP3 文件
    
    参数：
        c_source: C 源码字符串
        chord_progression: 使用的和声进行（见 CHORD_PROGRESSIONS）
        tempo: 乐曲速度（BPM，默认 120）
        bars_per_phrase: 每个乐句的小节数（默认 4）
        output_file: 输出 Alda 文件路径（可选）
        export_midi: 是否导出 MIDI 文件（默认 False）
        midi_file: MIDI 输出文件路径（如不指定则自动生成）
        export_mp3: 是否导出 MP3 文件（默认 False）
        mp3_file: MP3 输出文件路径（如不指定则自动生成）
        style: 音乐风格 ('default' 或 'jazz', 默认 'default')
        seed: 随机数种子（用于复现结果）
    
    返回：
        (alda_score, metadata)
        - alda_score: Alda 格式的乐谱字符串
        - metadata: 乐谱的元数据（短语数、小节数等）
    
    异常：
        ValueError: 当使用未知的和声进行或风格时
    """
    # 第一步：编译 C 代码为 token 流
    tokens = compile_c_code(c_source)
    
    # 第二步：创建谱曲器并生成乐谱
    try:
        composer = Composer(
            chord_progression=chord_progression,
            tempo=tempo,
            bars_per_phrase=bars_per_phrase,
            style=style,
            bass_arpeggio=bass_arpeggio,
            seed=seed,
        )
    except ValueError as e:
        print(f"✗ 错误: {e}")
        raise
    
    alda_score, metadata = composer.compose_from_tokens(tokens)
    
    # 第三步：保存到文件（如果指定）
    if output_file:
        with open(output_file, 'w') as f:
            f.write(alda_score)
        print(f"✓ 钢琴曲已保存到: {output_file}")
    
    # 第四步：导出 MIDI（如果指定）
    if export_midi:
        if output_file is None:
            raise ValueError("导出 MIDI 需要先指定 output_file")
        
        midi_output = midi_file or output_file.replace('.alda', '.mid')
        export_to_midi(output_file, midi_output)
    
    # 第五步：导出 MP3（如果指定）
    if export_mp3:
        if output_file is None:
            raise ValueError("导出 MP3 需要先指定 output_file")
        
        mp3_output = mp3_file or output_file.replace('.alda', '.mp3')
        
        # 确保 MIDI 文件存在
        midi_path = midi_file or output_file.replace('.alda', '.mid')
        if not os.path.exists(midi_path):
            export_to_midi(output_file, midi_path)
        
        midi_to_mp3(midi_path, mp3_output)
    
    return alda_score, metadata


def play_alda_file(file_path: str) -> bool:
    """
    使用 Alda 播放器播放乐谱文件
    
    参数：
        file_path: Alda 文件路径
    
    返回：
        True 表示播放成功，False 表示失败
    """
    if not os.path.exists(file_path):
        print(f"✗ 文件不存在: {file_path}")
        return False
    
    try:
        print(f"🎵 正在播放: {file_path}")
        result = subprocess.run(
            ['alda', 'play', '-f', file_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("✓ 播放完成")
            return True
        else:
            print(f"✗ 播放出错: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ 未找到 Alda 播放器。请先安装 Alda")
        print("   安装指令: brew install alda (Mac) 或访问 https://alda.io")
        return False
    except subprocess.TimeoutExpired:
        print("✗ 播放超时")
        return False
    except Exception as e:
        print(f"✗ 播放出错: {e}")
        return False


def export_to_midi(
    alda_file: str,
    output_midi: Optional[str] = None,
) -> bool:
    """
    将 Alda 乐谱导出为 MIDI 文件
    
    参数：
        alda_file: Alda 乐谱文件路径
        output_midi: 输出 MIDI 文件路径（如不指定则自动生成）
    
    返回：
        True 表示导出成功，False 表示失败
    """
    if not os.path.exists(alda_file):
        print(f"✗ 文件不存在: {alda_file}")
        return False
    
    # 如果没有指定输出文件，自动生成名称
    if output_midi is None:
        # 将 .alda 替换为 .mid
        base_name = os.path.splitext(alda_file)[0]
        output_midi = f"{base_name}.mid"
    
    try:
        print(f"🎼 正在导出为 MIDI: {alda_file} → {output_midi}")
        result = subprocess.run(
            ['alda', 'export', '-f', alda_file, '-o', output_midi],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            # 获取文件大小
            file_size = os.path.getsize(output_midi) / 1024  # KB
            print(f"✓ MIDI 导出成功: {output_midi} ({file_size:.1f} KB)")
            return True
        else:
            print(f"✗ 导出失败: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ 未找到 Alda 工具。请先安装 Alda")
        print("   安装指令: brew install alda (Mac) 或访问 https://alda.io")
        return False
    except subprocess.TimeoutExpired:
        print("✗ 导出超时")
        return False
    except Exception as e:
        print(f"✗ 导出出错: {e}")
        return False


def midi_to_mp3(
    midi_file: str,
    output_mp3: Optional[str] = None,
) -> bool:
    """
    将 MIDI 文件转换为 MP3 音频文件
    
    依赖工具：
    - timidity: MIDI 音频合成
    - ffmpeg: 音频格式转换
    
    参数：
        midi_file: MIDI 文件路径
        output_mp3: 输出 MP3 文件路径（如不指定则自动生成）
    
    返回：
        True 表示转换成功，False 表示失败
    """
    if not os.path.exists(midi_file):
        print(f"✗ MIDI 文件不存在: {midi_file}")
        return False
    
    # 如果没有指定输出文件，自动生成名称
    if output_mp3 is None:
        base_name = os.path.splitext(midi_file)[0]
        output_mp3 = f"{base_name}.mp3"
    
    try:
        # 中间 WAV 文件（与输出 MP3 同名但后缀为 .wav）
        base_name = os.path.splitext(output_mp3)[0]
        temp_wav = f"{base_name}.wav"
        
        print(f"🎼 正在转换 MIDI 为 MP3...")
        print(f"   输入: {midi_file}")
        print(f"   输出: {output_mp3}")
        
        # 步骤 1：使用 timidity 将 MIDI 转为 WAV
        print("   第 1 步：合成音频 (timidity)...")
        result = subprocess.run(
            ['timidity', midi_file, '-Ow', '-o', temp_wav],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"✗ Timidity 错误: {result.stderr}")
            return False
        
        # 检查 WAV 文件是否生成
        if not os.path.exists(temp_wav):
            print(f"✗ WAV 文件生成失败")
            return False
        
        wav_size = os.path.getsize(temp_wav) / (1024 * 1024)
        print(f"   ✓ WAV 文件生成成功 ({wav_size:.2f} MB)")
        
        # 步骤 2：使用 ffmpeg 将 WAV 转为 MP3
        print("   第 2 步：转换格式 (ffmpeg)...")
        result = subprocess.run(
            ['ffmpeg', '-i', temp_wav, '-y', output_mp3],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # 清理临时 WAV 文件
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        if result.returncode == 0:
            # 获取文件大小
            file_size_kb = os.path.getsize(output_mp3) / 1024  # KB
            file_size_mb = file_size_kb / 1024  # MB
            size_display = f"{file_size_kb:.1f} KB" if file_size_kb < 1024 else f"{file_size_mb:.2f} MB"
            print(f"✓ MP3 转换成功: {output_mp3} ({size_display})")
            return True
        else:
            print(f"✗ ffmpeg 转换失败: {result.stderr}")
            return False
            
    except FileNotFoundError as e:
        missing_tool = str(e).split("'")[1] if "'" in str(e) else str(e)
        print(f"✗ 未找到工具: {missing_tool}")
        print("   请安装: brew install timidity ffmpeg")
        return False
    except subprocess.TimeoutExpired:
        print("✗ 转换超时")
        return False
    except Exception as e:
        print(f"✗ 转换出错: {e}")
        return False


def compose_to_mp3(
    c_source: str,
    chord_progression: str = 'I_vi_IV_V',
    tempo: int = 120,
    bars_per_phrase: int = 4,
    output_mp3: Optional[str] = 'piano_composition.mp3',
    style: str = 'default',
    seed: Optional[int] = None,
) -> bool:
    """
    从 C 源码一步到位生成 MP3 音频文件
    
    这是一个便捷函数，集成了代码编译、乐谱生成、MIDI 导出和格式转换
    
    工作流程：源代码 → Token 流 → Alda 乐谱 → MIDI 文件 → MP3 音频
    
    参数：
        c_source: C 源码字符串
        chord_progression: 和声进行名称
        tempo: 乐曲速度（BPM）
        bars_per_phrase: 每个乐句的小节数
        output_mp3: 输出 MP3 文件路径
        style: 音乐风格 ('default' 或 'jazz')
        seed: 随机数种子
    
    返回：
        True 表示成功，False 表示失败
    """
    # 生成中间文件名
    base_name = os.path.splitext(output_mp3)[0] if output_mp3 else 'output'
    midi_file = f"{base_name}.mid"
    alda_file = f"{base_name}.alda"
    
    print(f"🎼 代码到 MP3 转换流程")
    print("=" * 60)
    
    # 步骤 1：生成乐谱
    print("\n步骤 1: 代码 → Alda 乐谱")
    alda_score, metadata = generate_piano_composition(
        c_source,
        chord_progression=chord_progression,
        tempo=tempo,
        bars_per_phrase=bars_per_phrase,
        output_file=alda_file,
        style=style,
        seed=seed,
    )
    print(f"✓ 生成 {metadata['bars']} 小节的 Alda 乐谱")
    
    # 步骤 2：导出 MIDI
    print("\n步骤 2: Alda 乐谱 → MIDI 文件")
    if not export_to_midi(alda_file, midi_file):
        return False
    
    # 步骤 3：转换为 MP3
    print("\n步骤 3: MIDI 文件 → MP3 音频")
    if not midi_to_mp3(midi_file, output_mp3):
        return False
    
    print("\n" + "=" * 60)
    print(f"✓ 完成！MP3 文件已保存到: {output_mp3}")
    return True


def compose_and_play(
    c_source: str,
    chord_progression: str = 'I_vi_IV_V',
    tempo: int = 120,
    bars_per_phrase: int = 4,
    output_file: str = 'piano_composition.alda',
    play: bool = True,
    export_midi: bool = False,
    midi_file: Optional[str] = None,
    export_mp3: bool = False,
    mp3_file: Optional[str] = None,
    seed: Optional[int] = None,
) -> Tuple[str, dict]:
    """
    从 C 源码生成钢琴曲并播放
    
    参数：
        c_source: C 源码字符串
        chord_progression: 和声进行名称
        tempo: 乐曲速度（BPM）
        bars_per_phrase: 每个乐句的小节数
        output_file: 输出 Alda 文件路径
        play: 是否自动播放（默认 True）
        export_midi: 是否导出 MIDI 文件（默认 False）
        midi_file: MIDI 输出文件路径（如不指定则自动生成）
        export_mp3: 是否导出 MP3 文件（默认 False）
        mp3_file: MP3 输出文件路径（如不指定则自动生成）
        seed: 随机数种子
    
    返回：
        (alda_score, metadata)
    """
    alda_score, metadata = generate_piano_composition(
        c_source,
        chord_progression=chord_progression,
        tempo=tempo,
        bars_per_phrase=bars_per_phrase,
        output_file=output_file,
        seed=seed,
    )
    
    if play:
        play_alda_file(output_file)
    
    # 如果指定导出 MIDI

    if export_midi:
        midi_output = midi_file or output_file.replace('.alda', '.mid')
        export_to_midi(output_file, midi_output)
    
    # 如果指定导出 MP3
    if export_mp3:
        mp3_output = mp3_file or output_file.replace('.alda', '.mp3')
        
        # 确定 MIDI 文件路径
        midi_path = midi_file or output_file.replace('.alda', '.mid')
        
        # 如果还没有 MIDI 文件，先生成
        if not os.path.exists(midi_path):
            export_to_midi(output_file, midi_path)
        
        # 转换为 MP3
        midi_to_mp3(midi_path, mp3_output)
    
    return alda_score, metadata


# ========== 测试代码 ==========
if __name__ == "__main__":
    test_code = """
    #include <stdio.h>
    
    int main() {
        int x = 42;
        float y = 3.14;
        char* str = "Hello, World!";
        
        // 这是注释
        if (x > 0) {
            printf("x is positive\\n");
        }
        
        return 0;
    }
    """
    
    print("=" * 80)
    print("🎼 C 代码到钢琴乐谱编译器")
    print("=" * 80)
    
    # 第一步：编译 C 代码为 token 流
    tokens = compile_c_code(test_code)
    print("\n📊 Token 流分析:")
    print("-" * 80)
    for i, token in enumerate(tokens):
        if token.type != TokenType.EOF:
            print(f"  {i+1:3d}. {token}")
    print(f"\n  总计: {len([t for t in tokens if t.type != TokenType.EOF])} 个 tokens")
    
    # 第二步：生成钢琴乐谱
    print("\n" + "=" * 80)
    print("🎹 生成钢琴乐谱...")
    print("=" * 80 + "\n")
    
    alda_score, metadata = compose_and_play(
        test_code,
        chord_progression='I_vi_IV_V',       # 使用流行和声进行
        tempo=30,                             # 30 BPM
        bars_per_phrase=4,                    # 每个乐句 4 小节
        output_file='piano_composition.alda',
        play=True,                            # 自动播放
        export_midi=True,                     # 导出 MIDI 文件
        export_mp3=True,
        midi_file='piano_composition.mid',    # MIDI 文件名
        seed=42,                              # 固定随机种子（用于复现）
    )
    
    # 第三步：显示结果信息
    print("\n📋 乐谱元数据:")
    print("-" * 80)
    print(f"  乐句数: {metadata['phrases']}")
    print(f"  小节数: {metadata['bars']}")
    print(f"  Token 数: {metadata['tokens']}")
    print(f"  每句小节数: {metadata['bars_per_phrase']}")
    print(f"  和声进行: {metadata['progression']}")
    print(f"  速度: {metadata['tempo']} BPM")
    
    print("\n🎵 生成的 Alda 乐谱:")
    print("-" * 80)
    print(alda_score)
    print("-" * 80)
