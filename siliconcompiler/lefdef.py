# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from ply import lex

from pathlib import Path

#Documentation for ply
#https://ply.readthedocs.io/en/latest/ply.html#the-tokens-list

data = Path('/home/aolofsson/12LPPLUS_10M_3Mx_4Cx_2Kx_1Gx_LB_84cpp_tech.lef').read_text()

########################
# LEX Lexer
########################


#LEF Keywords
keywords = ["VERSION",
            "BUSBITCHARS",
            "DIVIDERCHAR",
            "UNITS",
            "MANUFACTURINGGRID",
            "USEMINSPACING",
            "CLEARANCEMEASURE",
            "PROPERTYDEFINITIONS",
            "LAYER",
            "MAXVIASTACK",
            "VIA",
            "VIARULE",
            "NONDEFAULTRULE",
            "SITE",
            "BEGINEXT",
            "MACRO",
            "PIN",
            "OBS",
            "SIZE",
            "END"]


#Tokens (nested keywords and delimeters)
tokens = keywords.copy()
tokens.extend(["SEMICOLON",
               "DIVIDER",
               "LEFTBRACKET",
               "RIGHTBRACKET",
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
t_MANUFACTURINGGRID   = r'MANUFACTURINGGRID'
t_USEMINSPACING       = r'USEMINSPACING'
t_CLEARANCEMEASURE    = r'CLEARANCEMEASURE'
t_PROPERTYDEFINITIONS = r'PROPERTYDEFINITIONS'
t_LAYER               = r'LAYER'
t_MAXVIASTACK         = r'MAXVIASTACK'
t_VIA                 = r'VIA'
t_VIARULE             = r'VIARULE'
t_NONDEFAULTRULE      = r'NONDEFAULTRULE'
t_SITE                = r'SITE'
t_BEGINEXT            = r'BEGINEXT'
t_SIZE                = r'SIZE'
t_PIN                 = r'PIN'
t_OBS                 = r'OBS'
t_MACRO               = r'MACRO'
t_END                 = r'END'
t_DIVIDER             = r'\/'
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
# LEF Parser
########################
#TODO: fix properly with yacc?

#1. Look for keywords, put parser in a state (left to right)
#2. Anything between quotes gets put into a list (open/close)"
#3. List is further split by ";"
#4. Then based on stage, put the list/scalar into keys

string  = False
lef     = {}
values  = []
keyword = None
while True:
    tok = lexer.token()
    if not tok:
        break
    #Sometimes there are ";" characters inside strings!!!!
    # ex: PROPERTY LEF58_TYPE "TYPE DIFFUSION ;" ;      
    if(tok.value == "\""):
        string = not string
        #values.append(tok.value)
    #lef statements terminate on ";"
    elif((not string) & (tok.value == ";")):
        # short nested layer statements
        # ex: LAYER LEF58_CUTCLASS STRING ;
        if((values[0] =="LAYER") | (values[0] =="PIN")):
            group     = values[0]
            attr      = values[0]
            start     = 1
        # short non nested statements
        # ex: BUSBITCHARS "[]" ; 
        elif((values[0] in keywords) & (len(values) < 4)):
            keyword   = values[0]
            attr      = values[0]
            group     = values[0]
            start     = 1
        # because there was a need for a useless syntactic END keyword??
        # ex: END NW LAYER PWELL TYPE MASTERSLICE ;        
        elif(values[0] =="END"):
            keyword  = values[2]
            #short statement after end
            if(len(values) < 5):
                group = keyword
                attr  = keyword
                start = 3
            else:
                group = values[3]
                attr  = values[4]
                start = 5
        # first entry of propertydef
        # ex: PROPERTYDEFINITIONS LAYER LEF58_CUTCLASS STRING ;
        elif((values[1] =="LAYER") | (values[1] =="PIN")):
            keyword = values[0]
            group   = values[0]
            attr    = values[1]
            start   = 2
        # all other nested statements
        else:
            attr   = values[0]
            start  = 1
        lef[keyword]              ={}
        lef[keyword][group]       ={}
        lef[keyword][group][attr] = values[slice(start,len(values))]
        #print("VAL", values)
        print("                            STATEMENT", " key=", keyword, " group=", group, " attr=", attr, " lef=",lef[keyword][group][attr], sep='')
        values.clear()
    else:
        values.append(tok.value)        
   

#Printing out struct
for key in lef.keys():
    print("KV PAIR:", key, lef[key])
