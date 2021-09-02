# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from ply import lex

#################################################################
# LEF Parser
#################################################################
#The LEF parser uses the awesome lec tokenizer PLYL
#https://ply.readthedocs.io/en/latest/ply.html#the-tokens-list

class ParseError(Exception):
    pass

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
                   "ID",
                   "FLOAT"])
        
    # Reular exprssions ruls with some action code
    t_DIVIDER             = r'\/'
    t_SEMICOLON           = r'\;'
    t_QUOTE               = r'\"'

    def t_FLOAT(self, t):
        r'[\d\.\-]+'
        t.value = float(t.value)
        return t

    # TODO: according to ref, identifiers can include basically anything besides
    # whitespace -- make this less strict and test it
    def t_ID(self, t):
        r'[^#;\s]+'
        if t.value in self.keywords:
            t.type = t.value
        return t

    def __init__ (self):
        self.lexer = lex.lex(module=self)
    
    # Keep track of newlines
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # Ignore white space and comments
    t_ignore_COMMENT      = r'\#.*'
    t_ignore              = ' \t'
        
    def t_error(self,t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def lib_parse(self, data):
        self.lexer.input(data)
        lib = {'sites': [], 'macros': {}}

        while True:
            tok = self.lexer.token()
            if not tok: return None

            # TODO: version technically might not be float, since
            # it can be of form "x.x.x"
            if tok.type in ('VERSION', 'MANUFACTURINGGRID'):
                # simple num statement
                num = self.lexer.token()
                semi = self.lexer.token()
                if num.type != 'FLOAT' or semi.type != 'SEMICOLON':
                    raise ParseError('Statement expects number followed by semicolon')
                lib[tok.value.lower()] = float(num.value)
            elif tok.type == 'UNITS':
                lib['units'] = self.parse_units()
            elif tok.type == 'SITE':
                lib['sites'].append(self.parse_site())
            elif tok.type == 'MACRO':
                name, macro = self.parse_macro()
                lib['macros'][name] = macro
            elif tok.type == 'END':
                tok = self.lexer.token()
                break

        return lib

    def parse_version(self):
        num = self.lexer.token()
        semi = self.lexer.token()
        if num.type != 'FLOAT' or semi.type != 'SEMICOLON':
            raise ParseError('Version statement expects number followed by semicolon')

        return {"version": float(num.value)}

    def parse_units(self):
        units = []
        while True:
            unit_type = self.lexer.token()
            if unit_type is None or unit_type.type == 'END':
                break

            unit_unit = self.lexer.token()
            convert_factor = self.lexer.token()
            semi = self.lexer.token()

            # TODO: check unit type/unit unit are valid
            if unit_type.type != 'ID' or convert_factor.type != 'FLOAT' or semi.type != 'SEMICOLON':
                raise ParseError('Parse units')

            units.append({unit_type.value.lower(): float(convert_factor.value)})

        # eat 'UNITS' after 'END'
        # TODO: check that this is UNITS if we want to be strict
        tok = self.lexer.token()

        return units

    def parse_site(self):
        # TODO: parse site instead of just ignoring contents
        name = self.lexer.token()
        if name.type != 'ID':
            raise ParseError("Parse site")

        tok = self.lexer.token()
        while tok.type != 'END':
            self.chomp_till_semi()
            tok = self.lexer.token()
        name2 = self.lexer.token()
        # TODO: check that names equal

        return {'name': name.value}

    def parse_macro(self):
        name = self.lexer.token()
        if name.type != 'ID':
            raise ParseError("Parse macro")

        macro = {}

        tok = self.lexer.token()
        while tok.type != 'END':
            if tok.type == 'SIZE':
                # TODO: refactor into own function w/ error check
                x = self.lexer.token()
                by = self.lexer.token()
                y = self.lexer.token()
                semi = self.lexer.token()
                macro['size'] = float(x.value), float(y.value)
            elif tok.type == 'PIN':
                self.parse_pin()
            elif tok.type == 'OBS':
                self.chomp_till_end()
            else:
                # every other sub-statement is terminated by the next semicolon
                self.chomp_till_semi()

            tok = self.lexer.token()
        name2 = self.lexer.token()

        return name.value, macro

    def parse_pin(self):
        name = self.lexer.token()
        tok = self.lexer.token()
        while tok.type != 'END':
            if tok.type == 'ID' and tok.value == 'PORT':
                self.chomp_till_end()
            else:
                self.chomp_till_semi()
            tok = self.lexer.token()
        name2 = self.lexer.token()

    def chomp_till_end(self):
        tok = self.lexer.token()
        while tok.type != 'END':
            tok = self.lexer.token()

    def chomp_till_semi(self):
        tok = self.lexer.token()
        while tok.type != 'SEMICOLON':
            tok = self.lexer.token()

    def parse_busbitchars(self):
        chars = self.lexer.token()
        semi = self.lexer.token()
        if num.type != 'FLOAT' or semi.type != 'SEMICOLON':
            raise ParseError('Version statement expects number followed by semicolon')

        return {"version": float(num.value)}

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

if(False):
    from pathlib import Path
    
    lefdata = Path('../third_party/pdklib/virtual/nangate45/r1p0/pnr/nangate45.tech.lef').read_text()
    mylef = Lef()
    lef = mylef.parse(lefdata)
    
    #Printing out struct
    for key in lef.keys():
        for group in lef[key].keys():
            for attr in lef[key][group].keys(): 
                print(key, group, attr,lef[key][group][attr])
                
