# nii-info

Display NIfTI image information in a tabular format

[![PyPI Version](https://img.shields.io/pypi/v/nii-info.svg)](https://pypi.org/project/nii-info/)

## Installation

```bash
pip install nii-info
```

## Motivation

This package attempts to provide a quick and easy way to get a high-level overview of a collection of NIfTI images.

Often when dealing with a collection of NIfTI images the metadata describing those images is embeded across multiple files, specifically the nii images themselves, as well as potential JOSN sidecar files.

Of course, one can crack open a NIfTI file to inspect the header, or load a JSON sidecar into an editor to view its contents. However this quickly becomes tedious when one is dealing with many files and many fields of interest.

`nii-info` collects the values of fields of interest across a set of NIfTI files and aggregates them in a tablular format.

## Usage

`nii-info` exposes a CLI: `nii`

```text
$ nii --help
usage: nii [-h] [-o OUT_TSV] [-f FIELDS] [-v] [-D]
           path [path ...]

Display NIfTI image information in a tabular format

...

positional arguments:
  path                  nifti files or directories
                        containing nifti files,
                        directories are searched
                        recursively

optional arguments:
  -h, --help            show this help message and exit
  -o OUT_TSV, --out-tsv OUT_TSV
                        file to write info to. (default:
                        stdout)
  -f FIELDS, --fields FIELDS
                        Fields to include in the table.
  -v, --version         show program's version number and
                        exit
  -D, --debug           run program in debug mode
```

The `nii` CLI accepts a list of files and/or directories. Directories are searched recursively for `*.nii` and `*.nii.gz` files.

Simple usage might look something like:

```bash
nii /path/to/nii/file1.nii.gz /path/to/nii/file2.nii.gz /path/to/nii/dir/
```

## Modifying Fields/Columns

This application enables the user to modify which JSON sidecar & NIfTI header fields are included in the generated output via the `-f`/`--fields` option.

The `-f` option can be passed multiple times and uses a special syntax.

The argument for the `-f` option should be string of comma-separated values, where each value contains the "location", sidecar or nii header "key", and optional "label".

For example, to add the `FlipAngle` and `InversionTime` fields from the sidecars as well as the `datatype` and `descrip` fields from the NIfTI headers to the default set of outputs, the command could look something like:

```bash
nii \
    -f 'sidecar:FlipAngle,sidecar:InversionTime' \
    -f 'header:datatype,header:descrip:Header Description' \
    /path/to/nii/dir/
```

In the above example, `sidecar:FlipAngle` tells the application to extract the `FlipAngle` field from each image's sidecar.

Additionally, `header:descrip:Header Description` tells the application to extract the `descrip` field from each image's NIfTI header and use the label `Header Descrption` as the column heading.

## Contributing

1. Have or install a recent version of `poetry` (version >= 1.1)
1. Fork the repo
1. Setup a virtual environment (however you prefer)
1. Run `poetry install`
1. Run `pre-commit install`
1. Add your changes (adding/updating tests is always nice too)
1. Commit your changes + push to your fork
1. Open a PR
