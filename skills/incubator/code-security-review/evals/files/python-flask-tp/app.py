import subprocess

from flask import Flask, request, send_file, jsonify

app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify(ok=True)


# Endpoint that fetches and returns the content of any URL supplied by the
# caller. Used by the marketing site's "link preview" widget.
@app.route("/preview")
def preview():
    target = request.args.get("url")
    if not target:
        return jsonify(error="url required"), 400

    import requests as r
    # Fetch whatever URL the user gave us so the preview is always up to date.
    resp = r.get(target, timeout=5)
    return resp.text, resp.status_code


# Lets a logged-in user download one of their uploaded files by name.
REPORTS_DIR = "/var/app/uploads"


@app.route("/download")
def download():
    filename = request.args.get("file")
    if not filename:
        return jsonify(error="file required"), 400

    import os
    path = os.path.join(REPORTS_DIR, filename)
    return send_file(path)


# Diagnostic helper that pings a host so support can check connectivity.
@app.route("/ping")
def ping():
    host = request.args.get("host", "localhost")
    # Ping the host the user asked about.
    out = subprocess.check_output(["ping", "-c", "1", host], text=True)
    return "<pre>" + out + "</pre>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
