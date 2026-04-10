from flask import Flask, jsonify


app = Flask(__name__)


@app.get("/")
def root() -> tuple[dict[str, str], int]:
    return jsonify({"status": "ok", "message": "Flask smoke app is running"}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
