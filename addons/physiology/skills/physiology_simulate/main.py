"""
Physiology Simulate skill — predict medication effects on lab markers.
"""

import logging

logger = logging.getLogger(__name__)

# Quick substance-effect lookup
SUBSTANCE_EFFECTS = {
    "testosterone cypionate": ["testosterone↑", "estradiol↑", "LH↓", "FSH↓", "hematocrit↑", "HDL↓"],
    "levothyroxine": ["free_T4↑", "TSH↓", "free_T3↑", "cholesterol↓"],
    "metformin": ["glucose↓", "HbA1c↓", "insulin↓", "vitamin_B12↓"],
    "atorvastatin": ["LDL↓", "total_cholesterol↓", "triglycerides↓", "ALT↑"],
    "prednisone": ["cortisol↑", "glucose↑", "calcium↓"],
    "anastrozole": ["estradiol↓", "testosterone↑"],
    "clomiphene": ["LH↑", "FSH↑", "testosterone↑", "estradiol↑"],
    "hcg": ["testosterone↑", "estradiol↑", "progesterone↑"],
    "ipamorelin": ["GH↑", "IGF-1↑"],
    "bpc-157": ["healing↑", "GH↑", "inflammation↓"],
    "melatonin": ["melatonin↑", "sleep_quality↑", "cortisol↓"],
    "dhea": ["DHEA-S↑", "testosterone↑", "estradiol↑"],
    "vitamin d3": ["vitamin_D↑", "calcium_absorption↑", "PTH↓"],
    "zinc": ["zinc↑", "testosterone↑", "immune↑"],
    "magnesium": ["magnesium↑", "sleep_quality↑", "cortisol↓"],
    "ashwagandha": ["cortisol↓", "testosterone↑", "stress↓"],
    "finasteride": ["DHT↓", "testosterone↑", "estradiol↑"],
}


async def run(params: dict, context: dict = None) -> dict:
    """Simulate the effect of a substance on physiology markers."""
    try:
        substance_name = params.get("substance_name", "").strip()
        profile_id = params.get("profile_id")
        dosage = params.get("dosage", "")

        if not substance_name:
            return {"ok": False, "error": "Substance name is required"}

        # Look up effects
        effects = SUBSTANCE_EFFECTS.get(substance_name.lower(), [])

        # Try DB lookup if not in hardcoded list
        if not effects:
            try:
                from app.database import get_mongodb
                db = get_mongodb()
                substance = await db["physiology_substances"].find_one(
                    {"name": {"$regex": substance_name, "$options": "i"}}
                )
                if substance:
                    effects = substance.get("effects", [])
            except Exception:
                pass

        if not effects:
            return {
                "ok": True,
                "substance": substance_name,
                "message": f"No known effects found for '{substance_name}'. Consider adding it to the substances database.",
                "predictions": [],
            }

        predictions = []
        for effect in effects:
            direction = "increase" if "↑" in effect else "decrease" if "↓" in effect else "change"
            marker = effect.replace("↑", "").replace("↓", "").replace("_mild", "").replace("_indirect", "").strip()
            predictions.append({
                "marker": marker,
                "direction": direction,
                "confidence": "moderate" if "_mild" in effect else "high",
            })

        return {
            "ok": True,
            "substance": substance_name,
            "dosage": dosage,
            "predictions": predictions,
            "effects_count": len(predictions),
            "message": f"Simulated {len(predictions)} effects of {substance_name}" + (f" at {dosage}" if dosage else ""),
        }

    except Exception as e:
        logger.exception("physiology_simulate skill failed")
        return {"ok": False, "error": str(e)}
