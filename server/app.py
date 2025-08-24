import os
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok"
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
