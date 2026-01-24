"""
Code Composer 命令行工具
将源代码转换为音乐
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Tuple

from .composer import compose
from .frontend import compile_c_code
from .styles import create_style_with, get_style, list_styles
from .config_loader import load_scales, list_available_bass_patterns
from .exporter import export_to_midi, midi_to_mp3, play_alda_code
from .structures import print_composition_tree
from .theory import (
    get_available_progressions,
    get_default_progression,
    gen_scale_alda,
    gen_progression_alda,
)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='code-composer',
        description='将源代码转换为音乐 - Code-to-Music Compiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  # 从文件读取 C 代码并转换为 MP3
  uv run python -m code_composer -f code.c -o music.mp3
  
  # 从命令行传入 Python 代码
  uv run python -m code_composer -c "x = 42; y = x + 1" --lang python -o output.mp3
  
  # 生成所有格式（Alda、MIDI、MP3）
  uv run python -m code_composer -f code.c --export-all -o music
  
  # 使用自定义和声进行和速度
  uv run python -m code_composer -f code.c -o music.mp3 --chord IV_V_iii_vi_ii_V_I --tempo 140
        '''
    )
    
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        '-f', '--file',
        type=str,
        help='输入源代码文件路径（支持 .c 和 .py）'
    )
    input_group.add_argument(
        '-c', '--code',
        type=str,
        help='直接传入源代码字符串'
    )
    
    # 输入语言
    parser.add_argument(
        '--lang',
        type=str,
        choices=['c', 'python', 'auto'],
        default='auto',
        help='源代码语言（默认自动判断）'
    )

    parser.add_argument(
        '--key',
        type=str,
        default=None,
        help='乐曲调（如 C, G, D#, Bb，默认使用风格的默认值）'
    )
    parser.add_argument(
        '--scale',
        type=str,
        default=None,
        help='音阶/调式（默认使用风格的默认值，可用: ' + ', '.join(load_scales().keys()) + '）'
    )
    
    parser.add_argument(
        '--test-scale',
        action='store_true',
        help='测试模式：只播放当前音阶（覆盖2个八度），不生成旋律'
    )

    parser.add_argument(
        '--test-chord',
        action='store_true',
        help='测试模式：只播放当前和声进行（分解和弦），不生成旋律'
    )
    
    # 输出参数
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='输出文件名（不含扩展名）或路径。如不指定则只播放不保存'
    )
    
    parser.add_argument(
        '--chord',
        type=str,
        default=None,  # 改为 None，在运行时根据音阶自动选择
        help='和声进行（不指定则根据音阶自动选择推荐进行）'
    )
    
    parser.add_argument(
        '--style',
        type=str,
        default='default',
        help='音乐风格（可用: ' + ', '.join(list_styles()) + '）'
    )
    
    parser.add_argument(
        '--tempo',
        type=int,
        default=None,
        help='乐曲速度 BPM（默认：120，waltz/minuet 为 160）'
    )
    
    parser.add_argument(
        '--bass-pattern',
        type=str,
        choices=list_available_bass_patterns(),
        default=None,
        help='低音模式（默认使用风格的低音模式）',
    )
    
    parser.add_argument(
        '--bars-per-phrase',
        type=int,
        default=4,
        help='每个乐句的小节数（默认：4）'
    )

    parser.add_argument(
        '--bars-per-token',
        type=int,
        choices=[1, 2],
        default=1,
        help='一个 token 覆盖的小节数（1 或 2，默认 1）'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='随机数种子（默认：42，用于复现结果）'
    )
    
    parser.add_argument(
        '--parts',
        type=str,
        choices=['melody', 'bass', 'both'],
        default='both',
        help='输出部分：melody（仅旋律 V1）bass（仅低音 V2）both（两者，默认）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出信息'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='生成后打印作品的树形结构信息'
    )
    
    parser.add_argument(
        '--no-play',
        action='store_true',
        help='生成后不自动播放音乐'
    )

    parser.add_argument(
        '--ignore-bad',
        action='store_true',
        help='忽略不和谐和弦变体'
    )

    parser.add_argument(
        '--instrument',
        type=str,
        default=None,
        help='使用的乐器'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    return parser


def detect_language(source: str) -> str:
    """自动检测源代码语言"""
    # 检查 C 风格特征
    c_keywords = ['#include', 'int', 'char', 'void', 'return', 'if', 'for', 'while']
    # 检查 Python 风格特征
    python_keywords = ['import', 'def', 'class', 'print', 'for', 'while', 'with']
    
    c_count = sum(1 for kw in c_keywords if kw in source)
    py_count = sum(1 for kw in python_keywords if kw in source)
    
    if c_count > py_count:
        return 'c'
    elif py_count > c_count:
        return 'python'
    else:
        # 默认返回 C
        return 'c'


def play_audio(alda_file: str, verbose: bool = False) -> bool:
    """使用 alda 命令播放音乐"""
    import subprocess
    
    path = Path(alda_file)
    if not path.exists():
        return False
    
    try:
        if verbose:
            print(f"🎵 播放: {path}")
        subprocess.run(['alda', 'play', '-f', str(path)], check=True, capture_output=True)
        return True
    except FileNotFoundError:
        print("❌ 错误: 未找到 alda 命令。请确保 alda 已安装。")
        print("   安装指南: https://alda.io/setup/")
        return False
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"⚠️  播放失败: {e}")
        return False
    except Exception as e:
        if verbose:
            print(f"⚠️  播放错误: {e}")
        return False


def read_source_file(filepath: str) -> Tuple[str, str]:
    """读取源代码文件，返回 (代码, 语言)"""
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 根据文件扩展名判断语言
    suffix = path.suffix.lower()
    if suffix == '.c':
        lang = 'c'
    elif suffix == '.py':
        lang = 'python'
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")
    
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    return source, lang


def determine_output_path(output: str, format_type: str) -> str:
    """确定输出文件路径"""
    path = Path(output)
    
    # 获取基础名称（不含扩展名）
    stem = path.stem
    parent = path.parent
    
    # 构建基础路径
    base_path = parent / stem
    
    # 添加扩展名
    if format_type == 'alda':
        return str(base_path.with_suffix('.alda'))
    elif format_type == 'midi':
        return str(base_path.with_suffix('.mid'))
    elif format_type == 'mp3':
        return str(base_path.with_suffix('.mp3'))
    else:
        return str(base_path)


def main() -> None:
    """主命令行入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 验证：非测试模式下必须提供输入源代码
    if not args.test_scale and not args.test_chord and not args.file and not args.code:
        parser.error("需要提供 -f/--file 或 -c/--code 参数，除非使用 --test-scale/--test-chord 模式")
    
    # 从风格获取默认值，用户指定的参数覆盖
    style_obj = get_style(args.style)
    if style_obj is None:
        print(f"❌ 错误: 未知的风格: {args.style}", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"🎵 使用风格: {args.style}")
        print(f"   调性: {args.key}, 音阶: {args.scale}, 速度: {args.tempo} BPM")
        available = get_available_progressions(args.scale, args.style)
        print(f"   和声进行: {args.chord} ({available[args.chord]})")
    
    # 初始化临时文件变量
    use_temp_file = False
    temp_dir = None
    original_output = args.output  # 保存原始输出路径

    # 如果没有指定输出文件
    if args.output is None:
        # 用户显式要求不播放但也不输出文件，直接报错
        if args.no_play:
            parser.error("❌ 错误: 使用 --no-play 时必须通过 -o 指定输出文件。")

        # 未禁用播放则使用临时目录输出并自动播放
        use_temp_file = True
        temp_dir = tempfile.mkdtemp(prefix='code_composer_')
        args.output = os.path.join(temp_dir, 'temp_music')
    
    try:
        # 处理测试模式：音阶 / 和弦进行
        if args.test_scale or args.test_chord:
            if args.test_scale:
                if args.verbose:
                    print(f"🎵 音阶测试模式")
                    print(f"   调性: {args.key}, 音阶: {args.scale}")
                alda_code = gen_scale_alda(args.key, args.scale, args.tempo)
            else:
                if args.verbose:
                    print(f"🎵 和弦进行测试模式")
                    print(f"   调性: {args.key}, 音阶: {args.scale}, 进行: {args.chord}")
                alda_code = gen_progression_alda(args.key, args.scale, args.chord, args.tempo)
            
            alda_file = None
            if original_output:
                alda_file = determine_output_path(original_output, 'alda')
                with open(alda_file, 'w') as f:
                    f.write(alda_code)
                label = "音阶" if args.test_scale else "和弦进行"
                print(f"✓ {label}已保存到: {alda_file}")
            elif args.verbose:
                print("✓ Alda 代码已生成")
            
            # 导出 MIDI 和 MP3（如果指定了输出）
            if original_output and alda_file:
                midi_file = determine_output_path(original_output, 'midi')
                mp3_file = determine_output_path(original_output, 'mp3')
                
                # 导出 MIDI
                if export_to_midi(alda_file, midi_file):
                    # 转换 MP3
                    midi_to_mp3(midi_file, mp3_file)
            
            if not args.no_play:
                play_alda_code(alda_code)
            return
        
        # 读取源代码
        if args.file:
            if args.verbose:
                print(f"📖 读取文件: {args.file}")
            source, detected_lang = read_source_file(args.file)
        else:
            source = args.code
            detected_lang = None
        
        # 确定语言
        if args.lang == 'auto':
            lang = detected_lang or detect_language(source)
        else:
            lang = args.lang
        
        if args.verbose:
            print(f"🔍 检测到语言: {lang.upper()}")
            print(f"📝 代码行数: {len(source.splitlines())}")
        

        # ===== 生成音乐 =====
        if args.verbose:
            print(f"\n🎼 生成 {args.format.upper()} 格式...")
        
        # 编译源码并构造 Style
        tokens = compile_c_code(source)
        style_obj = create_style_with(
            args.style,
            key=args.key,
            scale=args.scale,
            tempo=args.tempo,
            progression=args.chord,
            bass_pattern=args.bass_pattern,
            instrument=args.instrument,
        )
        alda_score, comp = compose(
            style=style_obj,
            tokens=tokens,
            seed=args.seed,
            parts=args.parts,
            ignore_bad=args.ignore_bad,
        )
        # 保存 Alda 文件
        alda_file = determine_output_path(args.output, 'alda')
        midi_file = determine_output_path(args.output, "midi")
        mp3_file = determine_output_path(args.output, "mp3")
        sf_file = Path(__file__).parent.parent / "sf" / "GeneralUser-GS.sf2"
        
        with open(alda_file, 'w') as f:
            f.write(alda_score)
        
        # 根据格式要求进行导出
        export_to_midi(alda_file, midi_file)
        midi_to_mp3(midi_file, mp3_file, str(sf_file))
        
        print(f"✓ 生成成功!")
        
        # 调试输出：作品树形结构
        if args.debug:
            print("\n[DEBUG] 作品树形结构:")
            print("-" * 80)
            print(print_composition_tree(comp))
        
        # 自动播放（总是播放 Alda 文件）
        if not args.no_play:
            play_audio(alda_file, verbose=args.verbose)
    
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # 清理临时文件
        if use_temp_file and temp_dir:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


if __name__ == '__main__':
    main()
