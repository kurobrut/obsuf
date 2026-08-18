import json
from enum import Enum
from http.server import BaseHTTPRequestHandler
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
        "and", "break", "do", "else", "elseif", "end", "false", "for",
        "function", "goto", "if", "in", "local", "nil", "not", "or",
        "repeat", "return", "then", "true", "until", "while"
    }

    OPERATORS = {
        "+", "-", "*", "/", "%", "^", "==", "~=", "!=", "<=", ">=",
        "<", ">", "=", "(", ")", "{", "}", "[", "]", ";", ":", ",",
        ".", "..", "...", "#", "&", "|", "~", "<<", ">>"
    }

    def __init__(self, code: str):
        self.code = code
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def peek(self, offset=0):
        pos = self.pos + offset
        if pos < len(self.code):
            return self.code[pos]
        return ""

    def advance(self):
        if self.pos >= len(self.code):
            return ""

        char = self.code[self.pos]
        self.pos += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def read_string(self, quote):
        result = ""

        self.advance()

        while self.pos < len(self.code):
            char = self.peek()

            if char == quote:
                self.advance()
                break

            if char == "\\":
                self.advance()
                next_char = self.advance()

                escape_map = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "\\": "\\",
                    '"': '"',
                    "'": "'",
                }

                result += escape_map.get(next_char, next_char)
            else:
                result += self.advance()

        return result

    def read_number(self):
        result = ""

        while self.peek().isdigit():
            result += self.advance()

        if self.peek() == "." and self.peek(1) != ".":
            result += self.advance()

            while self.peek().isdigit():
                result += self.advance()

        return result

    def read_identifier(self):
        result = ""

        while self.peek().isalnum() or self.peek() == "_":
            result += self.advance()

        return result

    def tokenize(self):
        while self.pos < len(self.code):
            line = self.line
            column = self.column
            char = self.peek()

            if char in " \t\n\r":
                value = ""

                while self.peek() in " \t\n\r":
                    value += self.advance()

                self.tokens.append(
                    Token(TokenType.WHITESPACE, value, line, column)
                )

            elif char == "-" and self.peek(1) == "-":
                value = ""

                while self.peek() and self.peek() != "\n":
                    value += self.advance()

                self.tokens.append(
                    Token(TokenType.COMMENT, value, line, column)
                )

            elif char in "\"'":
                value = self.read_string(char)

                self.tokens.append(
                    Token(TokenType.STRING, value, line, column)
                )

            elif char.isdigit():
                value = self.read_number()

                self.tokens.append(
                    Token(TokenType.NUMBER, value, line, column)
                )

            elif char.isalpha() or char == "_":
                value = self.read_identifier()

                token_type = (
                    TokenType.KEYWORD
                    if value in self.KEYWORDS
                    else TokenType.IDENTIFIER
                )

                self.tokens.append(
                    Token(token_type, value, line, column)
                )

            elif (
                char == "."
                and self.peek(1) == "."
                and self.peek(2) == "."
            ):
                self.advance()
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "...", line, column)
                )

            elif char == "." and self.peek(1) == ".":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "..", line, column)
                )

            elif char == "<" and self.peek(1) == "<":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "<<", line, column)
                )

            elif char == ">" and self.peek(1) == ">":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, ">>", line, column)
                )

            elif char == "=" and self.peek(1) == "=":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "==", line, column)
                )

            elif char == "~" and self.peek(1) == "=":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "~=", line, column)
                )

            elif char == "<" and self.peek(1) == "=":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, "<=", line, column)
                )

            elif char == ">" and self.peek(1) == "=":
                self.advance()
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, ">=", line, column)
                )

            elif char in self.OPERATORS:
                self.advance()

                self.tokens.append(
                    Token(TokenType.OPERATOR, char, line, column)
                )

            else:
                self.advance()

        self.tokens.append(
            Token(TokenType.EOF, "", self.line, self.column)
        )

        return self.tokens


def analyze(code):
    lexer = LuaLexer(code)
    tokens = lexer.tokenize()

    identifiers = []
    functions = 0
    strings = 0

    for token in tokens:
        if token.type == TokenType.IDENTIFIER:
            identifiers.append(token.value)

        elif (
            token.type == TokenType.KEYWORD
            and token.value == "function"
        ):
            functions += 1

        elif token.type == TokenType.STRING:
            strings += 1

    return {
        "total_tokens": len(tokens),
        "total_identifiers": len(identifiers),
        "unique_identifiers": len(set(identifiers)),
        "total_functions": functions,
        "total_strings": strings,
        "total_lines": tokens[-1].line if tokens else 0,
        "size_original": len(code),
    }


def send_json(handler, status, data):
    body = json.dumps(data).encode("utf-8")

    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header(
        "Access-Control-Allow-Methods",
        "POST, OPTIONS"
    )
    handler.send_header(
        "Access-Control-Allow-Headers",
        "Content-Type"
    )
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()

    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        send_json(self, 200, {"ok": True})

    def do_POST(self):
        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(content_length)

            if not raw_body:
                send_json(
                    self,
                    400,
                    {"error": "No request body provided"}
                )
                return

            body = json.loads(raw_body.decode("utf-8"))

            code = body.get("code", "")

            if not isinstance(code, str) or not code.strip():
                send_json(
                    self,
                    400,
                    {"error": "No code provided"}
                )
                return

            stats = analyze(code)

            send_json(
                self,
                200,
                stats
            )

        except json.JSONDecodeError:
            send_json(
                self,
                400,
                {"error": "Invalid JSON"}
            )

        except Exception as exc:
            send_json(
                self,
                500,
                {"error": str(exc)}
            )

    def do_GET(self):
        send_json(
            self,
            405,
            {"error": "Use POST /api/analyze"}
        )
        return
