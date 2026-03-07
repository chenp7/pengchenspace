# 3MF Converter

Static website to upload a BambuLab `.3mf` file and download a Snapmaker U1-compatible `.3mf` directly in the browser.

## Local run (no backend)

```bash
cd "/Users/pengchen/Projects/3MF Converter"
python3 -m http.server 8000
```

Open: `http://127.0.0.1:8000`

## Deploy on GitHub Pages

1. Push this repo to GitHub.
2. In GitHub repo settings, open `Pages`.
3. Set source to `Deploy from a branch`.
4. Choose your branch (for example `main`) and folder `/ (root)`.
5. Save. GitHub Pages will publish `index.html`.

## Conversion behavior

This app follows the `bambu-3mf-orca-fixer` approach:
- It modifies only `Metadata/project_settings.config`.
- It keeps all other embedded files unchanged in content.
- It runs fully client-side with HTML + JS (`JSZip`), so files are not uploaded to a server.
