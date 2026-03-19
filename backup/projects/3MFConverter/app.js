const CFG_PATH = "Metadata/project_settings.config";

const SNAPMAKER_U1_PRESET = {
  before_layer_change_gcode: "G92 E0",
  solid_infill_filament: "1",
  raft_first_layer_expansion: "0",
  sparse_infill_filament: "1",
  tree_support_wall_count: "0",
  wall_filament: "1",
  change_filament_gcode: "; disabled for Snapmaker Orca compatibility",
  machine_start_gcode: "; use printer profile defaults for Snapmaker Orca compatibility",
};

const fileInput = document.getElementById("file");
const filename = document.getElementById("filename");
const dropzone = document.getElementById("dropzone");
const convertBtn = document.getElementById("convertBtn");
const statusEl = document.getElementById("status");
const alertEl = document.getElementById("alert");

let selectedFile = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function showError(text) {
  alertEl.textContent = text;
  alertEl.classList.remove("hidden");
}

function clearError() {
  alertEl.textContent = "";
  alertEl.classList.add("hidden");
}

function setSelectedFile(file) {
  selectedFile = file;
  const valid = !!file && file.name.toLowerCase().endsWith(".3mf");
  convertBtn.disabled = !valid;
  filename.textContent = file ? file.name : "No file selected";
  if (file && !valid) {
    showError("Only .3mf files are supported.");
    setStatus("Please choose a valid .3mf file.");
  } else if (file) {
    clearError();
    setStatus("Ready to convert.");
  } else {
    clearError();
    setStatus("Waiting for a .3mf file.");
  }
}

fileInput.addEventListener("change", () => {
  setSelectedFile(fileInput.files[0] || null);
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("active");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("active");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("active");
  const file = event.dataTransfer.files[0];
  if (!file) return;
  fileInput.files = event.dataTransfer.files;
  setSelectedFile(file);
});

function downloadBlob(blob, originalName) {
  const stem = originalName.replace(/\.3mf$/i, "");
  const outputName = `${stem}-snapmaker-u1.3mf`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = outputName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function convertFile(file) {
  const zipData = await file.arrayBuffer();
  const zip = await JSZip.loadAsync(zipData);
  const configEntry = zip.file(CFG_PATH);
  if (!configEntry) {
    throw new Error(`Invalid .3mf: missing ${CFG_PATH}`);
  }

  const configText = await configEntry.async("string");
  let config;
  try {
    config = JSON.parse(configText);
  } catch {
    throw new Error("Invalid JSON in project settings.");
  }

  for (const [key, value] of Object.entries(SNAPMAKER_U1_PRESET)) {
    config[key] = value;
  }

  zip.file(CFG_PATH, `${JSON.stringify(config, null, 4)}\n`);

  return zip.generateAsync({
    type: "blob",
    compression: "DEFLATE",
    compressionOptions: { level: 6 },
    mimeType: "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
  });
}

convertBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  clearError();
  convertBtn.disabled = true;
  setStatus("Converting...");

  try {
    const outputBlob = await convertFile(selectedFile);
    downloadBlob(outputBlob, selectedFile.name);
    setStatus("Done. Download started.");
  } catch (error) {
    showError(error.message || "Conversion failed.");
    setStatus("Conversion failed.");
  } finally {
    convertBtn.disabled = false;
  }
});
