"""
音乐导出模块：Alda/MIDI/MP3 格式转换和播放

提供：
- Alda 乐谱导出为 MIDI
- MIDI 转换为 MP3（通过 timidity + ffmpeg）
- Alda 乐谱播放
"""

import os
import subprocess
from typing import Optional


def play_alda_file(file_path: str) -> bool:
    """使用 Alda 播放器播放乐谱文件"""
    if not os.path.exists(file_path):
        print(f"✗ 文件不存在: {file_path}")
        return False

    try:
        print(f"🎵 播放: {file_path}")
        subprocess.run(
            ['alda', 'play', '-f', file_path],
            check=True,
            capture_output=True,
            timeout=300
        )
        return True
    except FileNotFoundError:
        print("✗ 未找到 alda 命令。请确保 alda 已安装。")
        print("   安装指南: https://alda.io/setup/")
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
    """将 Alda 乐谱导出为 MIDI 文件"""
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
    """将 MIDI 文件转换为 MP3 音频文件"""
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
