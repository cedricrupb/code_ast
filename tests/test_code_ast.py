from unittest import TestCase

from code_ast import ast, ASTParser, ASTVisitor, ASTTransformer

from code_ast.transformer import FormattedUpdate, TreeUpdate

# Prepare parser
ASTParser("python") # Bootstrap parser for all test runs

# Test the general language parsers ----------------------------------------------------------------

class TestPythonParser(TestCase):
    
    def test_ast_fn(self):
        code_ast = ast("def foo():\n    bar()", lang = "python")

        current_node = code_ast.root_node()
        self.assertEqual(current_node.type, "module")

        self.assertEqual(current_node.child_count, 1)
        current_node = current_node.children[0]
        self.assertEqual(current_node.type, "function_definition")

        self.assertEqual(current_node.child_count, 5)
        self.assertEqual(current_node.children[0].type, "def")
        self.assertEqual(current_node.children[1].type, "identifier")
        self.assertEqual(current_node.children[2].type, "parameters")
        self.assertEqual(current_node.children[4].type, "block")

        current_node = current_node.children[4]
        self.assertEqual(current_node.child_count, 1)
        current_node = current_node.children[0]
        self.assertEqual(current_node.type, "expression_statement")

        self.assertEqual(current_node.child_count, 1)
        current_node = current_node.children[0]
        self.assertEqual(current_node.type, "call")

    def test_match_fn(self):
        code_ast = ast("def foo():\n    bar()", lang = "python")

        current_node = code_ast.root_node()
        current_node = current_node.children[0]

        self.assertEqual(current_node.child_count, 5)
        self.assertEqual(current_node.children[1].type, "identifier")
        self.assertEqual(
            code_ast.match(current_node.children[1]), "foo"
        )

        current_node = current_node.children[4]
        current_node = current_node.children[0]
        current_node = current_node.children[0]
        current_node = current_node.children[0]
        self.assertEqual(current_node.type, "identifier")

        self.assertEqual(
            code_ast.match(current_node), "bar"
        )


# Test visitors ------------------------------------------------------------------------------------


class TestVisitor(TestCase):

    def test_count_identifier(self):
        code_ast = ast("def foo():\n    bar()", lang = "python")

        class IdCounter(ASTVisitor):

            def __init__(self):
                self.count = 0
            
            def visit_identifier(self, node):
                self.count += 1
        
        counter = IdCounter()
        code_ast.visit(counter)
        self.assertEqual(counter.count, 2)

    def test_count_identifier2(self):
        code_ast = ast("def foo(x, y):\n    return x + y", lang = "python")

        class IdCounter(ASTVisitor):

            def __init__(self):
                self.count = 0
            
            def visit_identifier(self, node):
                self.count += 1
        
        counter = IdCounter()
        code_ast.visit(counter)
        self.assertEqual(counter.count, 5)


# Test transforms ----------------------------------------------------------------------------------

class TestTransformer(TestCase):

    def test_transform_add(self):
        code_ast = ast("def foo(x, y):\n return x + y", lang = "python")

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

        mirror_transformer = MirrorAddTransformer()
        code_ast.visit(mirror_transformer)

        source_edit = mirror_transformer.edit()

        current_node = source_edit.children[0] 
        self.assertEqual(current_node.source_node.type, "function_definition")
        current_node = current_node.children[-1] 
        self.assertEqual(current_node.source_node.type, "block")
        current_node = current_node.children[0] 
        self.assertEqual(current_node.source_node.type, "return_statement")
        current_node = current_node.children[-1] 
        self.assertTrue(current_node.target_edit is not None)
        

        transformed_code = mirror_transformer.code()
        self.assertEqual(transformed_code, "def foo(x, y):\n return y + x")



