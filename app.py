from flask import Flask, render_template, request, jsonify
import subprocess
import json
import random
import os
from datetime import datetime

app = Flask(__name__)

# === MEMORY FUNCTIONS ===
def load_memory():
    try:
        with open("memory.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[MEMORY LOAD ERROR]", e)
        return {}

def save_memory(memory):
    with open("memory.json", "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

# === CHAT HISTORY FUNCTIONS ===
def load_history():
    try:
        with open("chat_history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[HISTORY LOAD ERROR]", e)
        return []

def save_history(history):
    with open("chat_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

# === JOURNALING FUNCTION ===
def save_to_journal(entry):
    try:
        if not os.path.exists("journal.json"):
            journal = []
        else:
            with open("journal.json", "r", encoding="utf-8") as f:
                journal = json.load(f)
                if not isinstance(journal, list):
                    raise ValueError("journal.json must be a list")

        journal.append(entry)

        with open("journal.json", "w", encoding="utf-8") as f:
            json.dump(journal, f, indent=2)

    except Exception as e:
        print("[JOURNAL SAVE ERROR]", e)

# === ROUTES ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("message", "")
    memory = load_memory()
    memory_facts = memory.get("memories", [])

    moods = ["chill", "curious", "goofy", "snarky", "gentle"]
    mood = random.choice(moods)

    prompt = f"""You are Nova, a witty AI companion with a {mood} tone.
Speak casually and like a real person—brief, unpredictable, informal. Don’t overexplain.

You remember the following facts:
{chr(10).join(memory_facts)}

Only mention memories if the user brings them up first.
If the user says "hello" and it's the first message after a long time, make your greeting extra warm.
Otherwise, keep greetings casual and mood-driven.

User: {user_input}
Nova:"""

    try:
        result = subprocess.run(
            ["ollama", "run", "nova", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.stderr:
            print("[MODEL STDERR]", result.stderr)

        raw_output = result.stdout.strip()
        print("Nova's raw output:\n", raw_output)

        lines = raw_output.split("\n")
        response_lines = [line for line in lines if not line.strip().startswith(">>>")]
        reply = "\n".join(response_lines).strip() or "I'm here, but something glitched—try asking me again?"

        history = load_history()
        history.append({"user": user_input, "nova": reply})
        save_history(history[-50:])

        save_to_journal({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "nova": reply
        })

        if "remember that" in user_input.lower():
            memory.setdefault("memories", []).append(user_input)
            save_memory(memory)

        # Voice synthesis removed (TTS disabled)

        return jsonify({"response": reply})

    except Exception as e:
        print("[ASK ROUTE ERROR]", e)
        return jsonify({"response": f"Nova hit a snag: {str(e)}"})

@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(load_history())

@app.route("/clear-history", methods=["POST"])
def clear_history():
    save_history([])
    return jsonify({"status": "History cleared"})

@app.route("/view-history")
def view_history():
    return render_template("history.html")

@app.route("/journal", methods=["GET"])
def view_journal():
    try:
        with open("journal.json", "r", encoding="utf-8") as f:
            journal = json.load(f)
            return jsonify(journal if isinstance(journal, list) else [])
    except Exception as e:
        print("[VIEW JOURNAL ERROR]", e)
        return jsonify([])

@app.route("/summarize-journal", methods=["GET"])
def summarize_journal():
    try:
        with open("journal.json", "r", encoding="utf-8") as f:
            journal = json.load(f)

        if not isinstance(journal, list) or len(journal) < 2:
            return jsonify({"summary": "Not enough entries to summarize just yet."})

        convo_text = "\n".join(
            f"User: {entry['user']}\nNova: {entry['nova']}" for entry in journal[-10:]
        )

        summary_prompt = f"Summarize the following conversation between Franz and Nova:\n{convo_text}\nSummary:"

        result = subprocess.run(
            ["ollama", "run", "nova", summary_prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.stderr:
            print("[SUMMARY STDERR]", result.stderr)

        summary = result.stdout.strip()
        return jsonify({"summary": summary or "Something went blank—try again."})

    except Exception as e:
        print("[SUMMARY ERROR]", e)
        return jsonify({"error": str(e)})

# App Startup
if __name__ == "__main__":
    print("🚀 Nova is booting u11p on http://192.168.1.10:5000/ (accessible on your local network)")
    app.run(host="0.0.0.0", port=5000, debug=True)