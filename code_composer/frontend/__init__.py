"""
前端模块：支持多语言代码解析和 Token 转换

包含：
- lexer: 通用词法分析接口
- c: C 语言前端（使用 pycparser）
- python: Python 语言前端（使用 tokenize）
"""

from .lexer import Token, TokenType, BaseLexer
from .c import compile_c_code
from .python import compile_python_code

__all__ = [
    "Token",
    "TokenType",
    "BaseLexer",
    "compile_c_code",
    "compile_python_code",
]
