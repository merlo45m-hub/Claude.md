#!/usr/bin/env python3
"""
Decision logging for fractional short positions.
Call write_decision_block() before any trade action.
Format: <thought> block with Logic, Risk, Confidence, Implementation Tip
"""
import datetime
import json
import os

DECISION_LOG = '/root/ai_stock_trader/decision_log.txt'

def write_decision_block(logic: str, risk: str, confidence: int, tip: str = ""):
    """Log a decision block with required format"""
    block = {
        "logic": logic,
        "risk": risk,
        "confidence": confidence,
        "tip": tip
    }
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(DECISION_LOG, 'a') as f:
        f.write(f"{timestamp} {json.dumps(block)}\n")

# Example usage (will be called by bot before trades):
# write_decision_block(
#     logic="SMA crossover confirms trend + RSI < 70 avoids overbought",
#     risk="Position size = 10% cash, fractional shares reduce slippage",
#     confidence=8,
#     tip="Monitor dashboard /api/decision for logged blocks"
# )