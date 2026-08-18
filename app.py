#!/usr/bin/env python3
"""Flask backend for Lua Obfuscator Web App"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
import io
import re
import base64
import random
import string
from typing import Dict, List, Tuple
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
        if self.peek() in 'eE':
            result += self.advance()
            if self.peek() in '+-':
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


class LuaObfuscator:
    def __init__(self, code: str):
        self.code = code
        self.lexer = LuaLexer(code)
        self.tokens = self.lexer.tokenize()
    
    def minify(self) -> str:
        result = []
        prev_token = None
        
        for token in self.tokens:
            if token.type in (TokenType.WHITESPACE, TokenType.COMMENT):
                continue
            
            if prev_token and prev_token.type != TokenType.OPERATOR and token.type != TokenType.OPERATOR:
                if prev_token.type != TokenType.PUNCTUATION and token.type != TokenType.PUNCTUATION:
                    if prev_token.value not in ('(', '[', '{') and token.value not in (')', ']', '}', '.', ':', ',', ';'):
                        result.append(' ')
            
            result.append(token.value)
            prev_token = token
        
        return ''.join(result)
    
    def beautify(self, indent_size: int = 2) -> str:
        result = []
        indent_level = 0
        indent_char = ' ' * indent_size
        current_line = []
        
        keywords_increase = {'then', 'do', 'repeat'}
        keywords_decrease = {'end', 'until', 'else', 'elseif'}
        
        for token in self.tokens:
            if token.type == TokenType.COMMENT:
                current_line.append(token.value)
                continue
            
            if token.type == TokenType.WHITESPACE:
                continue
            
            if token.type == TokenType.KEYWORD:
                if token.value in keywords_decrease:
                    indent_level = max(0, indent_level - 1)
                
                if current_line:
                    result.append(indent_char * indent_level + ''.join(current_line).strip())
                    current_line = []
                
                current_line.append(token.value)
                
                if token.value in keywords_increase:
                    indent_level += 1
                    result.append(indent_char * indent_level + ''.join(current_line).strip())
                    current_line = []
            
            elif token.value == ';':
                current_line.append(token.value)
                if current_line:
                    result.append(indent_char * indent_level + ''.join(current_line).strip())
                    current_line = []
            
            else:
                current_line.append(token.value)
        
        if current_line:
            result.append(indent_char * indent_level + ''.join(current_line).strip())
        
        return '\n'.join(result)
    
    def obfuscate(self, obfuscate_strings: bool = False) -> str:
        result = []
        identifier_map = {}
        
        for token in self.tokens:
            if token.type == TokenType.IDENTIFIER:
                if token.value not in identifier_map:
                    identifier_map[token.value] = self._generate_obfuscated_name()
                result.append(identifier_map[token.value])
            elif token.type == TokenType.STRING and obfuscate_strings:
                encoded = base64.b64encode(token.value.encode()).decode()
                result.append(f'(__obf_decode("{encoded}"))')
            else:
                result.append(token.value)
        
        return ''.join(result)
    
    def _generate_obfuscated_name(self, length: int = 8) -> str:
        chars = 'ilLoO1_'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def shorten_variable_names(self) -> str:
        result = []
        identifier_map = {}
        var_counter = 0
        
        def get_short_name(counter):
            if counter < 26:
                return chr(97 + counter)
            else:
                return 'a' + chr(97 + (counter - 26) % 26) + str((counter - 26) // 26)
        
        for token in self.tokens:
            if token.type == TokenType.IDENTIFIER:
                if token.value not in identifier_map:
                    identifier_map[token.value] = get_short_name(var_counter)
                    var_counter += 1
                result.append(identifier_map[token.value])
            else:
                result.append(token.value)
        
        return ''.join(result)
    
    def remove_comments(self) -> str:
        return ''.join(token.value for token in self.tokens 
                      if token.type != TokenType.COMMENT)
    
    def encrypt_strings(self, key: str = "default") -> str:
        result = []
        key_bytes = key.encode()
        
        for token in self.tokens:
            if token.type == TokenType.STRING:
                encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] 
                                 for i, b in enumerate(token.value.encode()))
                hex_str = encrypted.hex()
                result.append(f'(__decrypt_str("{hex_str}", "{key}"))')
            else:
                result.append(token.value)
        
        return ''.join(result)
    
    def analyze_code(self) -> Dict:
        identifiers = []
        functions = 0
        strings = 0
        numbers = 0
        comments = 0
        keywords = []
        
        for token in self.tokens:
            if token.type == TokenType.IDENTIFIER:
                identifiers.append(token.value)
            elif token.type == TokenType.KEYWORD:
                if token.value == 'function':
                    functions += 1
                keywords.append(token.value)
            elif token.type == TokenType.STRING:
                strings += 1
            elif token.type == TokenType.NUMBER:
                numbers += 1
            elif token.type == TokenType.COMMENT:
                comments += 1
        
        return {
            'total_tokens': len(self.tokens),
            'total_identifiers': len(identifiers),
            'unique_identifiers': len(set(identifiers)),
            'total_functions': functions,
            'total_strings': strings,
            'total_numbers': numbers,
            'total_comments': comments,
            'total_lines': self.tokens[-1].line if self.tokens else 0,
            'size_original': len(self.code),
        }


app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process():
    try:
        data = request.json
        code = data.get('code', '')
        operations = data.get('operations', {})
        encryption_key = data.get('encryption_key', 'default')
        
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        obf = LuaObfuscator(code)
        result = code
        messages = []
        
        if operations.get('remove_comments'):
            result = LuaObfuscator(result).remove_comments()
            messages.append('✓ Comments removed')
        
        if operations.get('minify'):
            result = LuaObfuscator(result).minify()
            messages.append('✓ Minified')
        
        if operations.get('beautify'):
            result = LuaObfuscator(result).beautify()
            messages.append('✓ Beautified')
        
        if operations.get('shorten_names'):
            result = LuaObfuscator(result).shorten_variable_names()
            messages.append('✓ Variable names shortened')
        
        if operations.get('obfuscate'):
            result = LuaObfuscator(result).obfuscate()
            messages.append('✓ Variables obfuscated')
        
        if operations.get('encrypt_strings'):
            result = LuaObfuscator(result).encrypt_strings(encryption_key)
            messages.append('✓ Strings encrypted')
        
        stats = obf.analyze_code()
        final_stats = LuaObfuscator(result).analyze_code()
        
        return jsonify({
            'result': result,
            'messages': messages,
            'stats_before': stats,
            'stats_after': final_stats,
            'size_reduction': f"{((len(code) - len(result)) / len(code) * 100):.1f}%" if code else "0%"
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        code = data.get('code', '')
        
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        obf = LuaObfuscator(code)
        stats = obf.analyze_code()
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    try:
        data = request.json
        code = data.get('code', '')
        filename = data.get('filename', 'obfuscated.lua')
        
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        return send_file(
            io.BytesIO(code.encode()),
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
