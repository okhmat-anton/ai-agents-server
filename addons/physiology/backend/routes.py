"""
Human Physiology addon — backend routes.

Manages lab results, substance database, and medication-effect simulation
at the hormone / peptide / biochemical level.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from app.database import get_mongodb
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/addons/physiology",
    tags=["addon-physiology"],
    dependencies=[Depends(get_current_user)],
)

# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

LAB_RESULTS_COL = "physiology_lab_results"
PROFILES_COL = "physiology_profiles"
SUBSTANCES_COL = "physiology_substances"
SIMULATIONS_COL = "physiology_simulations"
META_COL = "physiology_meta"

# ---------------------------------------------------------------------------
# Reference ranges (adult, SI units) — seeded on first use
# ---------------------------------------------------------------------------

REFERENCE_RANGES = [
    # Hormones
    {"name": "Testosterone (total)", "category": "hormone", "unit": "nmol/L", "low": 8.64, "high": 29.0, "gender": "male"},
    {"name": "Testosterone (total)", "category": "hormone", "unit": "nmol/L", "low": 0.29, "high": 1.67, "gender": "female"},
    {"name": "Estradiol (E2)", "category": "hormone", "unit": "pmol/L", "low": 40, "high": 162, "gender": "male"},
    {"name": "Estradiol (E2)", "category": "hormone", "unit": "pmol/L", "low": 46, "high": 607, "gender": "female"},
    {"name": "Cortisol (morning)", "category": "hormone", "unit": "nmol/L", "low": 138, "high": 635},
    {"name": "TSH", "category": "hormone", "unit": "mIU/L", "low": 0.4, "high": 4.0},
    {"name": "Free T4", "category": "hormone", "unit": "pmol/L", "low": 12, "high": 22},
    {"name": "Free T3", "category": "hormone", "unit": "pmol/L", "low": 3.1, "high": 6.8},
    {"name": "Insulin (fasting)", "category": "hormone", "unit": "pmol/L", "low": 18, "high": 173},
    {"name": "Growth Hormone (GH)", "category": "hormone", "unit": "µg/L", "low": 0.0, "high": 8.0},
    {"name": "IGF-1", "category": "hormone", "unit": "nmol/L", "low": 10.5, "high": 41.8},
    {"name": "DHEA-S", "category": "hormone", "unit": "µmol/L", "low": 1.0, "high": 11.7, "gender": "male"},
    {"name": "DHEA-S", "category": "hormone", "unit": "µmol/L", "low": 0.9, "high": 11.0, "gender": "female"},
    {"name": "Prolactin", "category": "hormone", "unit": "mIU/L", "low": 86, "high": 324, "gender": "male"},
    {"name": "LH", "category": "hormone", "unit": "IU/L", "low": 1.7, "high": 8.6, "gender": "male"},
    {"name": "FSH", "category": "hormone", "unit": "IU/L", "low": 1.5, "high": 12.4, "gender": "male"},
    {"name": "Progesterone", "category": "hormone", "unit": "nmol/L", "low": 0.7, "high": 4.3, "gender": "male"},
    {"name": "Melatonin (night)", "category": "hormone", "unit": "pg/mL", "low": 40, "high": 160},
    {"name": "PTH", "category": "hormone", "unit": "pmol/L", "low": 1.6, "high": 6.9},
    {"name": "Aldosterone", "category": "hormone", "unit": "pmol/L", "low": 97, "high": 832},

    # Peptides & proteins
    {"name": "C-Reactive Protein (CRP)", "category": "peptide", "unit": "mg/L", "low": 0.0, "high": 5.0},
    {"name": "Ferritin", "category": "peptide", "unit": "µg/L", "low": 20, "high": 250, "gender": "male"},
    {"name": "Ferritin", "category": "peptide", "unit": "µg/L", "low": 10, "high": 120, "gender": "female"},
    {"name": "Hemoglobin", "category": "peptide", "unit": "g/L", "low": 130, "high": 175, "gender": "male"},
    {"name": "Hemoglobin", "category": "peptide", "unit": "g/L", "low": 120, "high": 160, "gender": "female"},
    {"name": "Albumin", "category": "peptide", "unit": "g/L", "low": 35, "high": 52},
    {"name": "Fibrinogen", "category": "peptide", "unit": "g/L", "low": 2.0, "high": 4.0},

    # Biochemistry
    {"name": "Glucose (fasting)", "category": "biochemistry", "unit": "mmol/L", "low": 3.9, "high": 5.6},
    {"name": "HbA1c", "category": "biochemistry", "unit": "%", "low": 4.0, "high": 5.6},
    {"name": "Total Cholesterol", "category": "biochemistry", "unit": "mmol/L", "low": 3.0, "high": 5.2},
    {"name": "LDL Cholesterol", "category": "biochemistry", "unit": "mmol/L", "low": 0.0, "high": 3.4},
    {"name": "HDL Cholesterol", "category": "biochemistry", "unit": "mmol/L", "low": 1.0, "high": 2.2},
    {"name": "Triglycerides", "category": "biochemistry", "unit": "mmol/L", "low": 0.0, "high": 1.7},
    {"name": "Creatinine", "category": "biochemistry", "unit": "µmol/L", "low": 62, "high": 106, "gender": "male"},
    {"name": "Creatinine", "category": "biochemistry", "unit": "µmol/L", "low": 44, "high": 80, "gender": "female"},
    {"name": "Urea", "category": "biochemistry", "unit": "mmol/L", "low": 2.5, "high": 7.1},
    {"name": "Uric Acid", "category": "biochemistry", "unit": "µmol/L", "low": 202, "high": 416, "gender": "male"},
    {"name": "ALT", "category": "biochemistry", "unit": "U/L", "low": 0, "high": 41},
    {"name": "AST", "category": "biochemistry", "unit": "U/L", "low": 0, "high": 40},
    {"name": "GGT", "category": "biochemistry", "unit": "U/L", "low": 0, "high": 60, "gender": "male"},
    {"name": "Bilirubin (total)", "category": "biochemistry", "unit": "µmol/L", "low": 3.4, "high": 20.5},
    {"name": "Alkaline Phosphatase", "category": "biochemistry", "unit": "U/L", "low": 40, "high": 130},

    # Vitamins & minerals
    {"name": "Vitamin D (25-OH)", "category": "vitamin", "unit": "nmol/L", "low": 50, "high": 125},
    {"name": "Vitamin B12", "category": "vitamin", "unit": "pmol/L", "low": 148, "high": 590},
    {"name": "Folate", "category": "vitamin", "unit": "nmol/L", "low": 7, "high": 45},
    {"name": "Iron", "category": "vitamin", "unit": "µmol/L", "low": 11, "high": 32, "gender": "male"},
    {"name": "Magnesium", "category": "vitamin", "unit": "mmol/L", "low": 0.66, "high": 1.07},
    {"name": "Calcium (total)", "category": "vitamin", "unit": "mmol/L", "low": 2.15, "high": 2.55},
    {"name": "Zinc", "category": "vitamin", "unit": "µmol/L", "low": 10.7, "high": 22.9},
    {"name": "Potassium", "category": "vitamin", "unit": "mmol/L", "low": 3.5, "high": 5.1},
    {"name": "Sodium", "category": "vitamin", "unit": "mmol/L", "low": 136, "high": 145},
    {"name": "Phosphate", "category": "vitamin", "unit": "mmol/L", "low": 0.87, "high": 1.45},
]

# Common substances affecting lab values
KNOWN_SUBSTANCES = [
    {"name": "Testosterone Cypionate", "category": "hormone_therapy", "effects": ["testosterone↑", "estradiol↑", "LH↓", "FSH↓", "hematocrit↑", "HDL↓"]},
    {"name": "Levothyroxine (T4)", "category": "hormone_therapy", "effects": ["free_T4↑", "TSH↓", "free_T3↑", "cholesterol↓"]},
    {"name": "Metformin", "category": "medication", "effects": ["glucose↓", "HbA1c↓", "insulin↓", "vitamin_B12↓"]},
    {"name": "Atorvastatin", "category": "medication", "effects": ["LDL↓", "total_cholesterol↓", "triglycerides↓", "ALT↑", "CK↑"]},
    {"name": "Prednisone", "category": "medication", "effects": ["cortisol↑", "glucose↑", "calcium↓", "immune_suppress"]},
    {"name": "Omeprazole", "category": "medication", "effects": ["vitamin_B12↓", "magnesium↓", "calcium_absorption↓"]},
    {"name": "Anastrozole", "category": "medication", "effects": ["estradiol↓", "testosterone↑_indirect"]},
    {"name": "Clomiphene", "category": "medication", "effects": ["LH↑", "FSH↑", "testosterone↑", "estradiol↑"]},
    {"name": "HCG", "category": "peptide_therapy", "effects": ["testosterone↑", "estradiol↑", "progesterone↑"]},
    {"name": "Ipamorelin", "category": "peptide_therapy", "effects": ["GH↑", "IGF-1↑", "sleep_quality↑"]},
    {"name": "BPC-157", "category": "peptide_therapy", "effects": ["healing↑", "GH↑_mild", "inflammation↓"]},
    {"name": "Sermorelin", "category": "peptide_therapy", "effects": ["GH↑", "IGF-1↑"]},
    {"name": "PT-141 (Bremelanotide)", "category": "peptide_therapy", "effects": ["libido↑", "melanocortin_activation"]},
    {"name": "TB-500 (Thymosin Beta-4)", "category": "peptide_therapy", "effects": ["healing↑", "inflammation↓", "flexibility↑"]},
    {"name": "Melatonin", "category": "supplement", "effects": ["melatonin↑", "sleep_quality↑", "cortisol↓_mild"]},
    {"name": "DHEA", "category": "supplement", "effects": ["DHEA-S↑", "testosterone↑_mild", "estradiol↑_mild"]},
    {"name": "Vitamin D3", "category": "supplement", "effects": ["vitamin_D↑", "calcium_absorption↑", "PTH↓"]},
    {"name": "Zinc", "category": "supplement", "effects": ["zinc↑", "testosterone↑_mild", "immune↑"]},
    {"name": "Magnesium", "category": "supplement", "effects": ["magnesium↑", "sleep_quality↑", "cortisol↓_mild"]},
    {"name": "Ashwagandha", "category": "supplement", "effects": ["cortisol↓", "testosterone↑_mild", "stress↓"]},
    {"name": "Finasteride", "category": "medication", "effects": ["DHT↓", "testosterone↑_mild", "estradiol↑_mild"]},
    {"name": "Lisinopril", "category": "medication", "effects": ["aldosterone↓", "potassium↑", "creatinine↑_mild"]},
]


# ---------------------------------------------------------------------------
# 1. PROFILES — user health profiles
# ---------------------------------------------------------------------------

@router.get("/profiles")
async def list_profiles():
    db = get_mongodb()
    items = []
    async for doc in db[PROFILES_COL].find().sort("created_at", -1):
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/profiles")
async def create_profile(body: dict):
    db = get_mongodb()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Profile name required")

    doc = {
        "name": name,
        "gender": body.get("gender", "male"),
        "age": body.get("age", 30),
        "weight_kg": body.get("weight_kg"),
        "height_cm": body.get("height_cm"),
        "notes": body.get("notes", ""),
        "current_medications": body.get("current_medications", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[PROFILES_COL].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.patch("/profiles/{profile_id}")
async def update_profile(profile_id: str, body: dict):
    from bson import ObjectId
    db = get_mongodb()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("_id", None)
    await db[PROFILES_COL].update_one({"_id": ObjectId(profile_id)}, {"$set": body})
    return {"ok": True}


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[PROFILES_COL].delete_one({"_id": ObjectId(profile_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 2. LAB RESULTS
# ---------------------------------------------------------------------------

@router.get("/lab-results")
async def list_lab_results(
    profile_id: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    db = get_mongodb()
    query = {}
    if profile_id:
        query["profile_id"] = profile_id

    items = []
    async for doc in db[LAB_RESULTS_COL].find(query).sort("test_date", -1).limit(limit):
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    total = await db[LAB_RESULTS_COL].count_documents(query)
    return {"items": items, "total": total}


@router.post("/lab-results")
async def create_lab_result(body: dict):
    db = get_mongodb()
    profile_id = body.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Profile ID required")

    # Process values and flag out-of-range
    values = body.get("values", [])
    flagged = []
    for v in values:
        # Find reference range
        for ref in REFERENCE_RANGES:
            if ref["name"].lower() == v.get("name", "").lower():
                val = v.get("value")
                if val is not None:
                    try:
                        val = float(val)
                        if val < ref["low"]:
                            v["flag"] = "low"
                            flagged.append(v["name"])
                        elif val > ref["high"]:
                            v["flag"] = "high"
                            flagged.append(v["name"])
                        else:
                            v["flag"] = "normal"
                        v["ref_low"] = ref["low"]
                        v["ref_high"] = ref["high"]
                        v["unit"] = ref["unit"]
                    except (ValueError, TypeError):
                        pass
                break

    doc = {
        "profile_id": profile_id,
        "test_date": body.get("test_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "lab_name": body.get("lab_name", ""),
        "values": values,
        "flagged_count": len(flagged),
        "flagged_markers": flagged,
        "notes": body.get("notes", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[LAB_RESULTS_COL].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.delete("/lab-results/{result_id}")
async def delete_lab_result(result_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[LAB_RESULTS_COL].delete_one({"_id": ObjectId(result_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 3. SUBSTANCES — reference database
# ---------------------------------------------------------------------------

@router.get("/substances")
async def list_substances(category: Optional[str] = None):
    db = get_mongodb()
    query = {}
    if category:
        query["category"] = category

    items = []
    count = await db[SUBSTANCES_COL].count_documents({})
    if count == 0:
        # Seed from known substances
        for s in KNOWN_SUBSTANCES:
            s["created_at"] = datetime.now(timezone.utc).isoformat()
        await db[SUBSTANCES_COL].insert_many([dict(s) for s in KNOWN_SUBSTANCES])

    async for doc in db[SUBSTANCES_COL].find(query).sort("name", 1):
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


@router.post("/substances")
async def create_substance(body: dict):
    db = get_mongodb()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Substance name required")

    doc = {
        "name": name,
        "category": body.get("category", "other"),
        "effects": body.get("effects", []),
        "description": body.get("description", ""),
        "half_life": body.get("half_life", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[SUBSTANCES_COL].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.delete("/substances/{substance_id}")
async def delete_substance(substance_id: str):
    from bson import ObjectId
    db = get_mongodb()
    await db[SUBSTANCES_COL].delete_one({"_id": ObjectId(substance_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# 4. REFERENCE RANGES
# ---------------------------------------------------------------------------

@router.get("/reference-ranges")
async def get_reference_ranges(category: Optional[str] = None, gender: Optional[str] = None):
    """Get reference ranges, optionally filtered."""
    items = REFERENCE_RANGES
    if category:
        items = [r for r in items if r["category"] == category]
    if gender:
        items = [r for r in items if r.get("gender") in (None, gender)]
    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# 5. SIMULATION — predict effects of medication
# ---------------------------------------------------------------------------

@router.post("/simulate")
async def simulate_medication(body: dict):
    """
    Simulate the effect of introducing a substance given current lab values.
    Uses rule-based approach + returns structured predictions.
    """
    db = get_mongodb()
    substance_name = body.get("substance_name", "").strip()
    profile_id = body.get("profile_id")
    dosage = body.get("dosage", "")

    if not substance_name:
        raise HTTPException(status_code=400, detail="Substance name required")

    # Find substance
    substance = await db[SUBSTANCES_COL].find_one({"name": {"$regex": substance_name, "$options": "i"}})
    if not substance:
        # Check known substances
        substance = next((s for s in KNOWN_SUBSTANCES if s["name"].lower() == substance_name.lower()), None)

    effects = substance.get("effects", []) if substance else []

    # Get latest lab results for reference
    latest_labs = None
    if profile_id:
        latest_labs = await db[LAB_RESULTS_COL].find_one(
            {"profile_id": profile_id},
            sort=[("test_date", -1)],
        )

    # Build predictions
    predictions = []
    for effect in effects:
        direction = "increase" if "↑" in effect else "decrease" if "↓" in effect else "change"
        marker = effect.replace("↑", "").replace("↓", "").replace("_mild", "").replace("_indirect", "").strip()

        # Find current value if we have labs
        current_value = None
        if latest_labs:
            for v in latest_labs.get("values", []):
                if marker.lower() in v.get("name", "").lower():
                    current_value = v.get("value")
                    break

        predictions.append({
            "marker": marker,
            "direction": direction,
            "confidence": "moderate" if "_mild" in effect else "high",
            "current_value": current_value,
            "effect_raw": effect,
        })

    # Store simulation
    sim_doc = {
        "profile_id": profile_id,
        "substance_name": substance_name,
        "dosage": dosage,
        "predictions": predictions,
        "effects_count": len(predictions),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db[SIMULATIONS_COL].insert_one(sim_doc)
    sim_doc["_id"] = str(result.inserted_id)

    return sim_doc


@router.get("/simulations")
async def list_simulations(profile_id: Optional[str] = None, limit: int = Query(50, le=200)):
    db = get_mongodb()
    query = {}
    if profile_id:
        query["profile_id"] = profile_id

    items = []
    async for doc in db[SIMULATIONS_COL].find(query).sort("created_at", -1).limit(limit):
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return {"items": items}


# ---------------------------------------------------------------------------
# 6. STATS & CLEAR
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats():
    db = get_mongodb()
    profiles = await db[PROFILES_COL].count_documents({})
    results = await db[LAB_RESULTS_COL].count_documents({})
    substances = await db[SUBSTANCES_COL].count_documents({})
    simulations = await db[SIMULATIONS_COL].count_documents({})
    return {
        "profiles": profiles,
        "lab_results": results,
        "substances": substances,
        "simulations": simulations,
        "reference_ranges": len(REFERENCE_RANGES),
    }


@router.delete("/clear")
async def clear_all():
    db = get_mongodb()
    r1 = await db[LAB_RESULTS_COL].delete_many({})
    r2 = await db[PROFILES_COL].delete_many({})
    r3 = await db[SUBSTANCES_COL].delete_many({})
    r4 = await db[SIMULATIONS_COL].delete_many({})
    return {
        "deleted_lab_results": r1.deleted_count,
        "deleted_profiles": r2.deleted_count,
        "deleted_substances": r3.deleted_count,
        "deleted_simulations": r4.deleted_count,
    }
