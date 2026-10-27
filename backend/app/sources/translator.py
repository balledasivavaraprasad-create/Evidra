"""Translate abstract Boolean AST queries into provider-specific query syntax."""
from app.contracts.enums import BooleanOperator, SourceNamespace
from app.contracts.models import QueryASTNode


def _escape_phrase(term: str) -> str:
    """Strip extraneous quotes and trim whitespace."""
    clean = term.strip().strip('"').strip("'")
    return clean


def translate_pubmed_ast(node: QueryASTNode) -> str:
    """Recursively translate AST to PubMed query with Title/Abstract field tags."""
    if node.term is not None:
        phrase = _escape_phrase(node.term)
        return f'"{phrase}"[Title/Abstract]'

    if not node.children:
        return ""

    operator = node.operator or BooleanOperator.AND
    translated_children = [translate_pubmed_ast(child) for child in node.children]
    translated_children = [c for c in translated_children if c]

    if not translated_children:
        return ""
    if len(translated_children) == 1:
        return translated_children[0]

    op_str = f" {operator.value} "
    return f"({op_str.join(translated_children)})"


def translate_europepmc_ast(node: QueryASTNode) -> str:
    """Recursively translate AST to Europe PMC query syntax with TITLE_ABS prefix."""
    if node.term is not None:
        phrase = _escape_phrase(node.term)
        return f'TITLE_ABS:"{phrase}"'

    if not node.children:
        return ""

    operator = node.operator or BooleanOperator.AND
    translated_children = [translate_europepmc_ast(child) for child in node.children]
    translated_children = [c for c in translated_children if c]

    if not translated_children:
        return ""
    if len(translated_children) == 1:
        return translated_children[0]

    op_str = f" {operator.value} "
    return f"({op_str.join(translated_children)})"


def build_pubmed_query(
    ast: QueryASTNode,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Assemble complete PubMed query string including publication date filters."""
    query = translate_pubmed_ast(ast)
    if not query:
        query = "all[Filter]"

    if start_date or end_date:
        start_fmt = (start_date or "1900").replace("-", "/")
        end_fmt = (end_date or "3000").replace("-", "/")
        query = f'({query}) AND ("{start_fmt}"[Date - Publication] : "{end_fmt}"[Date - Publication])'

    return query


def build_europepmc_query(
    ast: QueryASTNode,
    start_date: str | None = None,
    end_date: str | None = None,
    synonym_expansion: bool = False,
) -> str:
    """Assemble complete Europe PMC query string including date filters."""
    query = translate_europepmc_ast(ast)
    if not query:
        query = "*"

    if start_date or end_date:
        start_str = start_date or "1900-01-01"
        end_str = end_date or "3000-12-31"
        # Pad years if needed (e.g. '2020' -> '2020-01-01')
        if len(start_str) == 4:
            start_str += "-01-01"
        elif len(start_str) == 7:
            start_str += "-01"
        if len(end_str) == 4:
            end_str += "-12-31"
        elif len(end_str) == 7:
            end_str += "-28"
        query = f"({query}) AND (FIRST_PDATE:[{start_str} TO {end_str}])"

    return query


def translate_query(
    source: SourceNamespace,
    ast: QueryASTNode,
    start_date: str | None = None,
    end_date: str | None = None,
    synonym_expansion: bool = False,
) -> str:
    """Dispatch translation to the appropriate provider syntax."""
    if source == SourceNamespace.PUBMED:
        return build_pubmed_query(ast, start_date, end_date)
    if source == SourceNamespace.EUROPEPMC:
        return build_europepmc_query(ast, start_date, end_date, synonym_expansion)
    # Default fallback
    return build_pubmed_query(ast, start_date, end_date)
