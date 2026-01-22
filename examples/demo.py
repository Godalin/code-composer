"""
Code Composer 使用示例
"""

from code_composer.composer import compose
from code_composer.exporter import export_to_midi, midi_to_mp3
from code_composer.frontend.c import compile_c_code
from code_composer.styles import get_style

# 示例 1：Fibonacci 数列
fibonacci_code = """
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}

int main() {
    int result = fibonacci(10);
    return 0;
}
"""

if __name__ == "__main__":
    # 转换为 MP3
    alda_file = './out.alda'
    midi_file = './out.midi'
    mp3_file = './out.mp3'

    # 获取 Style 并编译源码
    style_obj = get_style("default")
    tokens = compile_c_code(fibonacci_code)
    alda_score, metadata, comp = compose(
        style=style_obj,
        tokens=tokens,
    )

    # 保存 Alda 文件
    with open(alda_file, 'w') as f:
        f.write(alda_score)

    # 导出 MIDI
    export_to_midi(alda_file, midi_file)

    # 导出 MP3
    midi_to_mp3(midi_file, mp3_file)
