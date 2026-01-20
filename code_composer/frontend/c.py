"""
C 代码前端 - 使用 pycparser 库进行解析
"""

from pycparser import c_parser, c_ast
from typing import List
from .lexer import Token, TokenType, BaseLexer


class CLexer(BaseLexer):
    """C 语言词法分析器 - 基于 pycparser AST"""
    
    KEYWORDS = {
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'inline', 'int', 'long', 'register', 'restrict', 'return', 'short',
        'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
        'unsigned', 'void', 'volatile', 'while', '_Bool', '_Complex', '_Imaginary'
    }
    
    def __init__(self, source: str):
        super().__init__(source)
        self.tokens = []
    
    def tokenize(self) -> List[Token]:
        """
        使用 pycparser 解析 C 代码并提取 token 流
        返回语法单元的序列（不是简单的字符级 token）
        """
        try:
            # 创建解析器
            parser = c_parser.CParser()
            
            # 尝试解析代码
            try:
                ast = parser.parse(self.source, filename='<stdin>')
            except Exception:
                # 如果解析失败，尝试添加主函数包装
                wrapped_source = f"""
                void __dummy__() {{
                    {self.source}
                }}
                """
                try:
                    ast = parser.parse(wrapped_source, filename='<stdin>')
                except Exception:
                    # 降级到简单的词法分析
                    return self._simple_tokenize()
            
            # 遍历 AST 提取 token
            self.tokens = self._extract_tokens_from_ast(ast)
            
        except Exception as e:
            # 如果 AST 解析失败，回退到简单的词法分析
            return self._simple_tokenize()
        
        self.tokens.append(Token(TokenType.EOF, '', 0, 0))
        return self.tokens
    
    def _extract_tokens_from_ast(self, node) -> List[Token]:
        """递归遍历 AST，提取 token"""
        tokens = []
        
        if node is None:
            return tokens
        
        # 对不同类型的 AST 节点进行处理
        if isinstance(node, c_ast.FileAST):
            # 文件的根节点
            for ext in (node.ext or []):
                tokens.extend(self._extract_tokens_from_ast(ext))
        
        elif isinstance(node, c_ast.Decl):
            # 声明（变量、函数等）
            # 顺序：storage(如 static) → type(如 int) → name(如 x) → init(如 = 42)
            if node.storage:
                for s in node.storage:
                    tokens.append(self._make_token(TokenType.KEYWORD, s))
            
            if node.type:
                tokens.extend(self._extract_tokens_from_ast(node.type))
            
            if node.name:
                tokens.append(self._make_token(TokenType.IDENTIFIER, node.name))
            
            if node.init:
                tokens.append(self._make_token(TokenType.OPERATOR, '='))
                tokens.extend(self._extract_tokens_from_ast(node.init))
        
        elif isinstance(node, c_ast.FuncDecl):
            # 函数声明
            tokens.append(self._make_token(TokenType.KEYWORD, 'func'))
            if node.args:
                tokens.extend(self._extract_tokens_from_ast(node.args))
            if node.type:
                tokens.extend(self._extract_tokens_from_ast(node.type))
        
        elif isinstance(node, c_ast.FuncDef):
            # 函数定义
            tokens.append(self._make_token(TokenType.KEYWORD, 'func'))
            if node.decl and node.decl.name:
                tokens.append(self._make_token(TokenType.IDENTIFIER, node.decl.name))
            if node.body:
                tokens.extend(self._extract_tokens_from_ast(node.body))
        
        elif isinstance(node, c_ast.If):
            # If 语句
            tokens.append(self._make_token(TokenType.KEYWORD, 'if'))
            tokens.extend(self._extract_tokens_from_ast(node.cond))
            if node.iftrue:
                tokens.extend(self._extract_tokens_from_ast(node.iftrue))
            if node.iffalse:
                tokens.append(self._make_token(TokenType.KEYWORD, 'else'))
                tokens.extend(self._extract_tokens_from_ast(node.iffalse))
        
        elif isinstance(node, c_ast.For):
            # For 循环
            tokens.append(self._make_token(TokenType.KEYWORD, 'for'))
            if node.init:
                tokens.extend(self._extract_tokens_from_ast(node.init))
            if node.cond:
                tokens.extend(self._extract_tokens_from_ast(node.cond))
            if node.next:
                tokens.extend(self._extract_tokens_from_ast(node.next))
            if node.stmt:
                tokens.extend(self._extract_tokens_from_ast(node.stmt))
        
        elif isinstance(node, c_ast.While):
            # While 循环
            tokens.append(self._make_token(TokenType.KEYWORD, 'while'))
            tokens.extend(self._extract_tokens_from_ast(node.cond))
            tokens.extend(self._extract_tokens_from_ast(node.stmt))
        
        elif isinstance(node, c_ast.Return):
            # Return 语句
            tokens.append(self._make_token(TokenType.KEYWORD, 'return'))
            if node.expr:
                tokens.extend(self._extract_tokens_from_ast(node.expr))
        
        elif isinstance(node, c_ast.BinaryOp):
            # 二元运算
            tokens.extend(self._extract_tokens_from_ast(node.left))
            tokens.append(self._make_token(TokenType.OPERATOR, node.op))
            tokens.extend(self._extract_tokens_from_ast(node.right))
        
        elif isinstance(node, c_ast.UnaryOp):
            # 一元运算
            tokens.append(self._make_token(TokenType.OPERATOR, node.op))
            tokens.extend(self._extract_tokens_from_ast(node.expr))
        
        elif isinstance(node, c_ast.ID):
            # 标识符
            tokens.append(self._make_token(TokenType.IDENTIFIER, node.name))
        
        elif isinstance(node, c_ast.Constant):
            # 常数
            if node.type == 'int':
                tokens.append(self._make_token(TokenType.NUMBER, node.value))
            else:
                tokens.append(self._make_token(TokenType.STRING, node.value))
        
        elif isinstance(node, c_ast.Assignment):
            # 赋值
            tokens.extend(self._extract_tokens_from_ast(node.lvalue))
            tokens.append(self._make_token(TokenType.OPERATOR, node.op))
            tokens.extend(self._extract_tokens_from_ast(node.rvalue))
        
        elif isinstance(node, c_ast.Compound):
            # 复合语句（代码块）
            if node.block_items:
                for item in node.block_items:
                    tokens.extend(self._extract_tokens_from_ast(item))
        
        elif isinstance(node, c_ast.ParamList):
            # 参数列表
            for param in node.params:
                tokens.extend(self._extract_tokens_from_ast(param))
        
        elif isinstance(node, c_ast.TypeDecl):
            # 类型声明 - 只输出类型本身，不输出 declname（declname 在 Decl 中处理）
            if node.type:
                tokens.extend(self._extract_tokens_from_ast(node.type))
        
        elif isinstance(node, c_ast.IdentifierType):
            # 类型名
            type_name = ' '.join(node.names)
            if type_name in self.KEYWORDS:
                tokens.append(self._make_token(TokenType.KEYWORD, type_name))
            else:
                tokens.append(self._make_token(TokenType.IDENTIFIER, type_name))
        
        elif isinstance(node, c_ast.FuncCall):
            # 函数调用
            tokens.append(self._make_token(TokenType.KEYWORD, 'call'))
            tokens.extend(self._extract_tokens_from_ast(node.name))
            if node.args:
                tokens.extend(self._extract_tokens_from_ast(node.args))
        
        elif isinstance(node, c_ast.ExprList):
            # 表达式列表
            for i, expr in enumerate(node.exprs):
                if i > 0:
                    tokens.append(self._make_token(TokenType.COMMA, ','))
                tokens.extend(self._extract_tokens_from_ast(expr))
        
        else:
            # 对于其他节点类型，尝试递归处理
            for attr_name, child_node in node.children():
                tokens.extend(self._extract_tokens_from_ast(child_node))
        
        return tokens
    
    def _make_token(self, token_type: TokenType, value: str) -> Token:
        """创建一个 token"""
        return Token(token_type, value, 0, 0)
    
    def _simple_tokenize(self) -> List[Token]:
        """
        简单的词法分析 - 当 AST 解析失败时使用
        按空白和标点符号分割源代码
        """
        tokens = []
        import re
        
        # 分割标记
        pattern = r'(\w+|[(){}\[\];:,.]|[+\-*/%=<>!&|^?]|//.*?$|/\*.*?\*/)'
        matches = re.finditer(pattern, self.source, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            text = match.group(0)
            
            # 跳过空白和注释
            if not text or text.isspace() or text.startswith('//') or text.startswith('/*'):
                continue
            
            # 识别 token 类型
            if text in self.KEYWORDS:
                token_type = TokenType.KEYWORD
            elif re.fullmatch(r'\d+(\.\d+)?([eE][+-]?\d+)?', text):
                token_type = TokenType.NUMBER
            elif text == '(':
                token_type = TokenType.LPAREN
            elif text == ')':
                token_type = TokenType.RPAREN
            elif text == '{':
                token_type = TokenType.LBRACE
            elif text == '}':
                token_type = TokenType.RBRACE
            elif text == '[':
                token_type = TokenType.LBRACKET
            elif text == ']':
                token_type = TokenType.RBRACKET
            elif text == ',':
                token_type = TokenType.COMMA
            elif text == ';':
                token_type = TokenType.SEMICOLON
            elif text == ':':
                token_type = TokenType.COLON
            elif text == '.':
                token_type = TokenType.DOT
            else:
                token_type = TokenType.IDENTIFIER
            
            tokens.append(Token(token_type, text, 0, 0))
        
        return tokens


def compile_c_code(source: str) -> List[Token]:
    """
    编译 C 源码为 token stream
    使用 pycparser 进行完整的 C 代码解析
    
    参数:
        source: C 源码字符串
    
    返回:
        Token 列表
    """
    lexer = CLexer(source)
    return lexer.tokenize()
