#!/usr/bin/env python3
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_hashes(errors):
    path = ROOT / "SHA256SUMS.txt"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        expected, name = line.split(None, 1)
        target = ROOT / name.strip().lstrip("*")
        if not target.is_file():
            errors.append(f"missing: {name}")
        elif sha(target) != expected:
            errors.append(f"hash mismatch: {name}")


def check_emslibs(errors):
    root = ROOT / "splits/emslibs2019"
    for stem in ("random20", "group20", "combined20"):
        meta = json.loads((root / f"{stem}.json").read_text())
        with np.load(root / f"{stem}.npz", allow_pickle=False) as split:
            if set(split.files) != {"train", "val"}:
                errors.append(f"{stem}: unexpected NPZ keys")
                continue
            train, val = split["train"], split["val"]
        if train.ndim != 1 or val.ndim != 1 or train.dtype.kind not in "iu" or val.dtype.kind not in "iu":
            errors.append(f"{stem}: invalid index arrays")
            continue
        if len(train) != meta["n_train"] or len(val) != meta["n_val"]:
            errors.append(f"{stem}: count mismatch")
        if len(np.intersect1d(train, val)):
            errors.append(f"{stem}: training/validation row overlap")
        n = meta["n_per_sample"]
        overlap = len(set(train // n) & set(val // n))
        if overlap != meta["overlap_groups"]:
            errors.append(f"{stem}: physical-sample overlap mismatch")


def check_quantification(errors):
    root = ROOT / "splits/superlibs_quantification"
    meta = json.loads((root / "scientific_manifest.json").read_text())
    stats = {}
    with (root / "row_set_statistics.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            stats[row["row_set"]] = int(row["spectra"])
    with np.load(root / "scientific_manifest_rows.npz", allow_pickle=False) as rows:
        if set(rows.files) != set(meta["row_sets"]):
            errors.append("quantification: row-set names differ from manifest")
        limit = int(meta["source"]["spectra_shape"][0])
        for name in rows.files:
            values = rows[name]
            if values.ndim != 1 or values.dtype.kind not in "iu":
                errors.append(f"quantification: invalid row set {name}")
            elif len(values) != len(np.unique(values)):
                errors.append(f"quantification: duplicate index within {name}")
            elif len(values) and (values.min() < 0 or values.max() >= limit):
                errors.append(f"quantification: out-of-range index in {name}")
            if name not in stats or len(values) != stats[name]:
                errors.append(f"quantification: count mismatch for {name}")


def csv_gz_count(path, required, errors):
    with gzip.open(path, "rt", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if not required <= fields:
            errors.append(f"{path.name}: missing required columns")
        return sum(1 for _ in reader)


def check_classification(errors):
    root = ROOT / "splits/superlibs_classification"
    status = json.loads((root / "row_manifest_status.json").read_text())
    required = {
        "hdf5_row_index", "immutable_row_id", "material_id", "family_id",
        "split_group_id", "class_label", "row_role", "locked",
        "training_eligible", "preprocessing_eligible", "model_selection_eligible",
    }
    files = {
        "branch_a_row_manifest.csv.gz": status["branch_a_rows"],
        "branch_b_row_manifest.csv.gz": status["branch_b_rows"],
    }
    for name, expected in files.items():
        if csv_gz_count(root / name, required, errors) != expected:
            errors.append(f"{name}: row-count mismatch")
    if not status.get("row_manifest_generation_pass") or not status.get("preprocessing_isolation_pass"):
        errors.append("classification: frozen release-gate status is not passing")
    csv_gz_count(root / "branch_b_balanced_replication_manifest.csv.gz", required, errors)
    for branch in ("a", "b"):
        meta = json.loads((root / f"branch_{branch}_preprocessing_fit_manifest.json").read_text())
        manifest = root / meta["row_manifest"]
        if sha(manifest) != meta["row_manifest_sha256"]:
            errors.append(f"classification: Branch {branch.upper()} preprocessing link mismatch")


def main():
    errors = []
    try:
        check_hashes(errors)
        check_emslibs(errors)
        check_quantification(errors)
        check_classification(errors)
    except Exception as exc:
        errors.append(f"verification exception: {exc}")
    result = {"complete": not errors, "errors": errors}
    print(json.dumps(result, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
