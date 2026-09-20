#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import deque

import h5py
import numpy as np

VERSION = "1.0"
STRING = h5py.string_dtype("utf-8")
BOOL_FIELDS = {"xml_exists", "csv_parse_ok", "xml_parse_ok", "grid_checked", "dark_subtracted"}
INT_FIELDS = {
    "csv_bytes", "locations_per_sample", "integrations_per_location",
    "pulses_per_integration", "integrations_averaged", "pulses_discarded",
    "spectral_columns_discarded", "saturated_integrations", "n_columns",
    "n_spectral_columns", "grid_points",
}
FLOAT_FIELDS = {
    "nominal_attenuation_mj", "actual_energy_on_target_mj", "distance_to_target_mm",
    "laser_attenuation_mj", "laser_repetition_rate_hz", "integration_time_s",
    "uv_trigger_delay_ns", "vis_trigger_delay_ns", "vnir_trigger_delay_ns",
    "boxcar_smoothing", "wavelength_first_nm", "wavelength_last_nm",
}
QUALIFIER_CODES = {"": 0, "<": 1, ">": 2, "non_numeric": 3}


def clean(value):
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def as_bool(value):
    text = clean(value).lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return bool(set(tokens) & {"1", "true", "yes", "y"})


def as_float(value):
    text = clean(value).replace(",", "")
    if not text:
        return np.nan
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text)
    return float(match.group()) if match else np.nan


def as_int(value):
    number = as_float(value)
    return -1 if math.isnan(number) else int(round(number))


def read_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_files(paths):
    h = hashlib.sha256()
    for path in paths:
        h.update(path.name.encode())
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
    return h.hexdigest()


def parse_index(value):
    match = re.search(r"\d+", clean(value))
    return int(match.group()) if match else -1


def validate_audit(audit, summary, development):
    required = ["products.csv", "metadata_targets.csv", "chemistry_long.csv", "audit_summary.json"]
    missing = [name for name in required if not (audit / name).is_file()]
    if missing:
        raise RuntimeError("Missing audit outputs: " + ", ".join(missing))
    if development:
        return
    checks = {
        "verification_pass": summary.get("verification_pass") is True,
        "complete_scan": summary.get("complete_scan") is True,
        "manifest inventory": summary.get("manifest", {}).get("inventory_match") is True,
        "part_files": summary.get("part_files") == 0,
        "missing_xml": summary.get("missing_xml") == 0,
        "csv_parse_failures": summary.get("csv_parse_failures") == 0,
        "xml_parse_failures": summary.get("xml_parse_failures") == 0,
        "unmatched_target_groups": summary.get("unmatched_target_groups") == 0,
        "grid_check_mode": summary.get("grid_check_mode") == "all",
        "grids_checked": summary.get("grids_checked") == summary.get("csv_products"),
        "distinct_grid_hashes": summary.get("distinct_grid_hashes") == 1,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("Audit is not definitive: " + ", ".join(failed))


def compression_args(name, level):
    if name == "none":
        return {}
    if name == "gzip":
        return {"compression": "gzip", "compression_opts": level, "shuffle": True}
    return {"compression": "lzf", "shuffle": True}


def write_vector(group, name, values, kind="string"):
    if kind == "bool":
        data = np.asarray([as_bool(x) for x in values], dtype=np.uint8)
    elif kind == "int":
        data = np.asarray([as_int(x) for x in values], dtype=np.int64)
    elif kind == "float":
        data = np.asarray([as_float(x) for x in values], dtype=np.float64)
    else:
        data = np.asarray([clean(x) for x in values], dtype=object)
    group.create_dataset(name, data=data, dtype=STRING if kind == "string" else data.dtype)


def csv_column_names(path):
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f)
        rows = [next(reader, []) for _ in range(24)]
    if len(rows) < 24:
        raise RuntimeError(f"Only {len(rows)} header rows: {path}")
    return [clean(x) for x in rows[23] if clean(x)]


