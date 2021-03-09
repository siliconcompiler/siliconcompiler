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

###################
# Write DEF
###################

def write_def(lefdef, filename):
    '''
    Write DEF File
    '''
    logging.info('Write DEF %s', filename)
    EOT=";"
    
    with open(filename, 'w') as f:
        print("#############################################", file=f)
        print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
        print("#############################################", file=f)

        #setup
        print("VERSION ",lefdef["version"], EOT, file=f)
        print("DIVIDERCHAR ",lefdef["dividerchar"], EOT, file=f)
        print("BUSBITCHARS ",lefdef["busbitchars"], EOT, file=f)
        print("DESIGN ",lefdef["design"], EOT, file=f)
        print("TECHNOLOGY ",lefdef["technology"], EOT, file=f)
        print("UNITS DISTANCE MICRONS ",lefdef["units"], EOT, file=f)
        print("\n", file=f)

        #properties
        for key,val in lefdef["property"].items():
            print(key, val, EOT, file=f)

        #diearea
        print("DIEAREA", file=f)
        for val in lefdef["diearea"]:
            print(" ( "+val+ " ) ", file=f)
        print(EOT, file=f)

        #row
        for k in lefdef["row"].keys():
            print("ROW ",
                  k, " ",
                  lefdef["row"][k]["site"], " ",
                  lefdef["row"][k]["x"], " ",
                  lefdef["row"][k]["y"], " ",
                  lefdef["row"][k]["orientation"], " ",
                  lefdef["row"][k]["numx"], " ",
                  lefdef["row"][k]["numy"], " ",
                  lefdef["row"][k]["stepx"], " ",
                  lefdef["row"][k]["stepy"], " ",
                  EOT,
                  file=f)

        #track
        for k in lefdef["track"].keys():
            print("TRACKS ",
                  k, " ",
                  lefdef["track"][k]["layer"], " ",
                  lefdef["track"][k]["direction"], " ",
                  lefdef["track"][k]["start"], " ",
                  lefdef["track"][k]["step"], " ",
                  lefdef["track"][k]["total"], " ",
                  EOT,
                  file=f)

        #via
        print("VIAS ", len(lefdef["via"]), EOT, file=f)
        for k in lefdef["via"].keys():
            print("VIA ",
                  k, " ",
                  #TODO
                  EOT,
                  file=f)
        
        #non default routing
        print("NONDEFAULTRULES ", len(lefdef["via"]), EOT, file=f)
        for k in lefdef["ndr"].keys():
              print("NONDEFAULTRULESVIA ",
                    k, " ",
                    #TODO
                    EOT,
                    file=f)  


        #components
        print("COMPONENTS ", len(lefdef["component"]), EOT, file=f)
        for inst in lefdef["component"].keys():
            print("- ",
                  inst, " ",
                  lefdef["component"][inst]["cell"], " + ",
                  lefdef["component"][inst]["status"], " (",
                  lefdef["component"][k]["x"], " ",
                  lefdef["component"][k]["y"], " ) ",
                  lefdef["component"][k]["orientation"], " ",
                  EOT,
                  file=f)
        print("END COMPONENTS", file=f)

        #pins
        print("PINS ", len(lefdef["pin"]), EOT, file=f)
        for pin in lefdef["pin"].keys():
            print("- ",
                  pin, 
                  " + NET ", lefdef["pin"][pin]["net"],
                  " + DIRECTION ", lefdef["pin"][pin]["direction"],
                  " + USE ", lefdef["pin"][pin]["use"],
                  file=f)
            for port in lefdef["pin"][pin].keys():
              print("PORT ",
                    "+ LAYER ", lefdef["pin"][pin][port]['layer'],
                    " ( ", lefdef["pin"][pin][port]['box'][0],
                    " ) ", lefdef["pin"][pin][port]['box'][1],
                    " ( ", lefdef["pin"][pin][port]['box'][2],
                    " ) ", lefdef["pin"][pin][port]['box'][3],
                    " + ", lefdef["pin"][pin][port]['status'],
                    " ( ", lefdef["pin"][pin][port]['point'][0],
                    "   ", lefdef["pin"][pin][port]['point'][1],
                    " ) ", lefdef["pin"][pin][port]['oreintation'],
                    EOT,
                    file=f)
        print("END PINS", file=f)


        #blockages
        #TODO

        #SPECIALNETS
        #TODO

        #11. NETS
        print("NETS ", len(lefdef["nets"]), EOT, file=f)
        for net in lefdef["net"].keys():
            print("- ",
                  net,
                  file=f)
            for conn in lefdef["nets"][net]['connnection']:   
              print(" ( ", lefdef["nets"][net]['connnection']['inst'],
                    " ", lefdef["nets"][net]['connnection']['pin'],
                    " ) ",
                    file=f)
            print("USE ",
                  lefdef["nets"][net]['use'],
                  EOT, file=f)


        print("END NETS", file=f)
        print("END DESIGN", file=f)
                  
###################
# Read DEF
###################
def read_def(lefdef, filename):
    mydef = Def()
    mydef.parse(defdata)
    
    return lefdef

