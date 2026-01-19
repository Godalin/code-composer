"""
基础词法分析器模块：定义 Token 和 BaseLexer 接口
"""

from enum import Enum, auto
from typing import List


class TokenType(Enum):
    """通用 Token 类型定义"""
    # 关键字
    KEYWORD = auto()
    
    # 标识符和字面量
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    CHAR = auto()
    
    # 操作符
    OPERATOR = auto()
    
    # 分隔符
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    SEMICOLON = auto()   # ;
    COMMA = auto()       # ,
    DOT = auto()         # .
    COLON = auto()       # :
    QUESTION = auto()    # ?
    
    # 特殊
    EOF = auto()
    NEWLINE = auto()


class Token:
    """代表一个词素（Token）"""
    
    def __init__(self, type_: TokenType, value: str, line: int = 0, col: int = 0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col
    
    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}, {self.col})"


class BaseLexer:
    """基础词法分析器接口"""
    
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """将源代码分词，返回 Token 列表（需子类实现）"""
        raise NotImplementedError("Subclass must implement tokenize()")