def load_product(item):
    index, path, expected_columns, dtype = item
    names = csv_column_names(path)
    data = np.loadtxt(path, delimiter=",", skiprows=24, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != expected_columns + 1:
        raise RuntimeError(f"{path}: expected {expected_columns + 1} numeric columns, got {data.shape[1]}")
    if len(names) != data.shape[1]:
        raise RuntimeError(f"{path}: header has {len(names)} columns, numeric table has {data.shape[1]}")
    if not np.isfinite(data).all():
        where = np.argwhere(~np.isfinite(data))[0]
        raise RuntimeError(f"{path}: non-finite numeric value at data row {where[0]}, column {where[1]}")
    return index, data[:, 0], data[:, 1:].T.astype(dtype, copy=False)


def prepare_materials(products):
    names = {}
    for row in products:
        key = clean(row.get("metadata_target_key"))
        name = clean(row.get("metadata_target_name"))
        if not key:
            raise RuntimeError(f"Product lacks metadata_target_key: {row.get('csv_path')}")
        names.setdefault(key, name)
        if names[key] != name:
            raise RuntimeError(f"Conflicting material names for {key}: {names[key]} vs {name}")
    keys = sorted(names)
    return keys, [names[k] for k in keys], {k: i for i, k in enumerate(keys)}


def prepare_chemistry(audit, material_keys, material_index):
    rows = read_csv_rows(audit / "chemistry_long.csv")
    pairs = []
    seen = set()
    for row in rows:
        key = clean(row.get("metadata_target_key"))
        if key not in material_index:
            continue
        pair = (clean(row.get("analyte")), clean(row.get("unit")))
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)
    analyte_index = {pair: i for i, pair in enumerate(pairs)}
    values = np.full((len(material_keys), len(pairs)), np.nan, dtype=np.float64)
    qualifiers = np.zeros(values.shape, dtype=np.uint8)
    long_rows = []
    for row in rows:
        key = clean(row.get("metadata_target_key"))
        if key not in material_index:
            continue
        pair = (clean(row.get("analyte")), clean(row.get("unit")))
        mi = material_index[key]
        ai = analyte_index[pair]
        value = as_float(row.get("value"))
        qualifier = clean(row.get("qualifier"))
        code = QUALIFIER_CODES.get(qualifier, 4)
        if np.isfinite(values[mi, ai]):
            raise RuntimeError(f"Duplicate chemistry value for {key}, {pair}")
        values[mi, ai] = value
        qualifiers[mi, ai] = code
        long_rows.append((mi, ai, value, code, clean(row.get("raw_value"))))
    return pairs, values, qualifiers, long_rows


def build_signature(audit, products, args):
    files = [audit / "audit_summary.json", audit / "products.csv", audit / "chemistry_long.csv"]
    source = {
        "audit_sha256": sha256_files(files),
        "products": len(products),
        "dtype": args.dtype,
        "compression": args.compression,
        "gzip_level": args.gzip_level,
    }
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(), source


