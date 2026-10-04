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
import math
import os
import struct
import sys
import tempfile

CHUNK_COPY = 1 << 20
# ds64 and fmt are read whole; anything larger than this is not one of them
HEADER_CHUNK_LIMIT = 1 << 20
SENTINEL = 0xFFFFFFFF
# WAVE_FORMAT_PCM and WAVE_FORMAT_IEEE_FLOAT, as a format tag or as the
# first two bytes of a WAVE_FORMAT_EXTENSIBLE sub-format GUID
PCM_FORMATS = (0x0001, 0x0003)
EXTENSIBLE = 0xFFFE
# the 14 bytes that follow the tag in the sub-format GUID of the formats
# registered by Microsoft, 0000xxxx-0000-0010-8000-00aa00389b71, as stored
SUBFORMAT_TAIL = bytes.fromhex("0000" + "0000" + "1000" + "800000aa00389b71")


def read_exact(f, n):
    """Read exactly n bytes from f, or stop with an error at a short read."""
    data = f.read(n)
    if len(data) != n:
        raise SystemExit("unexpected end of file")
    return data


def copy_bytes(src, dst, n):
    """Copy n bytes from src to dst in pieces, so no chunk is held whole."""
    remaining = n
    while remaining:
        piece = read_exact(src, min(CHUNK_COPY, remaining))
        dst.write(piece)
        remaining -= len(piece)


