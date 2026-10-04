# adm-test-corpus
ADM QC materials from https://qc.ebu.io/testmaterials/?path=/ADM/

## Trimming large files

Release assets are limited to 2 GB, and a Dolby Atmos master runs to about
a gigabyte per minute. `tools/trim_bw64.py input.wav output.wav --seconds 60`
keeps the first seconds of audio and copies every other chunk verbatim
(the ADM metadata, the chna track mapping, Dolby's dbmd, bext), so the
trimmed file still describes the whole programme; RF64 and BW64 inputs
over 4 GB are read through their ds64 chunk and written as plain RIFF.
A trimmed file is an adaptation of the original: say so in ATTRIBUTION.md.
