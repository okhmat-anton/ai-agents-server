import csv
import io
import statistics

def execute(text=None, file_path=None, operation="parse", columns=None, filter_expr=None, limit=100):
    """Parse, filter, and analyze CSV data."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        if columns:
            row = {k: v for k, v in row.items() if k in columns}
        rows.append(row)
    if operation == "stats":
        stats = {}
        all_cols = rows[0].keys() if rows else []
        for col in all_cols:
            vals = []
            for r in rows:
                try:
                    vals.append(float(r[col]))
                except (ValueError, TypeError):
                    pass
            if vals:
                stats[col] = {
                    "count": len(vals),
                    "mean": round(statistics.mean(vals), 4),
                    "min": min(vals),
                    "max": max(vals),
                    "sum": round(sum(vals), 4),
                }
                if len(vals) > 1:
                    stats[col]["stdev"] = round(statistics.stdev(vals), 4)
        return {"stats": stats, "total_rows": len(rows)}
    return {"rows": rows[:limit], "total_rows": len(rows), "columns": list(rows[0].keys()) if rows else []}
