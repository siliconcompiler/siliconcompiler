# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from ply import lex

from pathlib import Path

#Documentation for ply
#https://ply.readthedocs.io/en/latest/ply.html#the-tokens-list

data = Path('/home/aolofsson/work/openroad/OpenDB/src/def/TEST/complete.5.8.def').read_text()

########################
# LEX Lexer
########################


#LEF Keywords
keywords = ["VERSION",
            "BUSBITCHARS",
            "DIVIDERCHAR",
            "DESIGN",
            "TECHNOLOGY",
            "UNITS",
            "HISTORY",
            "PROPERTYDEFINITIONS",
            "DIEAREA",
            "ROWS",
            "TRACKS",
            "GCELLGRID",
            "VIAS",
            "STYLES",
            "NONDEFAULTRULES",
            "REGIONS",
            "COMPONENTS",
            "PINS",
            "PINPROPERTIES",
            "BLOCKAGES",
            "SLOTS",
            "FILLS",
            "SPECIALNETS",
            "NETS",
            "SCANCHAINS",
            "GROUPS",
            "BEGINEXT",
            "END"]


#Tokens (nested keywords and delimeters)
tokens = keywords.copy()
tokens.extend(["SEMICOLON",
               "PIPE",
               "DIVIDER",
               "LEFTPARENS",
               "RIGHTPARENS",
               "LEFTBRACKET",
               "RIGHTBRACKET",
               "LT",
               "GT",
               "PLUS",
               "MINUS",
               "MULT",
               "BACKSLASH",
               "QUOTE",
               "STRING",
               "FLOAT"])


# Ignore white space and comments
t_ignore_COMMENT      = r'\#.*'
t_ignore              = ' \t'           

# Reular exprssions ruls with some action code
t_VERSION             = r'VERSION'
t_BUSBITCHARS         = r'\[\]'
t_DIVIDERCHAR         = r'DIVIDERCHAR'
t_UNITS               = r'UNITS'
t_PROPERTYDEFINITIONS = r'PROPERTYDEFINITIONS'
t_NONDEFAULTRULES     = r'NONDEFAULTRULES'
t_BEGINEXT            = r'BEGINEXT'
t_PINS                = r'PINS'
t_END                 = r'END'
t_LEFTBRACKET         = r'\['
t_RIGHTBRACKET        = r'\]'
t_LEFTPARENS          = r'\('
t_RIGHTPARENS         = r'\)'
t_LT                  = r'\<'
t_GT                  = r'\>'
t_MINUS               = r'\-'
t_PLUS                = r'\+'
t_MULT                = r'\*'
t_DIVIDER             = r'\/'
t_BACKSLASH           = r'\\'
t_SEMICOLON           = r'\;'
t_QUOTE               = r'\"'
t_STRING              = r'\w+'
t_FLOAT               = r'[\d\.\-]+'

# Keep track of newlines
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()
lexer.input(data)

########################
# DEF Parser
########################
string        = False
lef           = {}
values        = []
keyword       = None
routing_layer = 1
while True:
    tok = lexer.token()
    if not tok:
        break
    if(tok.value == "\""):
        string = not string
    elif((not string) & (tok.value == ";")):
        print(values)
        values.clear()
    else:
        values.append(tok.value)    
        
