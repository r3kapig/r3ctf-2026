
import os, json, hashlib
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "questions_data.json"), "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]
HASHED_ANSWERS = DATA["hashed_answers"]
SPECIAL_AFTER = DATA["special_message_after"]  # 1-indexed question number after which to show msg
SPECIAL_MSG = DATA["special_message"]
TOTAL = len(QUESTIONS)

FLAG = os.environ.get("FLAG", "flag{this_is_a_dummy_flag_for_testing}")
with open("/flag", "w") as f:
    f.write(FLAG)


def norm(s: str) -> str:
    return s.strip()


def check_answer(idx: int, submitted: str) -> bool:
    h = hashlib.sha256(norm(submitted).encode()).hexdigest()
    return h == HASHED_ANSWERS[idx]


@app.route("/")
def index():
    if "solved" not in session:
        session["solved"] = 0
    return render_template("index.html")


@app.route("/api/state")
def state():
    solved = session.get("solved", 0)
    if solved >= TOTAL:
        return jsonify({
            "finished": True,
            "solved": solved,
            "total": TOTAL
        })
    return jsonify({
        "finished": False,
        "solved": solved,
        "total": TOTAL,
        "question_number": solved + 1,
        "question_text": QUESTIONS[solved]
    })


@app.route("/api/submit", methods=["POST"])
def submit():
    solved = session.get("solved", 0)
    if solved >= TOTAL:
        return jsonify({"finished": True, "flag": FLAG})

    payload = request.get_json(force=True, silent=True) or {}
    answer = payload.get("answer", "")

    if not isinstance(answer, str) or not answer:
        return jsonify({"correct": False, "message": "Answer cannot be empty"})

    if check_answer(solved, answer):
        solved += 1
        session["solved"] = solved

        special_message = None
        if solved == SPECIAL_AFTER and solved < TOTAL:
            special_message = SPECIAL_MSG

        if solved >= TOTAL:
            return jsonify({
                "correct": True,
                "finished": True,
                "flag": FLAG,
                "special_message": special_message
            })
        else:
            return jsonify({
                "correct": True,
                "finished": False,
                "solved": solved,
                "total": TOTAL,
                "question_number": solved + 1,
                "question_text": QUESTIONS[solved],
                "special_message": special_message
            })
    else:
        return jsonify({"correct": False, "message": "Wrong Answer"})


@app.route("/api/reset", methods=["POST"])
def reset():
    session["solved"] = 0
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
