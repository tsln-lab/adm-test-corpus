# Attribution

This repository redistributes ADM test material from two sources, as
release assets, so that the libear-max test suite and its continuous
integration can fetch them from one stable place: the EBU's ADM test
materials (release `v1.0.0`, unmodified) and excerpts of Netflix's Dolby
Atmos master ADM files (release `netflix-v1.0.0`, trimmed as described
below). Both are licensed under CC BY 4.0.

# The EBU's ADM test materials (release v1.0.0)

## Source

- Creator: European Broadcasting Union (EBU), https://tech.ebu.ch
- Material: ADM Test Materials
- Retrieved from: https://qc.ebu.io/testmaterials/?path=/ADM/
- Retrieved on: 2026-10-04

## Licence

The material is licensed under the Creative Commons Attribution 4.0
International licence (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/

Under that licence you may copy and redistribute the material and adapt
it for any purpose, provided you give appropriate credit, link to the
licence, and indicate whether changes were made. The EBU does not endorse
this repository or libear-max.

## Changes

None. The release assets are byte-identical to the files obtained from
the source above. Where an archive was repackaged for upload, the files
inside it are unchanged; the archive name and its checksum are listed in
the release notes.

## How this material is used

libear-max (https://github.com/tsln-lab/libear-max) reads these files in
an opt-in test suite that checks its ADM parsing, item selection and
round trips against material produced by other tools. A manifest of
expected results derived from these files lives in that repository.

# Netflix's Dolby Atmos master ADM files (release netflix-v1.0.0)

## Source

- Creator: Netflix, Inc.
- Material: the Dolby Atmos master ADM BWF files of the Netflix Open
  Content titles *Meridian*, *Nocturne* and *Sol Levante*
- Retrieved from: https://opencontent.netflix.com/
- Retrieved on: 2026-10-04

## Licence

The material is licensed under the Creative Commons Attribution 4.0
International licence (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/

Under that licence you may copy and redistribute the material and adapt
it for any purpose, provided you give appropriate credit, link to the
licence, and indicate whether changes were made. Netflix does not endorse
this repository or libear-max.

## Changes

The files are adaptations of the originals: each was trimmed to its first
60 seconds of audio with `tools/trim_bw64.py` of this repository, which
keeps the first seconds of the `data` chunk and copies every other chunk
verbatim, so the ADM metadata (`axml`), the track mapping (`chna`) and
Dolby's `dbmd` chunk are those of the full master and describe the whole
programme. The RF64 originals became plain RIFF files, and the assets were
renamed to `meridian.wav`, `nocturne.wav` and `sollevante.wav`.

| Asset | Original file |
| --- | --- |
| `meridian.wav` | `Meridian_ADMFromDAMF_JAN2021.wav` |
| `nocturne.wav` | `Nocture_ADM.wav` |
| `sollevante.wav` | `sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.wav` |

## How this material is used

libear-max reads these files in the same opt-in test suite, where they
are the only Dolby Atmos masters: files with Dolby's bed channel formats,
Cartesian object metadata sampled every few milliseconds, several beds
and contents per programme, and a `dbmd` chunk.
