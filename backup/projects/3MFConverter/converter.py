import hashlib
import json
import zipfile
from pathlib import Path

CFG_PATH = "Metadata/project_settings.config"

SNAPMAKER_U1_PRESET = {
    "before_layer_change_gcode": "G92 E0",
    "solid_infill_filament": "1",
    "raft_first_layer_expansion": "0",
    "sparse_infill_filament": "1",
    "tree_support_wall_count": "0",
    "wall_filament": "1",
    "change_filament_gcode": "; disabled for Snapmaker Orca compatibility",
    "machine_start_gcode": "; use printer profile defaults for Snapmaker Orca compatibility",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_project_settings(zf: zipfile.ZipFile) -> dict:
    if CFG_PATH not in zf.namelist():
        raise RuntimeError(f"Missing {CFG_PATH}")
    return json.loads(zf.read(CFG_PATH).decode("utf-8"))


def _build_output_zip(input_zip: Path, output_zip: Path, new_cfg_bytes: bytes) -> None:
    with zipfile.ZipFile(input_zip, "r") as zin, zipfile.ZipFile(output_zip, "w") as zout:
        for info in zin.infolist():
            payload = new_cfg_bytes if info.filename == CFG_PATH else zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.create_system = info.create_system
            zi.external_attr = info.external_attr
            zi.internal_attr = info.internal_attr
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, payload)


def _verify_only_project_settings_changed(input_zip: Path, output_zip: Path) -> None:
    with zipfile.ZipFile(input_zip, "r") as source_zip, zipfile.ZipFile(output_zip, "r") as result_zip:
        source_entries = {i.filename for i in source_zip.infolist()}
        result_entries = {i.filename for i in result_zip.infolist()}
        if source_entries != result_entries:
            raise RuntimeError("Internal file list changed")

        changed = []
        for name in sorted(source_entries):
            if _sha256_bytes(source_zip.read(name)) != _sha256_bytes(result_zip.read(name)):
                changed.append(name)

        if changed != [CFG_PATH]:
            raise RuntimeError(f"Unexpected changed entries: {changed}")


def convert_bambulab_to_snapmaker_u1(input_zip: Path, output_zip: Path) -> None:
    """Patch only project_settings.config to improve Snapmaker U1 Orca compatibility."""
    with zipfile.ZipFile(input_zip, "r") as source_zip:
        config = _load_project_settings(source_zip)

    for key, value in SNAPMAKER_U1_PRESET.items():
        config[key] = value

    patched_config = json.dumps(config, ensure_ascii=False, indent=4).encode("utf-8")
    _build_output_zip(input_zip, output_zip, patched_config)
    _verify_only_project_settings_changed(input_zip, output_zip)