def create_file(path, root, audit, products, material_keys, material_names, material_index,
                pairs, chemistry_values, chemistry_qualifiers, chemistry_long, args, signature, source):
    n_products = len(products)
    counts = np.asarray([as_int(x.get("n_spectral_columns")) for x in products], dtype=np.int64)
    if np.any(counts <= 0):
        raise RuntimeError("Every product must have at least one spectral column")
    starts = np.concatenate(([0], np.cumsum(counts[:-1])))
    n_spectra = int(counts.sum())
    grid_rows = read_csv_rows(audit / "wavelength_grids.csv")
    grid_points = {as_int(x.get("grid_points")) for x in grid_rows if clean(x.get("grid_points"))}
    if len(grid_points) != 1:
        raise RuntimeError(f"Expected one wavelength length, got {sorted(grid_points)}")
    n_wavelengths = grid_points.pop()
    chunk_rows = min(max(1, args.chunk_spectra), n_spectra)
    kwargs = compression_args(args.compression, args.gzip_level)

    h5 = h5py.File(path, "w")
    h5.attrs.update({
        "format": "NASA SuperLIBS 10K Earth raw spectra",
        "format_version": VERSION,
        "build_status": "incomplete",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(root),
        "audit_directory": str(audit),
        "audit_sha256": source["audit_sha256"],
        "build_signature": signature,
        "products_written": 0,
        "spectra_written": 0,
        "spectrum_dtype": args.dtype,
        "normalization": "none",
        "split_group_identity": "metadata_target_key",
    })
    h5.create_dataset("wavelength_nm", shape=(n_wavelengths,), dtype=np.float64)
    h5.create_dataset(
        "spectra", shape=(n_spectra, n_wavelengths), dtype=np.dtype(args.dtype),
        chunks=(chunk_rows, n_wavelengths), **kwargs
    )
    h5.create_dataset("spectrum_product_index", shape=(n_spectra,), dtype=np.int32,
                      chunks=(min(262144, n_spectra),), **kwargs)
    h5.create_dataset("spectrum_material_index", shape=(n_spectra,), dtype=np.int32,
                      chunks=(min(262144, n_spectra),), **kwargs)
    h5.create_dataset("spectrum_source_column", shape=(n_spectra,), dtype=np.uint8,
                      chunks=(min(262144, n_spectra),), **kwargs)
    h5.create_dataset("spectrum_energy_mj", shape=(n_spectra,), dtype=np.float32,
                      chunks=(min(262144, n_spectra),), **kwargs)

    materials = h5.create_group("materials")
    materials.create_dataset("metadata_target_key", data=np.asarray(material_keys, dtype=object), dtype=STRING)
    materials.create_dataset("metadata_target_name", data=np.asarray(material_names, dtype=object), dtype=STRING)
    product_material = np.asarray([material_index[clean(x.get("metadata_target_key"))] for x in products], dtype=np.int32)
    product_counts = np.bincount(product_material, minlength=len(material_keys)).astype(np.int32)
    spectrum_counts = np.bincount(product_material, weights=counts, minlength=len(material_keys)).astype(np.int64)
    materials.create_dataset("product_count", data=product_counts)
    materials.create_dataset("spectrum_count", data=spectrum_counts)

    chemistry = h5.create_group("chemistry")
    chemistry.create_dataset("analyte", data=np.asarray([x[0] for x in pairs], dtype=object), dtype=STRING)
    chemistry.create_dataset("unit", data=np.asarray([x[1] for x in pairs], dtype=object), dtype=STRING)
    chemistry.create_dataset("value", data=chemistry_values, **kwargs)
    chemistry.create_dataset("qualifier_code", data=chemistry_qualifiers, **kwargs)
    chemistry.create_dataset("qualifier_code_meaning", data=np.asarray([
        "0=none", "1=<", "2=>", "3=non_numeric", "4=other"
    ], dtype=object), dtype=STRING)
    if chemistry_long:
        chemistry.create_dataset("record_material_index", data=np.asarray([x[0] for x in chemistry_long], dtype=np.int32))
        chemistry.create_dataset("record_analyte_index", data=np.asarray([x[1] for x in chemistry_long], dtype=np.int16))
        chemistry.create_dataset("record_value", data=np.asarray([x[2] for x in chemistry_long], dtype=np.float64))
        chemistry.create_dataset("record_qualifier_code", data=np.asarray([x[3] for x in chemistry_long], dtype=np.uint8))
        chemistry.create_dataset("record_raw_value", data=np.asarray([x[4] for x in chemistry_long], dtype=object), dtype=STRING)

    product_group = h5.create_group("products")
    fields = list(products[0])
    for field in fields:
        values = [row.get(field, "") for row in products]
        if field in BOOL_FIELDS:
            write_vector(product_group, field, values, "bool")
        elif field in INT_FIELDS:
            write_vector(product_group, field, values, "int")
        elif field in FLOAT_FIELDS:
            write_vector(product_group, field, values, "float")
        else:
            write_vector(product_group, field, values, "string")
    product_group.create_dataset("material_index", data=product_material)
    product_group.create_dataset("first_spectrum", data=starts.astype(np.int64))
    product_group.create_dataset("spectrum_count", data=counts.astype(np.int32))
    product_group.create_dataset("target_position_index", data=np.asarray([parse_index(x.get("target_number")) for x in products], dtype=np.int16))
    product_group.create_dataset("location_index", data=np.asarray([parse_index(x.get("location_on_sample") or x.get("filename_location")) for x in products], dtype=np.int16))
    h5.flush()
    return h5, starts, counts, product_material


