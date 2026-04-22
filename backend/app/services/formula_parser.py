"""DSL Parser pour formules de lignes prévisionnelles (Plan 5b Phase 4).

Grammaire (récursif descendant, pas d'eval) :
    expr    := term (('+' | '-') term)*
    term    := factor (('*' | '/') factor)*
    factor  := NUMBER | REF | '(' expr ')' | '-' factor
    NUMBER  := digit+ ('.' digit+)?
    REF     := '{' IDENT ('_M-' DIGIT+)? '}'
    IDENT   := caractères alphanumériques + accents + espace (trimmed, case-insensitive)
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Callable, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session


class FormulaError(Exception):
    """Erreur de parsing ou d'évaluation d'une formule."""


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------


@dataclass
class Num:
    value: Decimal


@dataclass
class Ref:
    category_name: str  # normalized (stripped, lowercase)
    month_offset: int  # 0 = current, N = M-N


@dataclass
class BinOp:
    op: str  # '+', '-', '*', '/'
    left: "Node"
    right: "Node"


@dataclass
class UnaryOp:
    op: str  # '-'
    operand: "Node"


Node = Union[Num, Ref, BinOp, UnaryOp]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def _normalize_ident(raw: str) -> str:
    """Trim + lowercase, utilisé pour la comparaison des noms de catégories."""
    return raw.strip().lower()


def _tokenize(expr: str) -> list[tuple[str, object]]:
    """Retourne une liste (kind, value).

    kinds: NUMBER, REF, LPAREN, RPAREN, PLUS, MINUS, STAR, SLASH, EOF
    """
    tokens: list[tuple[str, object]] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c == "(":
            tokens.append(("LPAREN", "("))
            i += 1
            continue
        if c == ")":
            tokens.append(("RPAREN", ")"))
            i += 1
            continue
        if c == "+":
            tokens.append(("PLUS", "+"))
            i += 1
            continue
        if c == "-":
            tokens.append(("MINUS", "-"))
            i += 1
            continue
        if c == "*":
            tokens.append(("STAR", "*"))
            i += 1
            continue
        if c == "/":
            tokens.append(("SLASH", "/"))
            i += 1
            continue
        if c.isdigit() or c == ".":
            j = i
            has_dot = False
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                if expr[j] == ".":
                    if has_dot:
                        raise FormulaError(f"Nombre invalide en position {i}")
                    has_dot = True
                j += 1
            raw = expr[i:j]
            try:
                tokens.append(("NUMBER", Decimal(raw)))
            except InvalidOperation as exc:
                raise FormulaError(f"Nombre invalide '{raw}'") from exc
            i = j
            continue
        if c == "{":
            # Parse REF : {IDENT(_M-N)?}
            j = i + 1
            end = expr.find("}", j)
            if end == -1:
                raise FormulaError("Référence '{' sans '}' de fermeture")
            inside = expr[j:end]
            if not inside.strip():
                raise FormulaError("Référence vide '{}'")
            # offset ?
            offset = 0
            ident_part = inside
            # Cherche suffix _M-\d+ à la fin
            suffix_marker = inside.rfind("_M-")
            if suffix_marker != -1:
                digits = inside[suffix_marker + 3 :]
                if digits.isdigit() and digits:
                    offset = int(digits)
                    ident_part = inside[:suffix_marker]
                # sinon on considère que _M- fait partie du nom
            ident = _normalize_ident(ident_part)
            if not ident:
                raise FormulaError(f"Nom de catégorie vide dans '{{{inside}}}'")
            tokens.append(("REF", Ref(category_name=ident, month_offset=offset)))
            i = end + 1
            continue
        raise FormulaError(f"Caractère inattendu '{c}' en position {i}")
    tokens.append(("EOF", None))
    return tokens


# ---------------------------------------------------------------------------
# Parser (recursive descent)
# ---------------------------------------------------------------------------


class _Parser:
    def __init__(self, tokens: list[tuple[str, object]]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> tuple[str, object]:
        return self.tokens[self.pos]

    def advance(self) -> tuple[str, object]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str) -> tuple[str, object]:
        tok = self.peek()
        if tok[0] != kind:
            raise FormulaError(f"Attendu {kind}, trouvé {tok[0]}")
        return self.advance()

    def parse_expr(self) -> Node:
        node = self.parse_term()
        while self.peek()[0] in ("PLUS", "MINUS"):
            op = "+" if self.advance()[0] == "PLUS" else "-"
            right = self.parse_term()
            node = BinOp(op=op, left=node, right=right)
        return node

    def parse_term(self) -> Node:
        node = self.parse_factor()
        while self.peek()[0] in ("STAR", "SLASH"):
            op = "*" if self.advance()[0] == "STAR" else "/"
            right = self.parse_factor()
            node = BinOp(op=op, left=node, right=right)
        return node

    def parse_factor(self) -> Node:
        kind, value = self.peek()
        if kind == "MINUS":
            self.advance()
            operand = self.parse_factor()
            return UnaryOp(op="-", operand=operand)
        if kind == "NUMBER":
            self.advance()
            return Num(value=value)  # type: ignore[arg-type]
        if kind == "REF":
            self.advance()
            return value  # type: ignore[return-value]
        if kind == "LPAREN":
            self.advance()
            node = self.parse_expr()
            self.expect("RPAREN")
            return node
        raise FormulaError(f"Expression invalide (token inattendu '{kind}')")


def parse(expr: str) -> Node:
    """Parse une expression DSL, raise FormulaError si invalide."""
    if not expr or not expr.strip():
        raise FormulaError("Expression vide")
    tokens = _tokenize(expr)
    parser = _Parser(tokens)
    tree = parser.parse_expr()
    if parser.peek()[0] != "EOF":
        raise FormulaError(f"Tokens restants après parsing ({parser.peek()[0]})")
    return tree


# ---------------------------------------------------------------------------
# Refs extraction + evaluation
# ---------------------------------------------------------------------------


def extract_refs(node: Node) -> list[Ref]:
    """Retourne toutes les Refs (doublons inclus) pour détection de cycle."""
    refs: list[Ref] = []

    def visit(n: Node) -> None:
        if isinstance(n, Ref):
            refs.append(n)
        elif isinstance(n, BinOp):
            visit(n.left)
            visit(n.right)
        elif isinstance(n, UnaryOp):
            visit(n.operand)
        # Num: noop

    visit(node)
    return refs


def evaluate(node: Node, resolver: Callable[[str, int], Decimal]) -> Decimal:
    """Évalue l'AST avec un resolver (category_name, month_offset) -> Decimal.

    Raise FormulaError en cas de division par zéro.
    """
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Ref):
        return resolver(node.category_name, node.month_offset)
    if isinstance(node, UnaryOp):
        inner = evaluate(node.operand, resolver)
        return -inner
    if isinstance(node, BinOp):
        left = evaluate(node.left, resolver)
        right = evaluate(node.right, resolver)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise FormulaError("Division par zéro")
            try:
                return left / right
            except (DivisionByZero, InvalidOperation) as exc:
                raise FormulaError(f"Division invalide: {exc}") from exc
        raise FormulaError(f"Opérateur inconnu '{node.op}'")
    raise FormulaError(f"Nœud AST inconnu: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Cycle detection (DFS sur le graphe des FORMULA lines)
# ---------------------------------------------------------------------------


def detect_cycle(
    scenario_id: int,
    target_category_id: int,
    formula_expr: str,
    session: Session,
) -> bool:
    """Retourne True si la formule référence (directement ou transitivement)
    sa propre catégorie `target_category_id` dans le même scénario.

    L'algorithme :
    1. Parse la formule, extrait les Refs.
    2. Pour chaque ref, résout le nom en category_id (case-insensitive).
       Si category_id == target → cycle.
       Sinon, si la catégorie a une FORMULA line dans ce scénario → recurse.
    3. Utilise un `visited` set pour éviter les boucles infinies.

    Les refs dont le nom ne correspond à aucune catégorie sont ignorées
    (elles seront détectées ailleurs lors de l'évaluation).
    """
    from app.models.category import Category
    from app.models.forecast_line import ForecastLine, ForecastLineMethod

    try:
        root = parse(formula_expr)
    except FormulaError:
        # Formule invalide → pas un cycle, mais le parse échouera ailleurs
        return False

    # Construit un index {name_lower: category_id} une fois
    cat_rows = session.execute(select(Category.id, Category.name)).all()
    name_to_id = {r.name.strip().lower(): r.id for r in cat_rows}

    def refs_of_expr(expr_node: Node) -> list[int]:
        ids: list[int] = []
        for ref in extract_refs(expr_node):
            cid = name_to_id.get(ref.category_name)
            if cid is not None:
                ids.append(cid)
        return ids

    visited: set[int] = set()
    stack: list[int] = list(refs_of_expr(root))

    while stack:
        cid = stack.pop()
        if cid == target_category_id:
            return True
        if cid in visited:
            continue
        visited.add(cid)

        # Récupère la FORMULA line pour cette catégorie dans ce scénario
        line = session.scalar(
            select(ForecastLine).where(
                ForecastLine.scenario_id == scenario_id,
                ForecastLine.category_id == cid,
                ForecastLine.method == ForecastLineMethod.FORMULA,
            )
        )
        if line is None or not line.formula_expr:
            continue
        try:
            sub_tree = parse(line.formula_expr)
        except FormulaError:
            continue
        stack.extend(refs_of_expr(sub_tree))

    return False
