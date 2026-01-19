"""
计算阶乘
"""

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def main():
    result = factorial(6)
    print(result)

if __name__ == '__main__':
    main()
