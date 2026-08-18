import json
from enum import Enum
from typing import List

class TokenType(Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    COMMENT = "COMMENT"
    WHITESPACE = "WHITESPACE"
    PUNCTUATION = "PUNCTUATION"
    EOF = "EOF"

class Token:
    def __init__(self, type: TokenType, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

class LuaLexer:
    KEYWORDS = {
        'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
        'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or',
        'repeat', 'return', 'then', 'true', 'until', 'while'
    }
    
    OPERATORS = {
        '+', '-', '*', '/', '%', '^', '==', '~=', '!=', '<=', '>=',
        '<', '>', '=', '(', ')', '{', '}', '[', ']', ';', ':', ',',
        '.', '..', '...', '#', '&', '|', '~', '<<', '>>'
    }
    
    def __init__(self, code: str):
        self.code = code
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def peek(self, offset=0) -> str:
        pos = self.pos + offset
        return self.code[pos] if pos < len(self.code) else ''
    
    def advance(self) -> str:
        if self.pos >= len(self.code):
            return ''
        char = self.code[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def read_string(self, quote: str) -> str:
        result = ''
        self.advance()
        while self.pos < len(self.code):
            char = self.peek()
            if char == quote:
                self.advance()
                break
            elif char == '\\':
                self.advance()
                next_char = self.advance()
                escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"}
                result += escape_map.get(next_char, next_char)
            else:
                result += self.advance()
        return result
    
    def read_number(self) -> str:
        result = ''
        while self.peek().isdigit():
            result += self.advance()
        if self.peek() == '.':
            result += self.advance()
            while self.peek().isdigit():
                result += self.advance()
        return result
    
    def read_identifier(self) -> str:
        result = ''
        while self.peek().isalnum() or self.peek() == '_':
            result += self.advance()
        return result
    
    def tokenize(self) -> List[Token]:
        while self.pos < len(self.code):
            line, column = self.line, self.column
            char = self.peek()
            
            if char in ' \t\n\r':
                ws = ''
                while self.peek() in ' \t\n\r':
                    ws += self.advance()
                self.tokens.append(Token(TokenType.WHITESPACE, ws, line, column))
            elif char == '-' and self.peek(1) == '-':
                comment = ''
                while self.peek() and self.peek() != '\n':
                    comment += self.advance()
                self.tokens.append(Token(TokenType.COMMENT, comment, line, column))
            elif char in '"\'':
                string_val = self.read_string(char)
                self.tokens.append(Token(TokenType.STRING, string_val, line, column))
            elif char.isdigit():
                number = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, number, line, column))
            elif char.isalpha() or char == '_':
                ident = self.read_identifier()
                token_type = TokenType.KEYWORD if ident in self.KEYWORDS else TokenType.IDENTIFIER
                self.tokens.append(Token(token_type, ident, line, column))
            elif char == '.' and self.peek(1) == '.' and self.peek(2) == '.':
                self.advance(); self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '...', line, column))
            elif char == '.' and self.peek(1) == '.':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '..', line, column))
            elif char == '<' and self.peek(1) == '<':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '<<', line, column))
            elif char == '>' and self.peek(1) == '>':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '>>', line, column))
            elif char == '=' and self.peek(1) == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '==', line, column))
            elif char == '~' and self.peek(1) == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '~=', line, column))
            elif char == '<' and self.peek(1) == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '<=', line, column))
            elif char == '>' and self.peek(1) == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, '>=', line, column))
            elif char in self.OPERATORS:
                self.advance()
                self.tokens.append(Token(TokenType.OPERATOR, char, line, column))
            else:
                self.advance()
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


def handler(request):
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
        }
    
    try:
        body = json.loads(request.body) if isinstance(request.body, str) else request.json
        code = body.get('code', '')
        
        if not code:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No code provided'}),
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            }
        
        lexer = LuaLexer(code)
        tokens = lexer.tokenize()
        
        identifiers = []
        functions = 0
        strings = 0
        
        for token in tokens:
            if token.type == TokenType.IDENTIFIER:
                identifiers.append(token.value)
            elif token.type == TokenType.KEYWORD and token.value == 'function':
                functions += 1
            elif token.type == TokenType.STRING:
                strings += 1
        
        stats = {
            'total_tokens': len(tokens),
            'total_identifiers': len(identifiers),
            'unique_identifiers': len(set(identifiers)),
            'total_functions': functions,
            'total_strings': strings,
            'total_lines': tokens[-1].line if tokens else 0,
            'size_original': len(code),
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(stats),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        }