def reopen_for_resume(path, signature, products):
    h5 = h5py.File(path, "r+")
    if h5.attrs.get("build_signature", "") != signature:
        h5.close()
        raise RuntimeError("Partial HDF5 was created from different inputs/options; use --overwrite")
    if len(h5["products/csv_path"]) != len(products):
        h5.close()
        raise RuntimeError("Partial HDF5 product count differs; use --overwrite")
    starts = h5["products/first_spectrum"][:]
    counts = h5["products/spectrum_count"][:]
    product_material = h5["products/material_index"][:]
    return h5, starts, counts, product_material


def finalize(h5, work_path, out_path, summary_path, products, material_keys, pairs, start_time):
    h5.attrs["build_status"] = "complete"
    h5.attrs["completed_utc"] = datetime.now(timezone.utc).isoformat()
    h5.flush()
    shapes = {
        "spectra": list(h5["spectra"].shape),
        "wavelength_nm": list(h5["wavelength_nm"].shape),
        "chemistry_value": list(h5["chemistry/value"].shape),
    }
    audit_sha = h5.attrs["audit_sha256"]
    spectrum_dtype = str(h5["spectra"].dtype)
    h5.close()
    os.replace(work_path, out_path)
    report = {
        "status": "PASS",
        "output": str(out_path),
        "output_bytes": out_path.stat().st_size,
        "products": len(products),
        "spectra": shapes["spectra"][0],
        "wavelength_points": shapes["spectra"][1],
        "materials": len(material_keys),
        "analytes": len(pairs),
        "spectrum_dtype": spectrum_dtype,
        "dataset_shapes": shapes,
        "audit_sha256": audit_sha,
        "elapsed_seconds": round(time.time() - start_time, 2),
        "split_group_identity": "metadata_target_key",
    }
    summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def bounded_map(function, tasks, workers):
    tasks = iter(tasks)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        queue = deque()
        for _ in range(max(1, workers * 2)):
            try:
                queue.append(pool.submit(function, next(tasks)))
            except StopIteration:
                break
        while queue:
            future = queue.popleft()
            yield future.result()
            try:
                queue.append(pool.submit(function, next(tasks)))
            except StopIteration:
                pass


