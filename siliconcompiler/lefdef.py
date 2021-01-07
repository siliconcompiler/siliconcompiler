# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from ply import lex

#################################################################
# LEF Parser
#################################################################
#The LEF parser uses the awesome lec tokenizer PLYL
#https://ply.readthedocs.io/en/latest/ply.html#the-tokens-list

class Lef:

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

    def __init__ (self):
        self.lexer = lex.lex(module=self)
    
    # Keep track of newlines
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Ignore white space and comments
    t_ignore_COMMENT      = r'\#.*'
    t_ignore              = ' \t'           
        
    #def t_error(self,t):
    #    print("Illegal character '%s'" % t.value[0])
    #    t.lexer.skip(1)
        
    def parse(self,data):
        string        = False
        lef           = {}
        values        = []
        keyword       = None
        routing_layer = 1
        self.lexer.input(data)        
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            #Sometimes there are ";" characters inside strings!!!!
            # ex: PROPERTY LEF58_TYPE "TYPE DIFFUSION ;" ;
            #print(tok)
            if(tok.value == "\""):
                string = not string
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
                elif((values[0] in self.keywords) & (len(values) < 4)):
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
                
                #Better way to init dict key?
                if(keyword not in lef):
                    lef[keyword] ={}
                if(group not in lef[keyword]):
                    lef[keyword][group] = {}                       

                #stuffing properties in dictionary
                lef[keyword][group][attr] = values[slice(start,len(values))]
                #keeping track of routing layers, where lef order matters?!!
                if((keyword=="LAYER") & (attr=="TYPE") & (lef[keyword][group][attr][0]=="ROUTING")):
                    lef[keyword][group]["ROUTING_LAYER"] = routing_layer
                    routing_layer = routing_layer + 1
                #";" terminates a statement in def, so clear the list
                #print("STATEMENT", " key=", keyword, " group=", group, " attr=", attr, " lef=",lef[keyword][group][attr], sep='')
                values.clear()
            else:
                #keep stuffing list until you get to a ";" 
                values.append(tok.value)

        return(lef)
   
####################################################
#FOOFOO TESTING
####################################################
from pathlib import Path

lefdata = Path('../third_party/pdklib/virtual/nangate45/r1p0/pnr/nangate45.tech.lef').read_text()
mylef = Lef()
lef = mylef.parse(lefdata)

#Printing out struct
for key in lef.keys():
    for group in lef[key].keys():
        for attr in lef[key][group].keys(): 
           print(key, group, attr,lef[key][group][attr])
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