def same_file(a, b):
    """True when the two paths name the same file (by identity when both exist)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.abspath(a) == os.path.abspath(b)


def trim(src, dst, seconds):
    """Copy the WAVE file open on src to dst, keeping `seconds` of audio.

    Returns the size of the written file. Raises SystemExit on malformed
    input: a short chunk header, a 64-bit size the ds64 chunk does not
    resolve, a fmt chunk that is not PCM or whose block alignment is not
    one frame, or a data chunk before the fmt chunk.
    """
    riff_id, riff_size, form = struct.unpack("<4sI4s", read_exact(src, 12))
    if riff_id not in (b"RIFF", b"RF64", b"BW64") or form != b"WAVE":
        raise SystemExit("not a WAVE file")
    # chunks are read up to the container's declared end, so bytes after it
    # are not taken for chunks; a size of 0 (some writers never fill it in)
    # or the sentinel (resolved by ds64) means the end of the file
    riff_end = 8 + riff_size if riff_id == b"RIFF" and riff_size not in (0, SENTINEL) else None
    # 64-bit sizes from ds64, one list per chunk id in file order: each
    # chunk whose header carries the sentinel takes the next one for its id
    sizes = {}
    fmt = None
    kept_frames = None
    dst.write(struct.pack("<4sI4s", b"RIFF", 0, b"WAVE"))
    while riff_end is None or src.tell() < riff_end:
        header = src.read(8)
        if not header:
            break
        if len(header) < 8:
            raise SystemExit("truncated chunk header at end of file")
        chunk_id, size = struct.unpack("<4sI", header)
        if size == SENTINEL:
            if not sizes.get(chunk_id):
                raise SystemExit(f"chunk {chunk_id!r} has a 64-bit size that no ds64 entry resolves")
            size = sizes[chunk_id].pop(0)
        if chunk_id == b"ds64":
            if size > HEADER_CHUNK_LIMIT or size < 28:
                raise SystemExit(f"ds64 chunk of {size} bytes is not plausible")
            body = read_exact(src, size)
            riff_size64, data_size64, _sample_count, table_length = struct.unpack("<QQQI", body[:28])
            if riff_size64:
                riff_end = 8 + riff_size64
            if 28 + 12 * table_length > size:
                raise SystemExit("ds64 chunk is shorter than its table")
            sizes.setdefault(b"data", []).append(data_size64)
            for i in range(table_length):
                entry_id, entry_size = struct.unpack("<4sQ", body[28 + 12 * i : 40 + 12 * i])
                sizes.setdefault(entry_id, []).append(entry_size)
            if size & 1:
                src.read(1)
            continue  # the output is a RIFF file: no ds64
        if chunk_id == b"fmt ":
            if size > HEADER_CHUNK_LIMIT or size < 16:
                raise SystemExit(f"fmt chunk of {size} bytes is not plausible")
            body = read_exact(src, size)
            fmt = struct.unpack("<HHIIHH", body[:16])
            format_tag, channels, _rate, _bytes_per_second, block_align, bits = fmt
            # only PCM and float, where a block is one frame of samples;
            # a compressed format's block is an encoded block of many frames
            if format_tag == EXTENSIBLE:
                # 16 bytes of WAVEFORMATEX, cbSize, 22 bytes of extension
                # ending in the sub-format GUID
                if size < 40 or struct.unpack("<H", body[16:18])[0] < 22:
                    raise SystemExit("extensible fmt chunk is too short to carry a sub-format")
                sub_tag = struct.unpack("<H", body[24:26])[0]
                if sub_tag not in PCM_FORMATS or body[26:40] != SUBFORMAT_TAIL:
                    raise SystemExit(f"extensible sub-format {body[24:40].hex()} is not PCM or float; only those can be trimmed by frames")
            elif format_tag not in PCM_FORMATS:
                raise SystemExit(f"format tag 0x{format_tag:04x} is not PCM or float; only those can be trimmed by frames")
            if channels == 0 or bits == 0 or block_align != channels * ((bits + 7) // 8):
                raise SystemExit(f"block alignment {block_align} is not one frame of {channels} channels at {bits} bits")
            dst.write(header + body)
            if size & 1:
                dst.write(read_exact(src, 1))
            continue
        if chunk_id == b"data":
            if fmt is None:
                raise SystemExit("data chunk before fmt chunk")
            channels, sample_rate, block_align = fmt[1], fmt[2], fmt[4]
            frames = size // block_align
            kept_frames = min(frames, int(seconds * sample_rate))
            kept = kept_frames * block_align
            dst.write(struct.pack("<4sI", b"data", kept))
            copy_bytes(src, dst, kept)
            if kept & 1:
                dst.write(b"\0")
            src.seek(size - kept + (size & 1), 1)
            print(f"data: {frames} frames of {channels} channels at {sample_rate} Hz, kept {kept_frames}")
            continue
        # any other chunk: copied as is (axml, chna, dbmd, bext, JUNK, ...)
        if size > SENTINEL - 1:
            raise SystemExit(f"chunk {chunk_id!r} is too large for a RIFF file")
        dst.write(struct.pack("<4sI", chunk_id, size))
        copy_bytes(src, dst, size)
        if size & 1:
            dst.write(read_exact(src, 1))
        print(f"{chunk_id.decode('ascii', 'replace')}: {size} bytes copied")
    if kept_frames is None:
        raise SystemExit("no data chunk found")
    total = dst.tell()
    if total - 8 > SENTINEL:
        raise SystemExit("the trimmed file still exceeds 4 GB; keep fewer seconds")
    dst.seek(4)
    dst.write(struct.pack("<I", total - 8))
    return total


def main():
    """Parse the command line and trim the file.

    The output is written to a temporary file beside its final path and
    moved into place once the trim succeeds, so a failed run leaves
    whatever was at the output path untouched and no partial file behind.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--seconds", type=float, default=60.0, help="audio to keep (default 60)")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds < 0:
        raise SystemExit("--seconds must be a finite, non-negative number")
    if same_file(args.input, args.output):
        raise SystemExit("input and output are the same file; choose another output path")

    try:
        src = open(args.input, "rb")
    except OSError as e:
        raise SystemExit(f"{args.input}: {e.strerror}")
    out_dir = os.path.dirname(os.path.abspath(args.output))
    out_name = os.path.basename(args.output)
    with src:
        try:
            dst = tempfile.NamedTemporaryFile(mode="wb", dir=out_dir, prefix=out_name + ".", suffix=".part", delete=False)
        except OSError as e:
            raise SystemExit(f"{args.output}: {e.strerror}")
        try:
            with dst:
                total = trim(src, dst, args.seconds)
            os.replace(dst.name, args.output)
        except BaseException:
            try:
                os.remove(dst.name)
            except OSError:
                pass
            raise
    print(f"wrote {args.output} ({total} bytes)")


if __name__ == "__main__":
    sys.exit(main())
