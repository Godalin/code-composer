"""
Code Composer 命令行工具
将源代码转换为音乐
"""

import argparse
import sys
from pathlib import Path

from .composer import compose_to_mp3, generate_piano_composition


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='code-composer',
        description='将源代码转换为音乐 - Code-to-Music Compiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  # 从文件读取 C 代码并转换为 MP3
  code-composer -f code.c -o music.mp3
  
  # 从命令行传入 Python 代码
  code-composer -c "x = 42; y = x + 1" --lang python -o output.mp3
  
  # 生成所有格式（Alda、MIDI、MP3）
  code-composer -f code.c --export-all -o music
  
  # 使用自定义和声进行和速度
  code-composer -f code.c -o music.mp3 --chord IV_V_iii_vi_ii_V_I --tempo 140
        '''
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
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
    
    # 输出参数
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='输出文件名（不含扩展名）或路径。如不指定则只播放不保存'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['alda', 'midi', 'mp3'],
        default='mp3',
        help='输出格式（默认：mp3）'
    )
    
    parser.add_argument(
        '--export-all',
        action='store_true',
        help='导出所有格式（.alda、.mid、.mp3）'
    )
    
    # 音乐参数
    parser.add_argument(
        '--chord',
        type=str,
        choices=['I_vi_IV_V', 'I_V_IV_vi', 'IV_V_iii_vi_ii_V_I', 'Imaj7_vi7_ii7_V7', 'II_V_I', 'VI_ii_V_I'],
        default='I_vi_IV_V',
        help='和声进行（默认：I_vi_IV_V）'
    )
    
    parser.add_argument(
        '--style',
        type=str,
        choices=['default', 'jazz'],
        default='default',
        help='音乐风格（默认：default）'
    )
    
    parser.add_argument(
        '--tempo',
        type=int,
        default=120,
        help='乐曲速度 BPM（默认：120）'
    )
    
    parser.add_argument(
        '--bars-per-phrase',
        type=int,
        default=4,
        help='每个乐句的小节数（默认：4）'
    )
    
    parser.add_argument(
        '--bass-arpeggio',
        type=str,
        choices=['block', 'double', 'follow', 'arpeggio', 'pendulum'],
        default='block',
        help='低音分解和弦模式（默认：block）'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='随机数种子（用于复现结果）'
    )
    
    # 其他选项
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出信息'
    )
    
    parser.add_argument(
        '--no-play',
        action='store_true',
        help='生成后不自动播放音乐'
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


def read_source_file(filepath: str) -> tuple[str, str]:
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


def main():
    """主命令行入口"""
    import tempfile
    import os
    import shutil
    
    parser = create_parser()
    args = parser.parse_args()
    
    # 初始化临时文件变量
    use_temp_file = False
    temp_dir = None
    
    # 如果没有指定输出文件，使用临时文件
    if args.output is None:
        use_temp_file = True
        # 创建临时目录和文件
        temp_dir = tempfile.mkdtemp(prefix='code_composer_')
        args.output = os.path.join(temp_dir, 'temp_music')
        args.no_play = False  # 确保会播放
    
    try:
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
        
        # 生成音乐
        if args.export_all:
            # 导出所有格式
            base_output = args.output
            
            if args.verbose:
                print(f"\n🎼 生成所有格式...")
            
            alda_file = determine_output_path(base_output, 'alda')
            midi_file = determine_output_path(base_output, 'midi')
            mp3_file = determine_output_path(base_output, 'mp3')
            
            alda_score, metadata = generate_piano_composition(
                source,
                chord_progression=args.chord,
                tempo=args.tempo,
                bars_per_phrase=args.bars_per_phrase,
                bass_arpeggio=args.bass_arpeggio,
                output_file=alda_file,
                export_midi=True,
                midi_file=midi_file,
                export_mp3=True,
                mp3_file=mp3_file,
                style=args.style,
                seed=args.seed
            )
            
            print(f"✓ 生成成功!")
            print(f"  • Alda:  {alda_file}")
            print(f"  • MIDI:  {midi_file}")
            print(f"  • MP3:   {mp3_file}")
            print(f"  • 小节数: {metadata['bars']}")
            
            # 自动播放 Alda
            if not args.no_play:
                print()
                play_audio(alda_file, verbose=args.verbose)
        
        else:
            # 单一格式导出
            output_file = determine_output_path(args.output, args.format)
            alda_file = determine_output_path(args.output, 'alda')
            
            if args.verbose:
                print(f"\n🎼 生成 {args.format.upper()} 格式...")
            
            # 生成 Alda 文件和其他格式
            alda_score, metadata = generate_piano_composition(
                source,
                chord_progression=args.chord,
                tempo=args.tempo,
                bars_per_phrase=args.bars_per_phrase,
                bass_arpeggio=args.bass_arpeggio,
                output_file=alda_file,
                export_midi=(args.format in ['midi', 'mp3']),
                midi_file=output_file if args.format == 'midi' else None,
                export_mp3=(args.format == 'mp3'),
                mp3_file=output_file if args.format == 'mp3' else None,
                style=args.style,
                seed=args.seed
            )
            success = True
            
            if success:
                print(f"✓ 生成成功!")
                print(f"  📁 输出文件: {output_file}")
                
                # 自动播放（总是播放 Alda 文件）
                if not args.no_play:
                    print()
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
