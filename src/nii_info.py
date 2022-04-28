from __future__ import annotations

import argparse
import csv
import json
import re
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from typing import NamedTuple
from typing import NoReturn
from typing import Sequence

import nibabel as nib


__version__ = "0.1.0"


def cli() -> NoReturn:
    raise SystemExit(main())


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
    parser = parser or argparse.ArgumentParser()
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
    out_tsv: TextIOWrapper = ns.out_tsv

    files = find_nii_files(paths)
    write_tsv(files, out_tsv)

    return 0


def find_nii_files(paths: list[str] | list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            files.extend(chain(p.rglob("*.nii"), p.rglob("*.nii.gz")))
        else:
            files.append(p)
    return sorted(set(files))


def write_tsv(files: list[str] | list[Path], tsvfile: TextIOWrapper):
    fieldnames = ImgInfo._fields
    writer = csv.DictWriter(tsvfile, fieldnames, delimiter="\t", lineterminator="\n")
    writer.writeheader()

    for filename in files:
        info = ImgInfo.from_filename(filename)
        writer.writerow(info._asdict())


class ImgInfo(NamedTuple):
    protocol_name: str
    series_description: str
    shape: tuple[int, int, int, int]
    pixdims: tuple[float, float, float, float]
    image_type: list[str]
    seconds: float
    filename: str

    @classmethod
    def from_filename(cls, filename: str | Path):
        img = nib.load(filename)
        sidecar_file = Path(re.sub(r"\.nii(\.gz)?$", ".json", str(filename)))
        sidecar = json.loads(sidecar_file.read_text()) if sidecar_file.exists() else {}

        protocol_name = sidecar.get("ProtocolName")
        series_description = sidecar.get("SeriesDescription")
        shape = tuple(img.header["dim"][1:5])
        pixdims = tuple(img.header["pixdim"][1:5])
        seconds = shape[3] * pixdims[3]
        image_type = sidecar.get("ImageType")
        filename = str(Path(filename).expanduser().resolve())

        return cls(
            protocol_name,
            series_description,
            shape,
            pixdims,
            image_type,
            seconds,
            filename,
        )


if __name__ == "__main__":
    cli()
