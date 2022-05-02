from __future__ import annotations

import argparse
import csv
import importlib
import json
import re
from enum import Enum
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from typing import Any
from typing import NamedTuple
from typing import NoReturn
from typing import Sequence

import nibabel as nib


__version__ = "1.0.1"


class FieldEntity(Enum):
    SIDECAR = "sidecar"
    HEADER = "header"
    FUNCTION = "function"


FIELD_ENTITIES = tuple(m.value for m in FieldEntity)
SPEC_REGEX = re.compile(r"^(?P<entity>[^\:]+):(?P<name>[^\:]+)(:(?P<label>[^\:]*))?$")
CLI_DESCRIPTION = """\
Display NIfTI image information in a tabular format

This application enables the user to modify which
JSON sidecar & NIfTI header fields are included in
the generated output via the "-f/--fields" option.

The "-f" option can be passed multiple times and
uses a special syntax.

The argument for the "-f" option should be string of
comma-separated values, where each value contains the
"location", sidecar or nii header "key", and optional
"label".

For example, to include the "FlipAngle" and "InversionTime"
fields from the sidecars as well as the "datatype" and
"descrip" fields from the nifti headers, the command
could look something like:

nii \\
    -f 'sidecar:FlipAngle,sidecar:InversionTime' \\
    -f 'header:datatype,header:descrip:Header Description' \\
    /path/to/nii/dir/

In the above example, "sidecar:FlipAngle" tells the
application to extract the "FlipAngle" field
from each image's sidecar.

Additionally, "header:descrip:Header Description"
tells the application to extract the "descrip" field
from each image's nifti header and use the label
"Header Descrption" as the column heading.
"""


class NiftiField(NamedTuple):
    entity: FieldEntity
    name: str
    label: str | None


class Defaults:
    fields = [
        NiftiField(FieldEntity.SIDECAR, "ProtocolName", None),
        NiftiField(FieldEntity.SIDECAR, "SeriesDescription", None),
        NiftiField(FieldEntity.FUNCTION, "nii_info._get_dims", "shape"),
        NiftiField(FieldEntity.FUNCTION, "nii_info._get_pixdims", "pixdims"),
        NiftiField(FieldEntity.FUNCTION, "nii_info._elapsed_time", "elapsed Time (s)"),
        NiftiField(FieldEntity.SIDECAR, "ImageType", None),
        NiftiField(FieldEntity.FUNCTION, "nii_info._get_filename", "filename"),
    ]
    fields_alias = "[DEFAULTS]"


def cli(args: Sequence[str] | None = None) -> NoReturn:
    raise SystemExit(main(args))


def main(args: Sequence[str] | None = None) -> int | str:
    parser = create_parser()
    ns = parser.parse_args(args)
    debug: bool = ns.debug

    try:
        return ns.handler(ns)
    except Exception as e:
        if debug:
            raise
        else:
            return str(e)


def create_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    parser = parser or argparse.ArgumentParser(
        description=CLI_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="+",
        type=Path,
        help="nifti files or directories containing nifti files, "
        "directories are searched recursively",
    )
    parser.add_argument(
        "-o",
        "--out-tsv",
        default="-",
        type=argparse.FileType("w"),
        help="file to write info to. (default: stdout)",
    )
    parser.add_argument(
        "-f",
        "--fields",
        default=["[DEFAULTS]"],
        action="append",
        help="Fields to include in the table.",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        default=False,
        help="run program in debug mode",
    )

    parser.set_defaults(handler=handler)

    return parser


def handler(ns: argparse.Namespace) -> int:
    paths: list[Path] = ns.path
    tsvfile: TextIOWrapper = ns.out_tsv
    specs = parse_fields_args(ns.fields)
    fields = parse_field_specs(specs)

    nii_info(paths, tsvfile, fields=fields)

    return 0


def parse_fields_args(args: list[str]) -> list[str]:
    specs: list[str] = []
    for arg_s in args:
        specs.extend(arg_s.split(","))
    return specs


