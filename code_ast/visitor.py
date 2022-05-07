"""
AST Visitors

Can be directly executed on AST structures
"""

class ASTVisitor:

    # Decreased version of visit (no edges are supported) -----------------------

    def visit(self, node):
        """
        Default visitor function

        Override this to capture all nodes that are not covered by a specific visitor.
        """

    def leave(self, node):
        """
        Default leave function

        This is called when a subtree rooted at the given node is left.
        Override this to capture all nodes that are not covered by a specific leave function.
        """

    # Internal methods ---------------------------------------------------------

    def on_visit(self, node):
        visitor_fn = getattr(self, "visit_%s" % node.type, self.visit)
        return visitor_fn(node) is not False

    def on_leave(self, node):
        leave_fn = getattr(self, "leave_%s" % node.type, self.leave)
        return leave_fn(node)

    # Navigation ----------------------------------------------------------------

    def walk(self, root_node):
        if root_node is None: return
        
        cursor   = root_node.walk()
        has_next = True

        while has_next:
            current_node = cursor.node
            # Step 1: Try to go to next child if we continue the subtree
            if self.on_visit(current_node):
                has_next = cursor.goto_first_child()
            else:
                has_next = False

            # Step 2: Try to go to next sibling
            if not has_next:
                self.on_leave(current_node)
                has_next = cursor.goto_next_sibling()

            # Step 3: Go up until sibling exists
            while not has_next and cursor.goto_parent():
                self.on_leave(cursor.node) # We will never return back to this specific parent
                has_next = cursor.goto_next_sibling()

                
    def __call__(self, root_node):
        return self.walk(root_node)


# Compositions ----------------------------------------------------------------

class VisitorComposition(ASTVisitor):

    def __init__(self, *visitors):
        super().__init__()
        self.visitors = visitors

    def on_visit(self, node):
        for base_visitor in self.visitors:
            if base_visitor.on_visit(node) is False: return False
        return True

    def on_leave(self, node):
        for base_visitor in self.visitors:
            base_visitor.on_leave(node)

    def __repr__(self):
        return str(self.visitors)


class ResumingVisitorComposition(ASTVisitor):
    """
    Unlike a standard composition, visitors
    are resumed even if one visitor stops for a branch.

    This class should be equivalent to running N visitors
    in sequence.
    """

    def __init__(self, *visitors):
        super().__init__()
        self.visitors = visitors

        self.__active_visitors = [True] * len(visitors)
        self.__resume_on       = {}
    
    def on_visit(self, node):
        for pos, base_visitor in enumerate(self.visitors):
            if not self.__active_visitors[pos]: continue

            if base_visitor.on_visit(node) is False:
                self.__active_visitors[pos] = False
                self.__resume_on[pos] = node

        return any(self.__active_visitors)

    
    def on_leave(self, node):
        for pos, base_visitor in enumerate(self.visitors):
            if not self.__active_visitors[pos]:
                resume_node = self.__resume_on[pos]
                if resume_node == node:
                    self.__active_visitors[pos] = True
                else:
                    continue
            
            base_visitor.on_leave(node)

