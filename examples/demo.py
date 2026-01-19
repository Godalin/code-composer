"""
Code Composer 使用示例
"""

from code_composer import compose_to_mp3

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
    compose_to_mp3(
        fibonacci_code,
        output_mp3="output/fibonacci.mp3",
        tempo=120,
        bars_per_phrase=4
    )
    
    print("✓ 示例运行完成！生成的 MP3 文件在 output 目录中")
