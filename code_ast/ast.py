from .parsers import match_span

class SourceCodeAST:

    def __init__(self, config, source_tree, source_lines):
        self.config = config
        self.source_tree = source_tree
        self.source_lines = source_lines

    def root_node(self):
        return self.source_tree.root_node

    def match(self, source_node):
        return match_span(source_node, self.source_lines)

    # Visit tree ----------------------------------------------------------------

    def visit(self, visitor):

        try:
            visitor.from_code_lines(self.source_lines)
        except AttributeError:
            # Is not a transformer
            pass

        visitor(self.source_tree)

    # Repr ----------------------------------------------------------------

    def code(self):
        return "\n".join(self.source_lines)

    def __repr__(self):

        lang = self.config.lang
        lang_name = "".join((lang_part[0].upper() + lang_part[1:] for lang_part in lang.split("-")))

        ast_repr = ast_to_str(self.source_tree, indent = 1)

        return f"{lang_name}CodeAST [0, 0] - [{len(self.source_lines)}, {len(self.source_lines[-1])}]\n{ast_repr}"


# AST to readable ----------------------------------------------------------------

LEAVE_WHITELIST = {"identifier", "integer", "float"}

def _serialize_node(node):
    return f"{node.type} [{node.start_point[0]}, {node.start_point[1]}] - [{node.end_point[0]}, {node.end_point[1]}]"

def ast_to_str(tree, indent = 0):
    ast_lines = []
    root_node = tree.root_node
    cursor    = root_node.walk()

    has_next = True

    while has_next:
        current_node = cursor.node

        if current_node.child_count > 0 or current_node.type in LEAVE_WHITELIST:
            ast_lines.append("    "*indent + _serialize_node(current_node))

        # Step 1: Try to go to next child if we continue the subtree
        if cursor.goto_first_child():
            indent += 1
            has_next = True
        else:
            has_next = False

        # Step 2: Try to go to next sibling
        if not has_next:
            has_next = cursor.goto_next_sibling()

        # Step 3: Go up until sibling exists
        while not has_next and cursor.goto_parent():
            indent -= 1
            has_next = cursor.goto_next_sibling()

    return "\n".join(ast_lines)