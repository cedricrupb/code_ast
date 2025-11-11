"""
Lean wrapper around the tree-sitter Python API

Main features:
- Parses arbitrary code as string and bytes
- Autoloading / Compiling of AST parsers

"""
import os
from tree_sitter import Language, Parser

import importlib
from importlib.metadata import version

import logging as logger

# For autoloading
import requests
from git import Repo


try:
    from tree_sitter_languages import get_language, get_parser
except ImportError:
    get_language, get_parser = None, None


# Automatic loading of Tree-Sitter parsers --------------------------------

def load_language(lang):
    """
    Loads a language specification object necessary for tree-sitter.

    Language specifications are loaded from remote or a local cache.
    If language specification is not contained in cache, the function
    clones the respective git project and then builds the language specification
    via tree-sitter.
    We employ the same language identifier as tree-sitter and
    lang is translated to a remote repository 
    (https://github.com/tree-sitter/tree-sitter-[lang]).

    Note: Since tree_sitter v0.22.0, language specifications are loaded as 
    Python packages. Therefore, autoloading won't work. For these, you
    have to install the right python package via PIP 
    (see: https://github.com/tree-sitter/py-tree-sitter).

    Parameters
    ----------
    lang : [python, java, javascript, ...]
        language identifier specific to tree-sitter.
        As soon as there is a repository with the same language identifier
        the language is supported by this function.

    Returns
    -------
    Language
        language specification object

    """
    if version("tree_sitter") < "0.22.0":
        return _pre22_load_language(lang)
    return _load_language(lang)


def _load_language(lang):
    try:
        tree_sitter_pkg = importlib.import_module(f"tree_sitter_{lang}")
        return Language(tree_sitter_pkg.language())
    except ImportError:
        raise ImportError(f"'tree_sitter_{lang}' not found. Please install the package via `pip install tree-sitter-{lang}`.")


def _pre22_load_language(lang):

    if get_language is not None:
        try:
            return get_language(lang)
        except Exception as e:
            logger.exception("No pre-compiled language for %s exists. Start compiling." % lang)

    cache_path = _path_to_local()
    
    compiled_lang_path = os.path.join(cache_path, "%s-lang.so" % lang)
    source_lang_path   = os.path.join(cache_path, "tree-sitter-%s" % lang)

    if os.path.isfile(compiled_lang_path):
        return Language(compiled_lang_path, _lang_to_fnname(lang))
    
    if os.path.exists(source_lang_path) and os.path.isdir(source_lang_path):
        logger.warning("Compiling language for %s" % lang)
        _compile_lang(source_lang_path, compiled_lang_path)
        return load_language(lang)

    logger.warning("Autoloading AST parser for %s: Start download from Github." % lang)
    _clone_parse_def_from_github(lang, source_lang_path)
    return load_language(lang)


def _construct_parser(lang_id, language):
    if version("tree_sitter") < "0.22.0":
        return _pre22_construct_parser(lang_id, language)
    return Parser(language)

def _pre22_construct_parser(lang_id, language):
    if get_parser is not None:
        return get_parser(lang_id)
    else:
        parser  = Parser()
        parser.set_language(language)
        return parser



# Parser ---------------------------------------------------------------

class ASTParser:
    """
    Wrapper for tree-sitter AST parser

    Supports autocompiling the language specification needed 
    for parsing (see load_language)

    """

    def __init__(self, lang):
        """
        Autoload language specification and parser

        Parameters
        ----------
        lang : [python, java, javascript, ...]
            Language identifier specific to tree-sitter.
            Same as for load_language
        
        """

        self.lang_id = lang
        self.lang    = load_language(lang)
        self.parser  = _construct_parser(self.lang_id, self.lang)

        
    def parse_bytes(self, data):
        """
        Parses source code as bytes into AST

        Parameters
        ----------
        data : bytes
            Source code as a stream of bytes

        Returns
        -------
        tree-sitter syntax tree

        """
        return self.parser.parse(data)

    def parse(self, source_code):
        """
        Parses source code into AST

        Parameters
        ----------
        source_code : str
            Source code as a string

        Returns
        -------
        tree-sitter syntax tree
            tree-sitter object representing the syntax tree

        source_lines
            a list of code lines for reference

        """
        source_lines = source_code.splitlines()
        source_bytes = source_code.encode("utf-8")

        return self.parse_bytes(source_bytes), source_lines


# Utils ------------------------------------------------

def match_span(source_tree, source_lines):
    """
    Greps the source text represented by the given source tree from the original code

    Parameters
    ----------
    source_tree : tree-sitter node object
        Root of the AST which should be used to match the code
    
    source_lines : list[str]
        Source code as a list of source lines

    Returns
    -------
    str
        the source code that is represented by the given source tree
    
    """
    
    start_line, start_char = source_tree.start_point
    end_line,   end_char   = source_tree.end_point

    assert start_line <= end_line
    assert start_line != end_line or start_char <= end_char

    source_area     = source_lines[start_line:end_line + 1]
    
    if start_line == end_line:
        return source_area[0][start_char:end_char]
    else:
        source_area[0]  = source_area[0][start_char:]
        source_area[-1] = source_area[-1][:end_char]
        return "\n".join(source_area)


# Auto Load Languages --------------------------------------------------

PATH_TO_LOCALCACHE = None

def _path_to_local():
    global PATH_TO_LOCALCACHE
    
    if PATH_TO_LOCALCACHE is None:
        current_path = os.path.abspath(__file__)
        
        while os.path.basename(current_path) != "code_ast":
            current_path = os.path.dirname(current_path)
        
        current_path = os.path.dirname(current_path) # Top dir
        PATH_TO_LOCALCACHE = os.path.join(current_path, "build")
        
    return PATH_TO_LOCALCACHE


def _compile_lang(source_path, compiled_path):
    logger.debug("Compile language from %s" % compiled_path)

    Language.build_library(
        compiled_path,
        [
            source_path
        ]
    )


def _lang_to_fnname(lang):
    """
    dash is not supported for function names. Therefore,
    we assume that dashes represented by underscores.
    """
    return lang.replace("-", "_")


# Auto Clone from Github --------------------------------
    
def _exists_url(url):
    req = requests.get(url)
    return req.status_code == 200


def _clone_parse_def_from_github(lang, cache_path):
    
    # Start by testing whethe repository exists
    REPO_URL = "https://github.com/tree-sitter/tree-sitter-%s" % lang

    if not _exists_url(REPO_URL):
        raise ValueError("There is no parsing def for language %s available." % lang)

    logger.warning("Start cloning the parser definition from Github.")
    try:  
        Repo.clone_from(REPO_URL, cache_path)
    except Exception:
        raise ValueError("To autoload a parsing definition, git needs to be installed on the system!")








