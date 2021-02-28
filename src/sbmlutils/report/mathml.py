"""Sympy based content to presentation MathML conversion.

A common problem in rendering MathML is that the content MathML is difficult to read.
The presentation MathML has a much better rendering and improves understandability.
This module uses stylesheets for the conversion of content MathMl -> presention MathML.

This is currently just a proof of principle.
Content MathML would improve readability of reports.

MathML is currently rendered with MathJax http://docs.mathjax.org/en/latest/
in the report. This should be updated using sympy for converstion to latex
or presentation mathml

astnode -> content MathML -> expr -> latex
formula (annotation) -> expr -> latex

see also: https://docs.sympy.org/dev/modules/printing.html#module-sympy.printing.mathml
"""
import logging
from typing import Any, List, Set

import libsbml
from sympy import Symbol, sympify
from sympy.printing.latex import latex
from sympy.printing.mathml import MathMLContentPrinter, MathMLPresentationPrinter


logger = logging.getLogger(__name__)


def formula_to_astnode(formula: str) -> libsbml.ASTNode:
    """Convert formula string to ASTNode.

    :param formula: SBML formula string
    :return: libsbml.ASTNode
    """
    astnode = libsbml.parseL3Formula(formula)
    if not astnode:
        logging.error(f"Formula could not be parsed: '{formula}'")
        logging.error(libsbml.getLastParseL3Error())
    return astnode


def cmathml_to_astnode(cmathml: str) -> libsbml.ASTNode:
    """Convert Content MathML string to ASTNode.

    :param cmathml: SBML Content MathML string
    :return: libsbml.ASTNode
    """
    return libsbml.readMathMLFromString(cmathml)


def astnode_to_expression(astnode: libsbml.ASTNode) -> Any:
    """Convert AstNode to sympy expression.

    An AST node in libSBML is a recursive tree structure; each node has a type,
    a pointer to a value, and a list of children nodes. Each ASTNode node may
    have none, one, two, or more children depending on its type. There are
    node types to represent numbers (with subtypes to distinguish integer,
    real, and rational numbers), names (e.g., constants or variables),
    simple mathematical operators, logical or relational operators and
    functions.

    see also: http://sbml.org/Software/libSBML/docs/python-api/libsbml-math.html

    :param astnode: libsbml.ASTNode
    :return: sympy expression
    """
    formula = libsbml.formulaToL3String(astnode)
    return formula_to_expression(formula)


def formula_to_expression(formula: str) -> Any:
    """Parse sympy expression from given formula string.

    :param formula: SBML formula string
    :return: sympy expression
    """
    # round trip to remove unnecessary inline dimensions
    ast_node = formula_to_astnode(formula)
    variables = _get_variables(ast_node)

    # simplify lambda expressions
    ast_node = _remove_lambda2(ast_node)

    settings = libsbml.L3ParserSettings()
    settings.setParseUnits(False)
    formula = libsbml.formulaToL3StringWithSettings(ast_node, settings=settings)

    # create sympy expressions with variables and formula
    formula = _replace_piecewise(formula)
    formula = formula.replace("&&", "&")
    formula = formula.replace("||", "|")
    try:
        expr = sympify(formula, locals={v: Symbol(f"{v}") for v in variables})
    except Exception as e:
        logger.error(f"Formula could not be sympified: '{formula}'")
        raise e

    return expr


def _get_variables(astnode: libsbml.ASTNode, variables: Set[str] = None) -> Set[str]:
    """Get variables from ASTNode."""
    if variables is None:
        variables: Set[str] = set()  # type: ignore

    num_children = astnode.getNumChildren()
    if num_children == 0:
        if astnode.isName():
            name = astnode.getName()
            variables.add(name)  # type: ignore
    else:
        for k in range(num_children):
            child = astnode.getChild(k)  # type: libsbml.ASTNode
            _get_variables(child, variables=variables)

    return variables  # type: ignore


def _remove_lambda2(astnode: libsbml.ASTNode) -> libsbml.ASTNode:
    """Replace lambda function with function expression.

    Removes the lambda and argument parts from lambda expressions;
    lambda(x, y, x+y) -> x+y

    :param formula: SBML formula string
    :return: formula string
    """
    if astnode.isLambda():
        num_children = astnode.getNumChildren()
        # get function with arguments
        f = astnode.getChild(num_children - 1)  # type: libsbml.ASTNode
        return f.deepCopy()

    return astnode


