# Token data classes for parsing Verilog

# The lexer/tokenizer emits a sequence of Token subclasses

from .structures import DataClass


class Token(DataClass):
    pass


class DirectiveToken(Token):
    _attributes = ["directive", "line"]


class MacroToken(Token):
    _attributes = ["name"]


class KeywordToken(Token):
    _attributes = ["keyword"]


class IdentifierToken(Token):
    _attributes = ["name"]


class NumericToken(Token):
    _attributes = ["value", "signed", "size"]


class OperatorToken(Token):
    _attributes = ["operator"]


class SemicolonToken(Token):
    _attributes = []


class EndToken(Token):
    _attributes = []
