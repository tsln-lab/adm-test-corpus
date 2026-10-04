# adm-test-corpus
ADM test material for [libear-max](https://github.com/tsln-lab/libear-max),
as release assets:

- `v1.0.0`: the EBU's ADM QC materials from
  <https://qc.ebu.io/testmaterials/?path=/ADM/>, unmodified
- `netflix-v1.0.0`: the first 60 seconds of Netflix's Dolby Atmos master
  ADM files for *Meridian*, *Nocturne* and *Sol Levante*, from
  <https://opencontent.netflix.com/>, trimmed with the tool below

Both are CC BY 4.0; see [ATTRIBUTION.md](ATTRIBUTION.md).

## Trimming large files

Release assets are limited to 2 GB, and a Dolby Atmos master runs to about
a gigabyte per minute. `tools/trim_bw64.py input.wav output.wav --seconds 60`
keeps the first seconds of audio and copies every other chunk verbatim
(the ADM metadata, the chna track mapping, Dolby's dbmd, bext), so the
trimmed file still describes the whole programme; RF64 and BW64 inputs
over 4 GB are read through their ds64 chunk and written as plain RIFF.
A trimmed file is an adaptation of the original: say so in ATTRIBUTION.md.
