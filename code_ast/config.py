
class ParserConfig:
    """Helper object to translate arguments of ast to config object"""

    def __init__(self, lang, **kwargs):
        self.lang = lang
        self.syntax_error = "raise" # Options: raise, warn, ignore

        # A list of all statement node defined in the language
        self.statement_types = [
            "*_statement", "*_definition", "*_declaration"
        ]

        self.update(kwargs)

    
    def update(self, kwargs):
        for k, v in kwargs.items():

            if k not in self.__dict__:
                raise TypeError("TypeError: tokenize() got an unexpected keyword argument '%s'" % k)
        
            self.__dict__[k] = v
    
    def __repr__(self):

        elements = []
        for k, v in self.__dict__.items():
            if v is not None:
                elements.append("%s=%s" % (k, v))
        
        return "Config(%s)" % ", ".join(elements)