def parse_field_specs(specs: list[str]) -> list[NiftiField]:
    fields: list[NiftiField] = []
    for spec in specs:
        _spec = spec.strip()

        # inject the default fields
        if _spec == Defaults.fields_alias:
            fields.extend(Defaults.fields)
            continue

        # parse the field spec
        _match = SPEC_REGEX.match(_spec)
        if _match is None:
            raise SyntaxError(f"Failed to parse field spec: {_spec!r}")
        groupdict = _match.groupdict()

        # extract the parts from the parsed spec
        entity_value = groupdict["entity"]
        try:
            entity = FieldEntity(entity_value)
        except ValueError:
            msg = (
                f"Unexpected field type {entity_value!r}. "
                f"Expected one of {FIELD_ENTITIES}"
            )
            raise ValueError(msg)
        name = groupdict["name"]
        label = groupdict["label"] or None

        field = NiftiField(entity, name, label)
        fields.append(field)

    return fields


def nii_info(
    paths: list[str] | list[Path],
    tsvfile: TextIOWrapper,
    *,
    fields: list[NiftiField] | None = None,
):
    fields = fields or Defaults.fields
    files = find_nii_files(paths)
    pairs = [load_pair(filename) for filename in files]
    records = [create_record(img, sidecar, fields) for img, sidecar in pairs]
    fieldnames = create_fieldnames(fields)
    write_tsv(tsvfile, records, fieldnames)


def find_nii_files(paths: list[str] | list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            files.extend(chain(p.rglob("*.nii"), p.rglob("*.nii.gz")))
        else:
            files.append(p)
    return sorted(set(files))


def load_pair(filename: str | Path) -> tuple[nib.Nifti1Image, dict[str, Any]]:
    img = nib.load(filename)
    sidecar_file = Path(re.sub(r"\.nii(\.gz)?$", ".json", str(filename)))
    sidecar = json.loads(sidecar_file.read_text()) if sidecar_file.exists() else {}
    return img, sidecar


def create_fieldnames(fields: list[NiftiField]) -> list[str]:
    return [f.label or f.name for f in fields]


def create_record(
    img: nib.Nifti1Image,
    sidecar: dict[str, Any],
    fields: list[NiftiField],
):
    record: list[Any] = []
    for field in fields:
        if field.entity == FieldEntity.SIDECAR:
            record.append(sidecar.get(field.name))
        elif field.entity == FieldEntity.HEADER:
            record.append(img.header[field.name])  # type: ignore
        elif field.entity == FieldEntity.FUNCTION:
            fn = fqn_import(field.name)
            record.append(fn(img, sidecar))
        else:
            raise ValueError(f"Unexpected field type {field.entity!r}")
    return record


def fqn_import(fqn: str):
    module_name, _, function_name = fqn.rpartition(".")
    return getattr(importlib.import_module(module_name), function_name)


def write_tsv(tsvfile, records: list[Any], fieldnames: list[str]):
    writer = csv.writer(tsvfile, delimiter="\t", lineterminator="\n")
    writer.writerow(fieldnames)
    writer.writerows(records)


# --- UTILITY FUNCTIONS ---


def _get_dims(
    img: nib.Nifti1Image,
    sidecar: dict[str, Any],
) -> tuple[int, int, int, int]:
    return tuple(img.header["dim"][1:5])  # type: ignore


def _get_pixdims(
    img: nib.Nifti1Image,
    sidecar: dict[str, Any],
) -> tuple[float, float, float, float]:
    return tuple(img.header["pixdim"][1:5])  # type: ignore


def _elapsed_time(img: nib.Nifti1Image, sidecar: dict[str, Any]) -> float:
    shape = _get_dims(img, sidecar)
    pixdims = _get_pixdims(img, sidecar)
    return shape[-1] * pixdims[-1]


def _get_filename(img: nib.Nifti1Image, sidecar: dict[str, Any]) -> str | None:
    return img.get_filename()


if __name__ == "__main__":
    cli()
