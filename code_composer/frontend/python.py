"""
Python 代码前端 - 使用 Python 的 tokenize 模块
"""

import tokenize as py_tokenize
import io
from typing import List, Optional
from .lexer import Token, TokenType, BaseLexer


class PythonLexer(BaseLexer):
    """Python 语言词法分析器"""
    
    KEYWORDS = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
        'while', 'with', 'yield'
    }
    
    def tokenize(self) -> List[Token]:
        """
        使用 Python 的 tokenize 模块解析 Python 代码
        将其结果映射到通用 Token 类型
        """
        tokens = []
        try:
            # 将源代码转为字节流
            source_bytes = self.source.encode('utf-8')
            readline = io.BytesIO(source_bytes).readline
            
            # 使用 tokenize 模块
            for py_token in py_tokenize.tokenize(readline):
                token_type = py_token.type
                token_string = py_token.string
                token_start = py_token.start
                
                # 跳过编码和结束标记
                if token_type in (py_tokenize.ENCODING, py_tokenize.ENDMARKER):
                    continue
                
                # 映射 Python tokenize 类型到通用 Token 类型
                mapped_type = self._map_token_type(token_type, token_string)
                
                if mapped_type:
                    tokens.append(Token(
                        mapped_type,
                        token_string,
                        token_start[0],
                        token_start[1]
                    ))
        except py_tokenize.TokenError:
            # 处理不完整的 Python 代码
            pass
        
        tokens.append(Token(TokenType.EOF, '', 0, 0))
        return tokens
    
    def _map_token_type(self, py_token_type: int, token_string: str) -> Optional[TokenType]:
        """将 Python tokenize 类型映射到通用 Token 类型"""
        
        if py_token_type == py_tokenize.NAME:
            # 检查是否为关键字
            if token_string in self.KEYWORDS:
                return TokenType.KEYWORD
            else:
                return TokenType.IDENTIFIER
        
        elif py_token_type == py_tokenize.NUMBER:
            return TokenType.NUMBER
        
        elif py_token_type == py_tokenize.STRING:
            return TokenType.STRING
        
        elif py_token_type == py_tokenize.OP:
            # 根据操作符类型分类
            if token_string == '(':
                return TokenType.LPAREN
            elif token_string == ')':
                return TokenType.RPAREN
            elif token_string == '{':
                return TokenType.LBRACE
            elif token_string == '}':
                return TokenType.RBRACE
            elif token_string == '[':
                return TokenType.LBRACKET
            elif token_string == ']':
                return TokenType.RBRACKET
            elif token_string == ';':
                return TokenType.SEMICOLON
            elif token_string == ',':
                return TokenType.COMMA
            elif token_string == '.':
                return TokenType.DOT
            elif token_string == ':':
                return TokenType.COLON
            elif token_string == '?':
                return TokenType.QUESTION
            else:
                return TokenType.OPERATOR
        
        elif py_token_type == py_tokenize.NEWLINE or py_token_type == py_tokenize.NL:
            return TokenType.NEWLINE
        
        elif py_token_type == py_tokenize.COMMENT:
            # 注释通常忽略，但可以选择保留为 KEYWORD
            return None
        
        elif py_token_type == py_tokenize.INDENT or py_token_type == py_tokenize.DEDENT:
            # Python 特有的缩进标记，映射为 NEWLINE
            return None
        
        else:
            return None


def compile_python_code(source: str) -> List[Token]:
    """
    编译 Python 源码为 token stream
    
    参数:
        source: Python 源码字符串
    
    返回:
        Token 列表
    """
    lexer = PythonLexer(source)
    return lexer.tokenize()
