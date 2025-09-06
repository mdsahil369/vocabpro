import json, os, re, random, time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, abort

APP_DIR = Path(__file__).parent.resolve()
DATA_DIR = APP_DIR / "data"
VOCAB_FILE = DATA_DIR / "vocab.json"
RESULTS_FILE = DATA_DIR / "results.json"
CONFIG_FILE = DATA_DIR / "config.json"

def load_vocab():
    with open("data/vocab.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def normalize_pos(s: str) -> str:
    if not s:
        return ""
    t = s.strip().lower().replace(".", "")
    mapping = {
        "n": "n.", "noun": "n.",
        "v": "v.", "verb": "v.",
        "adj": "adj.", "adjective": "adj.",
        "adv": "adv.", "adverb": "adv.",
        "pron": "pron.", "pronoun": "pron.",
        "prep": "prep.", "preposition": "prep.",
        "conj": "conj.", "conjunction": "conj.",
        "interj": "interj.", "interjection": "interj."
    }
    return mapping.get(t, s.strip()) if t not in mapping else mapping[t]

def canon(s: str) -> str:
    # For comparing user English word answers (case/space insensitive)
    return re.sub(r"\s+", " ", s.strip().lower())

def next_vocab_id(items):
    return (max((i.get("id", 0) for i in items), default=0) + 1) if items else 1

def parse_bulk(text: str):
    """
    Parse lines like:
      Put (v.) – রাখা
      Brave (adj.) - সাহসী
    Returns list of dicts {word, pos, meaning}
    """
    results = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Accept -, –, — as separator between word section and meaning
        # Pattern: EnglishWord (pos) SEP BanglaMeaning
        m = re.match(r"^\s*([A-Za-z\-\' ]+)\s*\(([^)]+)\)\s*[-–—]\s*(.+)$", line)
        if not m:
            # Try looser: EnglishWord SEP BanglaMeaning (no POS)
            m2 = re.match(r"^\s*([A-Za-z\-\' ]+)\s*[-–—]\s*(.+)$", line)
            if m2:
                word = m2.group(1).strip()
                pos = ""
                meaning = m2.group(2).strip()
                results.append({"word": word, "pos": pos, "meaning": meaning})
            continue
        word = m.group(1).strip()
        pos = normalize_pos(m.group(2))
        meaning = m.group(3).strip()
        results.append({"word": word, "pos": pos, "meaning": meaning})
    return results

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

@app.context_processor
def inject_now():
    return {"now_ts": int(time.time())}

def require_admin():
    if not session.get("is_admin"):
        abort(403)

# ------------- Routes (Public) -------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/learn/start", methods=["GET", "POST"])
def learn_start():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "Guest"
        # Create a quiz seed; front-end will fetch vocab and shuffle
        session["quiz_user_name"] = name
        session["quiz_started_at"] = datetime.now(timezone.utc).isoformat()
        return redirect(url_for("quiz"))
    return render_template("user_start.html")

@app.route("/learn/quiz")
def quiz():
    # 12 minutes timer on client
    name = session.get("quiz_user_name", "Guest")
    started = session.get("quiz_started_at")
    return render_template("quiz.html", name=name, started_at=started)

@app.post("/learn/finish")
def learn_finish():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    name = session.get("quiz_user_name", "Guest")
    started_at = session.get("quiz_started_at")
    ended_at = datetime.now(timezone.utc).isoformat()

    # Score calculation
    correct_pos = sum(1 for x in items if x.get("is_pos_correct"))
    correct_word = sum(1 for x in items if x.get("is_word_correct"))
    total_questions = len(items)
    score = (correct_pos * 0.5) + (correct_word * 0.5)
    record = {
        "id": int(datetime.now().timestamp()*1000),
        "name": name,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": 12*60,  # fixed timer
        "total_questions": total_questions,
        "answered": sum(1 for x in items if (x.get("user_pos") or x.get("user_word"))),
        "correct_pos": correct_pos,
        "correct_word": correct_word,
        "score": score,
        "items": items,
    }
    results = load_json(RESULTS_FILE, [])
    results.append(record)
    save_json(RESULTS_FILE, results)
    # Also show results page
    return jsonify({"ok": True, "redirect": url_for("results_page", attempt_id=record["id"])}), 200

@app.route("/results/<int:attempt_id>")
def results_page(attempt_id):
    results = load_json(RESULTS_FILE, [])
    rec = next((r for r in results if r["id"] == attempt_id), None)
    if not rec:
        return "Result not found", 404
    return render_template("results.html", rec=rec)


@app.get("/api/vocab")
def api_vocab():
    vocab = load_json(VOCAB_FILE, [])
    return jsonify(vocab)

# ------------- Routes (Admin) -------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        cfg = load_json(CONFIG_FILE, {"admin_username": "admin", "admin_password": "changeme"})
        if username == cfg.get("admin_username") and password == cfg.get("admin_password"):
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.get("/admin")
def admin_dashboard():
    require_admin()
    vocab = load_json(VOCAB_FILE, [])
    results = load_json(RESULTS_FILE, [])
    return render_template("admin_dashboard.html", vocab_count=len(vocab), attempts=len(results))

@app.route("/admin/vocab", methods=["GET", "POST"])
def admin_vocab():
    require_admin()
    vocab = load_json(VOCAB_FILE, [])
    if request.method == "POST":
        word = request.form.get("word", "").strip()
        pos = normalize_pos(request.form.get("pos", ""))
        meaning = request.form.get("meaning", "").strip()
        if not word or not meaning:
            flash("Word and meaning are required.", "error")
        else:
            # avoid duplicates (same word + meaning)
            for v in vocab:
                if canon(v["word"]) == canon(word) and v["meaning"] == meaning:
                    flash("Duplicate entry skipped.", "warning")
                    break
            else:
                vocab.append({"id": next_vocab_id(vocab), "word": word, "pos": pos, "meaning": meaning})
                save_json(VOCAB_FILE, vocab)
                flash("Word added.", "success")
        return redirect(url_for("admin_vocab"))
    return render_template("admin_vocab.html", vocab=vocab)

@app.post("/admin/vocab/<int:item_id>/delete")
def admin_vocab_delete(item_id):
    require_admin()
    vocab = load_json(VOCAB_FILE, [])
    vocab = [v for v in vocab if v.get("id") != item_id]
    save_json(VOCAB_FILE, vocab)
    flash("Deleted.", "success")
    return redirect(url_for("admin_vocab"))

@app.post("/admin/vocab/<int:item_id>/update")
def admin_vocab_update(item_id):
    require_admin()
    vocab = load_json(VOCAB_FILE, [])
    for v in vocab:
        if v.get("id") == item_id:
            v["word"] = request.form.get("word", v["word"]).strip()
            v["pos"] = normalize_pos(request.form.get("pos", v["pos"]))
            v["meaning"] = request.form.get("meaning", v["meaning"]).strip()
            break
    save_json(VOCAB_FILE, vocab)
    flash("Updated.", "success")
    return redirect(url_for("admin_vocab"))

@app.route("/admin/bulk", methods=["GET", "POST"])
def admin_bulk():
    require_admin()
    preview = []
    if request.method == "POST":
        text = request.form.get("bulk_text", "")
        parsed = parse_bulk(text)
        # Accept maximum 50 lines at a time
        preview = parsed[:50]
        if "confirm" in request.form:
            vocab = load_json(VOCAB_FILE, [])
            existing = {(canon(v["word"]), v["meaning"]) for v in vocab}
            for item in preview:
                key = (canon(item["word"]), item["meaning"])
                if key in existing:
                    continue
                vocab.append({
                    "id": next_vocab_id(vocab),
                    "word": item["word"].strip(),
                    "pos": normalize_pos(item.get("pos", "")),
                    "meaning": item["meaning"].strip()
                })
            save_json(VOCAB_FILE, vocab)
            flash(f"Imported {len(preview)} items.", "success")
            return redirect(url_for("admin_vocab"))
        elif parsed and not preview:
            flash("Nothing to import.", "warning")
    return render_template("admin_upload.html", preview=preview)

@app.get("/admin/results")
def admin_results():
    require_admin()
    results = load_json(RESULTS_FILE, [])
    # newest first
    results.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return render_template("admin_results.html", results=results)

@app.route("/exam")
def exam_page():
    return render_template("exam.html")


@app.route("/get_questions")
def get_questions():
    import random
    vocab = load_json(VOCAB_FILE, [])
    random.shuffle(vocab)  # shuffle server-side to prevent mismatch
    questions = []
    for idx, q in enumerate(vocab):
        questions.append({
            "id": idx,          # unique ID after shuffle
            "word": q["word"],
            "pos": q["pos"],
            "meaning": q["meaning"]
        })
    return jsonify({"questions": questions})






@app.route("/submit_exam", methods=["POST"])
def submit_exam():
    data = request.get_json()
    answers = data.get("answers", {})
    vocab = load_json(VOCAB_FILE, [])

    score = 0
    correct_word = 0
    correct_pos = 0
    items = []

    # Make vocab lookup by word
    vocab_lookup = {v["word"]: v for v in vocab}

    for word, ans in answers.items():
        q = vocab_lookup.get(word)
        if not q:
            continue

        user_word = ans.get("english", "").strip().lower()
        user_pos = ans.get("pos", "").strip().lower().replace(".", "")
        correct_word_val = q["word"].strip().lower()
        correct_pos_val = q["pos"].strip().lower().replace(".", "")

        is_word_correct = user_word == correct_word_val
        is_pos_correct = user_pos == correct_pos_val

        if is_word_correct:
            correct_word += 1
            score += 0.5
        if is_pos_correct:
            correct_pos += 1
            score += 0.5

        items.append({
            "user_word": ans.get("english",""),
            "user_pos": ans.get("pos",""),
            "word": q["word"],
            "pos": q["pos"],
            "meaning": q["meaning"],
            "is_word_correct": is_word_correct,
            "is_pos_correct": is_pos_correct
        })

    record = {
        "id": int(datetime.now().timestamp()*1000),
        "name": session.get("quiz_user_name", "Guest"),
        "started_at": session.get("quiz_started_at", datetime.now(timezone.utc).isoformat()),  # <-- ADD THIS
        "score": score,
        "total_questions": len(answers),
        "correct_word": correct_word,
        "correct_pos": correct_pos,
        "items": items,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


    results = load_json(RESULTS_FILE, [])
    results.append(record)
    save_json(RESULTS_FILE, results)

    return jsonify({"score": score, "total": len(answers)})

@app.route("/admin/results/<int:attempt_id>/delete", methods=["POST"], endpoint="admin_results_delete")
def admin_results_delete(attempt_id):
    require_admin()
    results = load_json(RESULTS_FILE, [])
    results = [r for r in results if r.get("id") != attempt_id]
    save_json(RESULTS_FILE, results)
    flash("Attempt deleted successfully.", "success")
    return redirect(url_for("admin_results"))



# This is prectice section for anything Start

# /////////////////////////////////////////////////////////////////////////////////////

# This is prectice section for anything End





# ------------- Templates & Static -------------
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"),"vocabpro.png", mimetype="image/png")


if __name__ == "__main__":
    # Ensure data dir exists
    os.makedirs(DATA_DIR, exist_ok=True)
    # Create default files if missing
    if not VOCAB_FILE.exists():
        save_json(VOCAB_FILE, [])
    if not RESULTS_FILE.exists():
        save_json(RESULTS_FILE, [])
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, {"admin_username":"admin","admin_password":"changeme"})
    app.run(debug=True)
