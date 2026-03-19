# 3MF Converter

Flask app with two conversion tools:
- Upload a BambuLab `.3mf` file and download a Snapmaker U1-compatible `.3mf`.
- Upload a `.png` file and export a color-separated `.svg` for Autodesk Fusion sketch import and later BambuLab coloring.

## Local run

```bash
cd "/Users/pengchen/Projects/pengchen.space/projects/3MFConverter"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## Conversion behavior

This app follows the `bambu-3mf-orca-fixer` approach:
- It modifies only `Metadata/project_settings.config`.
- It keeps all other embedded files unchanged in content.

The PNG-to-SVG workflow:
- Quantizes the image to a limited palette, defaulting to `4` colors.
- Ignores transparent pixels.
- Splits each remaining palette color into closed vector regions.
- Writes one SVG with separate grouped paths per color for downstream CAD or slicer workflows.
