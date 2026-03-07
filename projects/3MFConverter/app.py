import os
import tempfile
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from converter import convert_bambulab_to_snapmaker_u1

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 500  # 500MB


def _is_valid_3mf(filename: str) -> bool:
    return filename.lower().endswith(".3mf")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/convert")
def convert():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Please upload a .3mf file.")
        return redirect(url_for("index"))

    safe_name = secure_filename(uploaded.filename)
    if not _is_valid_3mf(safe_name):
        flash("Only .3mf files are supported.")
        return redirect(url_for("index"))

    input_stem = Path(safe_name).stem
    output_name = f"{input_stem}-snapmaker-u1.3mf"

    with tempfile.TemporaryDirectory() as workdir:
        input_path = Path(workdir) / safe_name
        output_path = Path(workdir) / output_name
        uploaded.save(input_path)

        try:
            convert_bambulab_to_snapmaker_u1(input_path, output_path)
        except Exception as exc:
            flash(f"Conversion failed: {exc}")
            return redirect(url_for("index"))

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
        )


if __name__ == "__main__":
    app.run(debug=True)
