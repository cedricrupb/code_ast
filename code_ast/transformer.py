from .visitor import ASTVisitor

class ASTTransformer(ASTVisitor):
    
    def __init__(self):
        super().__init__()
        self.org_code_lines    = None
        self._edit_trees       = []

    # Code processing functions --------------------------------

    def from_code_lines(self, code_lines):
        self.org_code_lines = code_lines

    def code(self):
        assert len(self._edit_trees) == 1, "Something went wrong during parsing"
        return self._edit_trees[0].apply(self.org_code_lines)

    def on_leave(self, original_node):
        updated_node = super().on_leave(original_node)

        num_children = original_node.child_count
        child_trees  = [self._edit_trees.pop(-1) for _ in range(num_children)][::-1]

        if updated_node is None or updated_node is original_node:
            self._edit_trees.append(EditTree(original_node, None, child_trees))
            return

        self._edit_trees.append(EditTree(original_node, updated_node, child_trees))


# Minimal edit tree ------------------------------------------------------------

class EditTree:

    def __init__(self, source_node, target_edit = None, children = []):
        self.source_node = source_node
        self.target_edit = target_edit
        self.children    = children

        for c in children:
            if c.target_edit is None: c.children = []

        if target_edit is None and any(c.target_edit is not None for c in self.children):
            self.target_edit = "SUBTREE"

    def apply(self, code_lines):
        return "\n".join(EditExecutor(self, code_lines).walk())

    def __repr__(self):
        target_edit = "UNCHANGED" if self.target_edit is None else self.target_edit
        return f"EditTree({len(self.children)}): {self.source_node} -> {target_edit}"



# A simple edit executor --------------------

class EditExecutor:

    def __init__(self, edit_tree, code_lines):
        self.code_lines = code_lines

        self._edit_stack   = [edit_tree]
        self._target_lines = []
        self._cursor       = (0, 0)
        self._delay_move   = (0, 0)

    def _move_cursor(self, position):
        assert position >= self._cursor

        while self._cursor[0] < position[0]:
            if self._cursor[1] == 0:
                self._target_lines.append(self.code_lines[self._cursor[0]])
            else:
                add_part = self.code_lines[self._cursor[0]][self._cursor[1]:]
                self._target_lines[-1] += add_part

            self._cursor = (self._cursor[0] + 1, 0)

        if self._cursor[1] < position[1]:
            add_part = self.code_lines[self._cursor[0]][self._cursor[1]:position[1]]
            if self._cursor[1] == 0:
                self._target_lines.append(add_part)
            else:
                self._target_lines[-1] += add_part
            
            self._cursor = (self._cursor[0], position[1])

    def _delay_cursor(self, position):
        assert position >= self._cursor
        self._delay_move = position

    def _execute_noop(self, edit_tree):
        node     = edit_tree.source_node
        node_end = node.end_point
        self._delay_cursor(node_end)

    def _execute(self, edit_tree):

        if edit_tree.target_edit is None:
            self._execute_noop(edit_tree)
            return
        
        if edit_tree.target_edit == "SUBTREE":
            self._edit_stack.extend(edit_tree.children[::-1])
            return

        if self._delay_move >= self._cursor:
            self._move_cursor(self._delay_move)
            self._delay_move = self._cursor

        self._cursor = edit_tree.source_node.end_point
        self._target_lines[-1] += edit_tree.target_edit


    def walk(self):
        
        while len(self._edit_stack) > 0:
            self._execute(self._edit_stack.pop(-1))

        if self._delay_move >= self._cursor:
            self._move_cursor(self._delay_move)
            self._delay_move = self._cursor

        return self._target_lines