
from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import os

app = Flask(__name__)

PRESENTS_FILE = os.path.join(os.path.dirname(__file__), "presents.txt")


def load_presents():
    """Load presents from CSV. Supports files with 2 or 3 columns.
    Returns a list of dicts: { 'name': str, 'link': str, 'bought': bool }
    """
    presents = []
    if not os.path.exists(PRESENTS_FILE):
        return presents
    with open(PRESENTS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            name = row[0].strip() if len(row) > 0 else ""
            link = row[1].strip() if len(row) > 1 else ""
            bought_raw = row[2].strip().lower() if len(row) > 2 else "false"
            bought = bought_raw in ("1", "true", "yes", "y", "ja")
            presents.append({"name": name, "link": link, "bought": bought})
    return presents


def save_presents(presents):
    """Write presents back to CSV with header Name,Link,Bought."""
    with open(PRESENTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Link", "Bought"])
        for p in presents:
            writer.writerow([p.get("name", ""), p.get("link", ""), "true" if p.get("bought") else "false"])


@app.route("/", methods=["GET"])
def index():
    presents = load_presents()
    return render_template("index.html", title="Cadeaulijstje 2025", presents=presents)


@app.route("/update", methods=["POST"])
def update():
    presents = load_presents()
    checked_indices = set()
    for value in request.form.getlist("bought"):
        try:
            checked_indices.add(int(value))
        except ValueError:
            continue
    for idx, present in enumerate(presents):
        present["bought"] = idx in checked_indices
    save_presents(presents)
    return redirect(url_for("index"))


@app.route("/toggle", methods=["POST"])
def toggle():
    """Toggle a single present's bought state based on index and checked flag."""
    presents = load_presents()
    try:
        idx = int(request.form.get("index", "-1"))
        checked_raw = request.form.get("checked", "false").lower()
        checked = checked_raw in ("1", "true", "yes", "y", "on")
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    if idx < 0 or idx >= len(presents):
        return jsonify({"ok": False, "error": "index_out_of_range"}), 400

    presents[idx]["bought"] = checked
    save_presents(presents)

    bought_count = sum(1 for p in presents if p.get("bought"))
    total = len(presents)
    return jsonify({"ok": True, "boughtCount": bought_count, "total": total})


if __name__ == "__main__":
    app.run(debug=True)