def _replace_piecewise(formula: str) -> str:
    """Replace libsbml piecewise with sympy piecewise.

    :param formula: SBML formula string
    :return: formula string
    """
    while True:
        index = formula.find("piecewise(")
        if index == -1:
            break

        # process piecewise
        search_idx = index + 9

        # init counters
        bracket_open = 0
        pieces = []
        piece_chars: List[str] = []

        while search_idx < len(formula):
            c = formula[search_idx]
            if c == ",":
                if bracket_open == 1:
                    pieces.append("".join(piece_chars).strip())
                    piece_chars = []
            else:
                if c == "(":
                    if bracket_open != 0:
                        piece_chars.append(c)
                    bracket_open += 1
                elif c == ")":
                    if bracket_open != 1:
                        piece_chars.append(c)
                    bracket_open -= 1
                else:
                    piece_chars.append(c)

            if bracket_open == 0:
                pieces.append("".join(piece_chars).strip())
                break

            # next character
            search_idx += 1

        # find end index
        if (len(pieces) % 2) == 1:
            pieces.append("True")  # last condition is True

        sympy_pieces = []
        for k in range(0, int(len(pieces) / 2)):
            sympy_pieces.append(f"({pieces[2*k]}, {pieces[2*k+1]})")
        new_str = f"Piecewise({','.join(sympy_pieces)})"
        formula = formula.replace(formula[index : search_idx + 1], new_str)

    return formula


def astnode_to_mathml(
    astnode: libsbml.ASTNode, printer: str = "content", **settings: Any
) -> str:
    """Convert formula to presentation/content MathML.

    This does not use ASTNode serialization, but parsing of the
    corresponding formula due to differences in MathML!

    :param printer:
    :param astnode: ASTNode
    :param settings:
    :return: Content or presentation MathML
    """
    expr = astnode_to_expression(astnode)
    return _expression_to_mathml(expr=expr, printer=printer, **settings)


def formula_to_mathml(formula: str, printer: str = "content", **settings: Any) -> str:
    """Convert formula to MathML.

    :param formula: SBML formula string
    :param printer: 'content' or 'presentation'
    :param settings:
    :return: Content or presentation MathML
    """
    expr = formula_to_expression(formula=formula)
    return _expression_to_mathml(expr=expr, printer=printer, **settings)


def _expression_to_mathml(expr: Any, printer: str = "content", **settings: Any) -> str:
    """Convert sympy expression to MathML.

    :param expr: sympy expression
    :param printer: 'content' or 'presentation'
    :param settings:
    :return: Content or presentation MathML
    """
    if printer == "presentation":
        s = MathMLPresentationPrinter(settings)
    else:
        s = MathMLContentPrinter(settings)
    xml = s._print(sympify(expr))
    s.apply_patch()
    pretty_xml = xml.toprettyxml()
    s.restore_patch()
    return str(pretty_xml)


def cmathml_to_pmathml(cmathml: str, **settings: Any) -> str:
    """Convert Content MathML to PresentationMathML.

    :param cmathml: Content MathML
    :param settings:
    :return: Presentation MathML
    """
    astnode = cmathml_to_astnode(cmathml)
    expr = astnode_to_expression(astnode)
    return _expression_to_mathml(expr, printer="presentation", **settings)


def formula_to_latex(formula: str, **settings: Any) -> str:
    """Convert formula to latex.

    :param formula: SBML formula string
    :param settings:
    :return: Latex string
    """
    expr = formula_to_expression(formula)
    return latex(expr, mul_symbol="dot", **settings)  # type: ignore


def astnode_to_latex(astnode: libsbml.ASTNode, **settings: Any) -> str:
    """Convert AstNode to Latex.

    :param astnode: libsbml.ASTNode
    :param settings:
    :return: Latex string
    """
    expr = astnode_to_expression(astnode)
    return latex(expr, mul_symbol="dot", **settings)  # type: ignore


def cmathml_to_latex(cmathml: str, **settings: Any) -> str:
    """Convert Content MathML to Latex.

    :param cmathml: Content Mathml string
    :param settings:
    :return: Latex string
    """
    astnode = cmathml_to_astnode(cmathml)
    return astnode_to_latex(astnode, **settings)
