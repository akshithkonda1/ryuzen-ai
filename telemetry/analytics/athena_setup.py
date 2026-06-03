"""Athena query helpers for Ryuzen Telemetry."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

athena_client = boto3.client("athena")

DATABASE = "ryuzen_telemetry"
OUTPUT_LOCATION = "s3://ryuzen-telemetry-athena-results/"

# Inputs are interpolated into Athena SQL, so they must be validated against a
# strict allowlist to prevent SQL injection. Model names are identifiers; month
# is an ISO year-month.
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,128}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _safe_model_name(model_name: str) -> str:
    if not _MODEL_NAME_RE.match(model_name or ""):
        raise ValueError(f"Invalid model_name: {model_name!r}")
    return model_name


def _safe_month(month: str) -> str:
    if not _MONTH_RE.match(month or ""):
        raise ValueError(f"Invalid month (expected YYYY-MM): {month!r}")
    return month


def _run_query(query: str) -> List[Dict[str, Any]]:
    try:
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": DATABASE},
            ResultConfiguration={"OutputLocation": OUTPUT_LOCATION},
        )
        execution_id = response.get("QueryExecutionId")
        result = athena_client.get_query_results(QueryExecutionId=execution_id)
        return [row["Data"] for row in result.get("ResultSet", {}).get("Rows", [])]
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - AWS failures
        logger.error("Athena query failed: %s", exc)
        raise


def model_performance_summary(model_name: str, month: str) -> List[Dict[str, Any]]:
    model_name = _safe_model_name(model_name)
    month = _safe_month(month)
    query = f"""
        SELECT category, avg(confidence_score) AS avg_confidence, avg(latency_ms) AS avg_latency
        FROM telemetry_events
        WHERE model_name = '{model_name}' AND month = '{month}'
        GROUP BY category
    """
    logger.info("Running model_performance_summary for %s %s", model_name, month)
    return _run_query(query)


def drift_detection(model_name: str, months_back: int) -> List[Dict[str, Any]]:
    model_name = _safe_model_name(model_name)
    months_back = int(months_back)
    query = f"""
        SELECT year, month, approx_distinct(drift_signature) AS drift_signatures
        FROM telemetry_events
        WHERE model_name = '{model_name}'
          AND date_parse(concat(year, '-', month, '-01'), '%Y-%m-%d') >= date_add('month', -{months_back}, current_timestamp)
        GROUP BY year, month
        ORDER BY year, month
    """
    logger.info("Running drift_detection for %s over %s months", model_name, months_back)
    return _run_query(query)


def disagreement_heatmap(month: str) -> List[Dict[str, Any]]:
    month = _safe_month(month)
    query = f"""
        SELECT model_name, disagreement_vector
        FROM telemetry_events
        WHERE month = '{month}'
    """
    logger.info("Running disagreement_heatmap for month %s", month)
    return _run_query(query)


def category_breakdown(model_name: str, month: str) -> List[Dict[str, Any]]:
    model_name = _safe_model_name(model_name)
    month = _safe_month(month)
    query = f"""
        SELECT category, count(*) as events
        FROM telemetry_events
        WHERE model_name = '{model_name}' AND month = '{month}'
        GROUP BY category
    """
    logger.info("Running category_breakdown for %s %s", model_name, month)
    return _run_query(query)


__all__ = [
    "model_performance_summary",
    "drift_detection",
    "disagreement_heatmap",
    "category_breakdown",
]
