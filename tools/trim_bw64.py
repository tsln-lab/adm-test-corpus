#!/usr/bin/env python3
"""Trim the audio of an ADM BWF (RIFF, BW64 or RF64) file, keeping the rest.

    tools/trim_bw64.py input.wav output.wav --seconds 60

Every chunk other than the audio data is copied verbatim: the ADM metadata
(axml), the track mapping (chna), Dolby's dbmd, bext and anything else, so
the file still describes the whole programme while carrying only its first
seconds of audio. The output is a plain RIFF file when it fits in 4 GB, and
the 64-bit sizes of an RF64 or BW64 input are resolved through its ds64
chunk. The trimmed length is rounded down to whole frames.

Readers see metadata whose timed blocks run past the end of the audio; the
EBU ADM Renderer and libear-max take that in their stride, and the audio
that is there plays with the right metadata. A trimmed file is an
adaptation of the original under CC BY 4.0: say so in the attribution.
"""

import argparse
import struct
import sys

CHUNK_COPY = 1 << 20


def read_exact(f, n):
    data = f.read(n)
    if len(data) != n:
        raise SystemExit("unexpected end of file")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--seconds", type=float, default=60.0, help="audio to keep (default 60)")
    args = parser.parse_args()

    with open(args.input, "rb") as src, open(args.output, "wb") as dst:
        riff_id, riff_size, form = struct.unpack("<4sI4s", read_exact(src, 12))
        if riff_id not in (b"RIFF", b"RF64", b"BW64") or form != b"WAVE":
            raise SystemExit(f"{args.input}: not a WAVE file")
        sizes = {}  # chunk id -> 64-bit size from ds64, for sizes written as 0xFFFFFFFF
        fmt = None
        dst.write(struct.pack("<4sI4s", b"RIFF", 0, b"WAVE"))
        kept_frames = None
        while True:
            header = src.read(8)
            if len(header) < 8:
                break
            chunk_id, size = struct.unpack("<4sI", header)
            if size == 0xFFFFFFFF and chunk_id in sizes:
                size = sizes[chunk_id]
            if chunk_id == b"ds64":
                body = read_exact(src, size)
                riff_size64, data_size64, _sample_count, table_length = struct.unpack("<QQQI", body[:28])
                sizes[b"data"] = data_size64
                for i in range(table_length):
                    entry_id, entry_size = struct.unpack("<4sQ", body[28 + 12 * i : 40 + 12 * i])
                    sizes[entry_id] = entry_size
                if size & 1:
                    src.read(1)
                continue  # the output is a RIFF file: no ds64
            if chunk_id == b"fmt ":
                body = read_exact(src, size)
                fmt = struct.unpack("<HHIIHH", body[:16])
                dst.write(header + body)
                if size & 1:
                    dst.write(read_exact(src, 1))
                continue
            if chunk_id == b"data":
                if fmt is None:
                    raise SystemExit("data chunk before fmt chunk")
                channels, sample_rate, block_align = fmt[1], fmt[2], fmt[4]
                frames = size // block_align
                kept_frames = min(frames, int(args.seconds * sample_rate))
                kept = kept_frames * block_align
                dst.write(struct.pack("<4sI", b"data", kept))
                remaining = kept
                while remaining:
                    piece = read_exact(src, min(CHUNK_COPY, remaining))
                    dst.write(piece)
                    remaining -= len(piece)
                if kept & 1:
                    dst.write(b"\0")
                src.seek(size - kept + (size & 1), 1)
                print(f"data: {frames} frames of {channels} channels at {sample_rate} Hz, kept {kept_frames}")
                continue
            # any other chunk: copied as is (axml, chna, dbmd, bext, JUNK, ...)
            if size > 0xFFFFFFFE:
                raise SystemExit(f"chunk {chunk_id!r} is too large for a RIFF file")
            dst.write(struct.pack("<4sI", chunk_id, size))
            remaining = size
            while remaining:
                piece = read_exact(src, min(CHUNK_COPY, remaining))
                dst.write(piece)
                remaining -= len(piece)
            if size & 1:
                dst.write(read_exact(src, 1))
            print(f"{chunk_id.decode('ascii', 'replace')}: {size} bytes copied")
        if kept_frames is None:
            raise SystemExit("no data chunk found")
        total = dst.tell()
        if total - 8 > 0xFFFFFFFF:
            raise SystemExit("the trimmed file still exceeds 4 GB; keep fewer seconds")
        dst.seek(4)
        dst.write(struct.pack("<I", total - 8))
    print(f"wrote {args.output} ({total} bytes)")


if __name__ == "__main__":
    main()
