"""
Smart Risk / Alert logic.

Rules:
  crowd > 50 AND weapon_detected  →  CRITICAL  (Red)
  crowd > 50                      →  WARNING   (Yellow)
  crowd > 30                      →  WARNING   (Yellow)
  weapon_detected                 →  CRITICAL  (Red)
  else                            →  NORMAL    (Green)
"""

from typing import Dict, Any


def compute_risk(crowd_count: int, weapon_detected: bool, weapon_severity: str = "NONE") -> Dict[str, Any]:
    """
    Return risk assessment dict.
    """
    if crowd_count > 50 and weapon_detected:
        return {
            "risk_level": "CRITICAL",
            "stress_score": 100,
            "color": "red",
            "message": f"CRITICAL — {crowd_count} people + weapon detected!",
        }

    if weapon_detected and weapon_severity in ("EXTREME", "HIGH"):
        return {
            "risk_level": "CRITICAL",
            "stress_score": 100,
            "color": "red",
            "message": f"CRITICAL — Weapon detected ({weapon_severity})!",
        }

    if weapon_detected:
        return {
            "risk_level": "WARNING",
            "stress_score": 75,
            "color": "yellow",
            "message": f"WARNING — Possible weapon detected.",
        }

    if crowd_count > 50:
        return {
            "risk_level": "WARNING",
            "stress_score": 70,
            "color": "yellow",
            "message": f"WARNING — High crowd density ({crowd_count} people).",
        }

    if crowd_count > 30:
        return {
            "risk_level": "WARNING",
            "stress_score": 50,
            "color": "yellow",
            "message": f"WARNING — Elevated crowd ({crowd_count} people).",
        }

    return {
        "risk_level": "NORMAL",
        "stress_score": 0,
        "color": "green",
        "message": "Normal — All clear.",
    }
