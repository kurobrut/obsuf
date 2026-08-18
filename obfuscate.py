import json
import base64
import random
from typing import Dict, List
from enum import Enum

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


class StrongObfuscator:
    def __init__(self, code: str):
        self.code = code
        self.lexer = LuaLexer(code)
        self.tokens = self.lexer.tokenize()
        self.obf_counter = 0
    
    def obfuscate_aggressive(self) -> str:
        result = []
        
        cleaned_tokens = []
        for token in self.tokens:
            if token.type not in (TokenType.COMMENT, TokenType.WHITESPACE):
                cleaned_tokens.append(token)
        
        identifier_map = {}
        
        for i, token in enumerate(cleaned_tokens):
            if token.type == TokenType.IDENTIFIER:
                if token.value not in identifier_map:
                    obf_name = self._generate_aggressive_name()
                    identifier_map[token.value] = obf_name
                result.append(identifier_map[token.value])
            elif token.type == TokenType.STRING:
                encrypted = self._encrypt_string(token.value)
                result.append(encrypted)
            else:
                result.append(token.value)
        
        output = ''.join(result)
        
        if '__o_d_' in output:
            decoder = self._get_decoder()
            output = decoder + output
        
        return output
    
    def _generate_aggressive_name(self, length: int = 12) -> str:
        patterns = [
            'ilIIlIlllIl', 'lIllIIlIIlI', '___O_O_O_O_',
            'OlOlOlOlOlO', '1111llll1ll', 'lll11l1l1ll',
            '_IOl_OlI_lO', 'I1l1I1l1I1l', 'OO00OO00OO0',
            '11LL11LL11L', 'llLL11llLL1'
        ]
        
        if self.obf_counter < len(patterns):
            result = patterns[self.obf_counter]
        else:
            chars = 'ilLoO1_IOL'
            result = ''.join(random.choice(chars) for _ in range(length))
        
        self.obf_counter += 1
        return result
    
    def _encrypt_string(self, s: str) -> str:
        try:
            encoded = base64.b64encode(s.encode()).decode()
            return f'(__o_d_("{encoded}"))'
        except:
            return f'"{s}"'
    
    def _get_decoder(self) -> str:
        return '''local function __o_d_(x)local y=""for i=1,#x,4 do local z={string.byte(x,i,i+3)}local a=z[1]-65 if a<0 then a=a+26 elseif a<26 then else a=52-a end;z[1]=a;for j,b in ipairs(z)do if b>=48 and b<=57 then b=b-48 elseif b>=65 and b<=90 then b=b-65 elseif b>=97 and b<=122 then b=b-97+26 end;if b>=0 then y=y..string.char(b+32)end end end return y:gsub("@","")end\n'''
    
    def analyze_code(self) -> Dict:
        identifiers = []
        functions = 0
        strings = 0
        
        for token in self.tokens:
            if token.type == TokenType.IDENTIFIER:
                identifiers.append(token.value)
            elif token.type == TokenType.KEYWORD and token.value == 'function':
                functions += 1
            elif token.type == TokenType.STRING:
                strings += 1
        
        return {
            'total_tokens': len(self.tokens),
            'total_identifiers': len(identifiers),
            'unique_identifiers': len(set(identifiers)),
            'total_functions': functions,
            'total_strings': strings,
            'total_lines': self.tokens[-1].line if self.tokens else 0,
            'size_original': len(self.code),
        }


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
        
        obf = StrongObfuscator(code)
        result = obf.obfuscate_aggressive()
        
        stats_before = obf.analyze_code()
        stats_after = StrongObfuscator(result).analyze_code()
        
        size_reduction = ((len(code) - len(result)) / len(code) * 100) if code else 0
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result,
                'stats_before': stats_before,
                'stats_after': stats_after,
                'size_reduction': f"{size_reduction:.1f}%"
            }),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        }
