# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from ply import lex

#################################################################
# DEF Parser
#################################################################
#The DEF parser uses the awesome lec tokenizer PLYL
#https://ply.readthedocs.io/en/latest/ply.html#the-tokens-list

class Def:

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


    #Create lexer once
    def __init__ (self):
        self.lexer = lex.lex(module=self)
        
    # Keep track of newlines
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    #def t_error(self,t):
    #    print("Illegal character '%s'" % t.value[0])
    #    t.lexer.skip(1)

    def parse(self,data):
        string        = False
        lef           = {}
        values        = []
        keyword       = None

        #Insert data to lexer
        self.lexer.input(data)  

        #Parse each token
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            if(tok.value == "\""):
                string = not string
            elif((not string) & (tok.value == ";")):
                print(values)
                values.clear()
            else:
                values.append(tok.value)


####################################################
#FOOFOO TESTING
####################################################
from pathlib import Path

defdata = Path('test/complete.5.8.def').read_text()
mydef = Def()
mydef.parse(defdata)



