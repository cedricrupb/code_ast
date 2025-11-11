# Code AST
> Fast structural analysis of any programming language in Python

Programming Language Processing (PLP) brings the capabilities of modern NLP systems to the world of programming languages. 
To achieve high performance PLP systems, existing methods often take advantage of the fully defined nature of programming languages. Especially the syntactical structure can be exploited to gain knowledge about programs.

**code.ast** provides easy access to the syntactic structure of a program. By relying on [tree-sitter](https://github.com/tree-sitter) as the back end, the parser supports fast parsing of variety of programming languages. 

The goal of code.ast is to combine the efficiency and variety of languages supported by tree-sitter with the convenience of more native parsers (like [libcst](https://github.com/Instagram/LibCST)). 

To achieve this, code.ast adds the features:
1. **Auto-loading:** Compile of source code parsers for any language supported by tree-sitter with a single keyword,
2. **Visitors:** Search the concrete syntax tree produced by tree-sitter quickly,
3. **Transformers:** Transform source code easily by transforming the syntax structure

*Note* that tree-sitter produces a concrete syntax tree and we currently parse
the CST as is. Future versions of code.ast might include options to simplify the CST
to an AST.

## Installation
The package is tested under Python 3. It can be installed via:
```bash
pip install code-ast
```

Note: You need to install the different tree-sitter languages as Python packages.
For example, for Python, you need to install `tree-sitter-python` via PIP:
```bash
pip install tree-sitter-python
```

Note (since tree-sitter v0.22.0): Autoloading of languages or installation with `tree_sitter_language` to utilize pre-compiled languages is deprecated. If you fix the tree-sitter version to `0.21.3` than you can make use of pre-compiled languages via:
```bash
pip install tree_sitter_languages
```

## Quick start
code.ast can parse nearly any program code in a few lines of code:
```python
import code_ast

# Python
code_ast.ast(
    '''
        def my_func():
            print("Hello World")
    ''',
lang = "python")

# Output:
# PythonCodeAST [0, 0] - [4, 4]
#    module [1, 8] - [3, 4]
#        function_definition [1, 8] - [2, 32]
#            identifier [1, 12] - [1, 19]
#            parameters [1, 19] - [1, 21]
#            block [2, 12] - [2, 32]
#                expression_statement [2, 12] - [2, 32]
#                    call [2, 12] - [2, 32]
#                        identifier [2, 12] - [2, 17]
#                        argument_list [2, 17] - [2, 32]
#                            string [2, 18] - [2, 31]

# Java
code_ast.ast(
    '''
    public class HelloWorld {
        public static void main(String[] args){
          System.out.println("Hello World");
        }
    }
    ''',
lang = "java")

# Output: 
# JavaCodeAST [0, 0] - [7, 4]
#    program [1, 0] - [6, 4]
#        class_declaration [1, 0] - [5, 1]
#            modifiers [1, 0] - [1, 6]
#            identifier [1, 13] - [1, 23]
#            class_body [1, 24] - [5, 1]
#                method_declaration [2, 8] - [4, 9]
#                    ...


```

## Visitors
code.ast implements the visitor pattern to quickly traverse the CST structure:
```python
import code_ast
from code_ast import ASTVisitor

code = '''
    def f(x, y):
        return x + y
'''

# Count the number of identifiers
class IdentifierCounter(ASTVisitor):

    def __init__(self):
        self.count = 0
    
    def visit_identifier(self, node):
        self.count += 1

# Parse the AST and then visit it with our visitor
source_ast = code_ast.ast(code, lang = "python")

count_visitor = IdentifierCounter()
source_ast.visit(count_visitor)

count_visitor.count
# Output: 5

```

## Transformers
Transformers provide an easy way to transform source code. For example, in the following, we want to mirror each binary addition:
```python
import code_ast
from code_ast import ASTTransformer, FormattedUpdate, TreeUpdate

code = '''
    def f(x, y):
        return x + y + 0.5
'''

# Mirror binary operator on leave
class MirrorAddTransformer(ASTTransformer):
    def leave_binary_operator(self, node):
        if node.children[1].type == "+":
            return FormattedUpdate(
                " %s + %s",
                [
                    TreeUpdate(node.children[2]),
                    TreeUpdate(node.children[0])
                ]
            )

# Parse the AST and then visit it with our visitor
source_ast = code_ast.ast(code, lang = "python")

mirror_transformer = MirrorAddTransformer()

# Mirror transformer are initialized by running them as visitors
source_ast.visit(mirror_transformer)

# Transformer provide a minimal AST edit
mirror_transformer.edit()
# Output: 
# module [2, 0] - [5, 0]
#    function_definition [2, 0] - [3, 22]
#        block [3, 4] - [3, 22]
#            return_statement [3, 4] - [3, 22]
#                binary_operator -> FormattedUpdate [3, 11] - [3, 22]
#                    binary_operator -> FormattedUpdate [3, 11] - [3, 16]

# And it can be used to directly transform the code
mirror_transformer.code()
# Output:
# def f(x, y):
#    return 0.5 + y + x

```

## Project Info
The goal of this project is to provide developer in the
programming language processing community with easy
access to syntax parsing. This is currently developed as a helper library for internal research projects. Therefore, it will only be updated
as needed.

Feel free to open an issue if anything unexpected
happens. 

Distributed under the MIT license. See ``LICENSE`` for more information.

We thank the developer of [tree-sitter](https://tree-sitter.github.io/tree-sitter/) library. Without tree-sitter this project would not be possible. 