def main():
    parser = argparse.ArgumentParser(description="Build a resumable raw HDF5 file from the verified NASA SuperLIBS 10K Earth archive.")
    parser.add_argument("root", nargs="?", default="/home/user/roboai_green/nasa_calibration")
    parser.add_argument("--audit", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--dtype", choices=["float32", "float64"], default="float32")
    parser.add_argument("--compression", choices=["lzf", "gzip", "none"], default="lzf")
    parser.add_argument("--gzip-level", type=int, default=4)
    parser.add_argument("--chunk-spectra", type=int, default=25)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--max-products", type=int, default=0, help="Development only; 0 builds all products.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    audit = Path(args.audit).expanduser().resolve() if args.audit else root / "audit_superlibs_10k_earth_full_grid"
    out = Path(args.out).expanduser().resolve() if args.out else root / "superlibs_10k_earth_raw.h5"
    work = out.with_name(out.name + ".part")
    summary_path = out.with_suffix(out.suffix + ".summary.json")
    development = args.max_products > 0
    start_time = time.time()

    summary = read_json(audit / "audit_summary.json")
    validate_audit(audit, summary, development)
    products = read_csv_rows(audit / "products.csv")
    if args.max_products:
        products = products[:args.max_products]
    if not products:
        raise SystemExit("ERROR: no products selected")
    if not development and len(products) != summary.get("csv_products"):
        raise SystemExit(f"ERROR: products.csv has {len(products)} rows, audit reports {summary.get('csv_products')}")

    out.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        out.unlink(missing_ok=True)
        work.unlink(missing_ok=True)
        summary_path.unlink(missing_ok=True)
    if out.exists():
        raise SystemExit(f"ERROR: output exists: {out}\nUse --overwrite to replace it.")
    if work.exists() and not args.resume:
        raise SystemExit(f"ERROR: partial build exists: {work}\nUse --resume or --overwrite.")

    material_keys, material_names, material_index = prepare_materials(products)
    pairs, chemistry_values, chemistry_qualifiers, chemistry_long = prepare_chemistry(
        audit, material_keys, material_index
    )
    signature, source = build_signature(audit, products, args)

    if work.exists():
        h5, starts, counts, product_material = reopen_for_resume(work, signature, products)
        start_product = int(h5.attrs.get("products_written", 0))
        print(f"Resuming at product {start_product:,}/{len(products):,}")
    else:
        h5, starts, counts, product_material = create_file(
            work, root, audit, products, material_keys, material_names, material_index,
            pairs, chemistry_values, chemistry_qualifiers, chemistry_long, args, signature, source
        )
        start_product = 0

    reference_grid = h5["wavelength_nm"][:] if start_product else None
    tasks = []
    for i in range(start_product, len(products)):
        row = products[i]
        path = root / clean(row.get("csv_path"))
        if not path.is_file():
            h5.close()
            raise SystemExit(f"ERROR: source CSV not found: {path}")
        tasks.append((i, path, int(counts[i]), np.dtype(args.dtype)))

    def consume(results):
        nonlocal reference_grid
        for i, wavelengths, spectra in results:
            if reference_grid is None:
                reference_grid = wavelengths
                h5["wavelength_nm"][:] = wavelengths
            elif wavelengths.shape != reference_grid.shape or not np.allclose(wavelengths, reference_grid, rtol=0, atol=1e-9):
                raise RuntimeError(f"Wavelength grid differs during build: {products[i]['csv_path']}")
            first = int(starts[i])
            stop = first + int(counts[i])
            h5["spectra"][first:stop] = spectra
            h5["spectrum_product_index"][first:stop] = i
            h5["spectrum_material_index"][first:stop] = product_material[i]
            h5["spectrum_source_column"][first:stop] = np.arange(1, int(counts[i]) + 1, dtype=np.uint8)
            h5["spectrum_energy_mj"][first:stop] = as_float(products[i].get("actual_energy_on_target_mj"))
            h5.attrs["products_written"] = i + 1
            h5.attrs["spectra_written"] = stop
            if (i + 1) % args.progress_every == 0 or i + 1 == len(products):
                h5.flush()
                elapsed = max(time.time() - start_time, 1e-9)
                rate = (i + 1 - start_product) / elapsed
                print(f"processed {i + 1:,}/{len(products):,}; spectra {stop:,}; {rate:.2f} products/s", flush=True)

    try:
        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                consume(bounded_map(load_product, tasks, args.workers))
        else:
            consume(map(load_product, tasks))
        report = finalize(h5, work, out, summary_path, products, material_keys, pairs, start_time)
    except Exception:
        h5.flush()
        h5.close()
        raise

    print("HDF5 build passed.")
    print(f"Products: {report['products']:,}")
    print(f"Spectra: {report['spectra']:,}")
    print(f"Wavelength points: {report['wavelength_points']:,}")
    print(f"Materials: {report['materials']:,}")
    print(f"Analytes: {report['analytes']:,}")
    print(f"Output: {out}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
