import math
import statistics as stat_mod

def execute(expression, operation="eval", data=None):
    """Evaluate math expressions safely. Supports arithmetic, trig, log, statistics."""
    if operation == "statistics" and data:
        result = {
            "count": len(data),
            "sum": sum(data),
            "mean": round(stat_mod.mean(data), 6),
            "median": round(stat_mod.median(data), 6),
            "min": min(data),
            "max": max(data),
        }
        if len(data) > 1:
            result["stdev"] = round(stat_mod.stdev(data), 6)
            result["variance"] = round(stat_mod.variance(data), 6)
        return {"result": result}
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "int": int, "float": float, "pow": pow, "len": len,
        "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf,
        "sqrt": math.sqrt, "cbrt": lambda x: x ** (1/3),
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
        "log": math.log, "log2": math.log2, "log10": math.log10,
        "exp": math.exp, "ceil": math.ceil, "floor": math.floor,
        "factorial": math.factorial, "gcd": math.gcd,
        "radians": math.radians, "degrees": math.degrees,
        "hypot": math.hypot, "isnan": math.isnan, "isinf": math.isinf,
    }
    try:
        code = compile(expression, "<math>", "eval")
        for name in code.co_names:
            if name not in allowed_names:
                return {"error": f"Function or variable not allowed: {name}"}
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": result}
    except Exception as exc:
        return {"error": str(exc), "expression": expression}
