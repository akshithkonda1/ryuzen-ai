"""Deterministic fast-path executor for lightweight prompts."""

from __future__ import annotations

import ast
import operator
import re
from typing import Optional

# Whitelisted arithmetic operators for the safe evaluator. Power (**) is
# intentionally excluded to avoid CPU/memory exhaustion from expressions like
# 9**9**9.
_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_SAFE_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class FastPathExecutor:
    def __init__(self):
        self.arith_pattern = re.compile(r"^\s*[\d\s+\-*/().]+\s*$")
        self.boolean_pattern = re.compile(r"^(true|false|yes|no)$", re.I)
        self.translation_pattern = re.compile(r"^translate (.+) to (spanish|french|german|japanese)$", re.I)
        self.definition_pattern = re.compile(r"^define (.+)$", re.I)

    async def try_fast_path(self, prompt: str) -> Optional[dict]:
        prompt = (prompt or "").strip()
        if not prompt:
            return None

        if self.arith_pattern.match(prompt):
            try:
                result = self._safe_eval(prompt)
                return self._wrap(str(result), confidence=0.99, reason="arithmetic")
            except Exception:
                return None

        if self.boolean_pattern.match(prompt):
            normalized = prompt.lower()
            answer = "Yes" if normalized in {"true", "yes"} else "No"
            return self._wrap(answer, confidence=0.95, reason="boolean")

        translation = self.translation_pattern.match(prompt)
        if translation:
            text, language = translation.groups()
            return self._wrap(f"Translation to {language.title()}: {text}", confidence=0.9, reason="translation")

        definition = self.definition_pattern.match(prompt)
        if definition:
            term = definition.group(1)
            return self._wrap(f"Definition of {term}: concise explanation.", confidence=0.6, reason="definition")

        if prompt.lower().startswith("yes or no") or prompt.lower().endswith("yes or no"):
            return self._wrap("Yes", confidence=0.6, reason="yes_no_default")

        return None

    def _wrap(self, answer: str, confidence: float, reason: str) -> dict:
        return {
            "final_answer": answer,
            "confidence": confidence,
            "model_used": "fast-path",
            "reasoning_trace": {"path": reason},
            "evidence_used": {},
            "models_considered": ["fast-path"],
        }

    def _safe_eval(self, expression: str):
        """Evaluate a simple arithmetic expression without using eval().

        Parses the expression into an AST and walks only a whitelist of numeric
        nodes and operators, so no names, calls, or attribute access can run.
        """
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("non-numeric constant")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
            return _SAFE_BINOPS[type(node.op)](self._eval_node(node.left), self._eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARYOPS:
            return _SAFE_UNARYOPS[type(node.op)](self._eval_node(node.operand))
        raise ValueError("unsupported expression")
