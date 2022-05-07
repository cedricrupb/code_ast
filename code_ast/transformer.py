from typing import Any, List
from dataclasses import dataclass

from .visitor import ASTVisitor
from .parsers import match_span


class ASTTransformer(ASTVisitor):
    
    def __init__(self):
        super().__init__()
        self.code_lines    = None
        self._edit_trees       = []

    # Code processing functions --------------------------------

    def from_code_lines(self, code_lines):
        self.code_lines = code_lines

    def code(self):
        return self.edit().apply(self.code_lines)

    def edit(self):
        assert len(self._edit_trees) == 1, "Something went wrong during parsing"
        return self._edit_trees[0]

    def on_leave(self, original_node):
        node_update = super().on_leave(original_node)

        if isinstance(node_update, str):
            node_update = TextUpdate(node_update)

        num_children = original_node.child_count
        child_trees  = [self._edit_trees.pop(-1) for _ in range(num_children)][::-1]

        if node_update is None or not isinstance(node_update, EditUpdate):
            self._edit_trees.append(EditTree(original_node, None, child_trees))
            return

        self._edit_trees.append(EditTree(original_node, node_update, child_trees))


# Minimal edit tree ------------------------------------------------------------

class EditTree:

    def __init__(self, source_node, target_edit = None, children = []):
        self.source_node = source_node
        self.target_edit = target_edit
        self.children    = children

        for c in children:
            if c.target_edit is None: c.children = []

        if target_edit is None and any(c.target_edit is not None for c in self.children):
            self.target_edit = SubtreeUpdate()

    def apply(self, code_lines):
        return EditExecutor(self, code_lines).walk()

    def __repr__(self):
        return "\n".join(_edit_to_str(self))

# Edit operations ----------------------------------------------------------------

@dataclass
class EditUpdate:
    
    def compile(self, sub_edits = None, code_lines = None):
        return ""

    @property
    def type(self):
        return self.__class__.__name__


@dataclass
class SubtreeUpdate(EditUpdate):
    pass


@dataclass
class TextUpdate(EditUpdate):
    text : str

    def compile(self, sub_edits = None, code_lines = None):
        return self.text

@dataclass
class NodeUpdate(EditUpdate):
    node : Any

    def compile(self, sub_edits = None, code_lines = None):
        return match_span(self.node, code_lines)


@dataclass
class TreeUpdate(EditUpdate):
    node : Any

    def compile(self, sub_edits = None, code_lines = None):
        
        for sub_edit in sub_edits:
            if sub_edit.target_edit is None: continue
            if sub_edit.source_node == self.node:
                return sub_edit.target_edit.compile(
                    sub_edit.children, code_lines
                )

        return match_span(self.node, code_lines)


@dataclass
class FormattedUpdate(EditUpdate):
    format_str : str
    args       : List[EditUpdate]

    def compile(self, sub_edits = None, code_lines = None):
        args = tuple(arg.compile(sub_edits, code_lines) 
                        for arg in self.args)
        return self.format_str % args


# Edit to str ----------------------------------------------------------------

def _serialize_tree(edit_tree):
    source = edit_tree.source_node
    if edit_tree.target_edit.type == "SubtreeUpdate":
        return f"{source.type} [{source.start_point[0]}, {source.start_point[1]}] - [{source.end_point[0]}, {source.end_point[1]}]"

    return f"{source.type} -> {edit_tree.target_edit.type} [{source.start_point[0]}, {source.start_point[1]}] - [{source.end_point[0]}, {source.end_point[1]}]"


def _edit_to_str(edit_tree, indent = 0):
    str_lines = []
    if edit_tree.target_edit is None: return []

    str_lines.append(
        "    " * indent + _serialize_tree(edit_tree)
    )
    str_lines.extend([l for c in edit_tree.children for l in _edit_to_str(c, indent = indent + 1)])

    return  str_lines



# A simple edit executor --------------------------------------------------------

class EditExecutor:

    def __init__(self, edit_tree, code_lines):
        self.code_lines = code_lines

        self._edit_stack   = [edit_tree]
        self._target_lines = []

        # Cursors
        self._cursor       = (0, 0)
        self._delay_move   = (0, 0)

    def _move_cursor(self, position):
        assert position >= self._cursor

        while self._cursor[0] < position[0]:
            if self._cursor[1] == 0:
                self._target_lines.append(self.code_lines[self._cursor[0]])
            else:
                add_part = self.code_lines[self._cursor[0]][self._cursor[1]:]
                self._target_lines.append(add_part)
            
            self._target_lines.append("\n")
            self._cursor = (self._cursor[0] + 1, 0)

        if self._cursor[1] < position[1]:
            add_part = self.code_lines[self._cursor[0]][self._cursor[1]:position[1]]
            self._target_lines.append(add_part)
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
        
        if edit_tree.target_edit.type == "SubtreeUpdate":
            self._edit_stack.extend(edit_tree.children[::-1])
            return

        if self._delay_move >= self._cursor:
            self._move_cursor(self._delay_move)
            self._delay_move = self._cursor

        self._cursor = edit_tree.source_node.end_point
        self._target_lines.append(
                edit_tree.target_edit.compile(
                    edit_tree.children, 
                    self.code_lines
                )
        )

    def walk(self):
        
        while len(self._edit_stack) > 0:
            self._execute(self._edit_stack.pop(-1))

        if self._delay_move >= self._cursor:
            self._move_cursor(self._delay_move)
            self._delay_move = self._cursor

        return "".join(self._target_lines)