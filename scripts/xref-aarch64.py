#!/usr/bin/env python3
"""Locate ADRP/ADD (and ADR) references to a string inside a stripped AArch64 ELF.

Ghidra-free xref finder for the Freebox bootchain components. Ghidra's headless
analyzer is overkill when the only question is "which code touches this string",
and these ELFs have no section headers, so most tooling gives up on them.

Usage:
    xref-aarch64.py <elf> <needle> [<needle> ...]

Prints, per matching string, every code site whose ADRP/ADD pair resolves to it,
plus the enclosing function guess (nearest preceding STP x29,x30 prologue).
"""

import re
import struct
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    path, needles = sys.argv[1], sys.argv[2:]
    blob = open(path, "rb").read()
    segments = load_segments(blob)

    text = next(s for s in segments if s["flags"] & 1)
    print(f"{path}: text vaddr={text['vaddr']:#x} size={text['filesz']:#x}\n")

    targets = find_strings(blob, segments, needles)
    if not targets:
        print("no matching strings")
        return 1

    refs = scan_xrefs(blob, text, {addr for addr, _ in targets})

    for addr, value in targets:
        sites = refs.get(addr, [])
        print(f"{addr:#012x}  {value!r}")
        for site in sites:
            fn = guess_function(blob, text, site)
            print(f"    xref @ {site:#012x}   (in func ~{fn:#012x})")
        if not sites:
            print("    no ADRP/ADD xref found (may be reached via table or literal pool)")
        print()
    return 0


def load_segments(blob: bytes) -> list[dict]:
    e_phoff, = struct.unpack_from("<Q", blob, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 0x36)
    out = []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", blob, o)
        p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from("<QQQQQQ", blob, o + 8)
        if p_filesz:
            out.append({"type": p_type, "flags": p_flags, "off": p_offset,
                        "vaddr": p_vaddr, "filesz": p_filesz})
    return out


def find_strings(blob: bytes, segments: list[dict], needles: list[str]) -> list[tuple[int, str]]:
    hits = []
    for seg in segments:
        chunk = blob[seg["off"]:seg["off"] + seg["filesz"]]
        for m in re.finditer(rb"[ -~]{4,}", chunk):
            value = m.group().decode()
            if any(n in value for n in needles):
                hits.append((seg["vaddr"] + m.start(), value))
    return hits


def scan_xrefs(blob: bytes, text: dict, wanted: set[int]) -> dict[int, list[int]]:
    """Walk the text segment tracking ADRP page values per register."""
    code = blob[text["off"]:text["off"] + text["filesz"]]
    base = text["vaddr"]
    pages: dict[int, tuple[int, int]] = {}  # reg -> (page, pc_of_adrp)
    refs: dict[int, list[int]] = {}

    for off in range(0, len(code) - 3, 4):
        word, = struct.unpack_from("<I", code, off)
        pc = base + off

        # ADR / ADRP share bits[28:24] == 0b10000; bit31 picks which.
        if (word >> 24) & 0x1F == 0x10:
            rd = word & 0x1F
            imm = ((word >> 5) & 0x7FFFF) << 2 | ((word >> 29) & 3)
            imm = sign_extend(imm, 21)
            if word >> 31:
                pages[rd] = ((pc & ~0xFFF) + (imm << 12), pc)
            else:
                record(refs, pc + imm, pc, wanted)
                pages.pop(rd, None)
            continue

        # ADD (immediate), 64-bit, shift=0  ->  top 10 bits 1001000100
        if (word >> 22) & 0x3FF == 0x244:
            rd, rn = word & 0x1F, (word >> 5) & 0x1F
            imm12 = (word >> 10) & 0xFFF
            if rn in pages:
                page, _ = pages[rn]
                record(refs, page + imm12, pc, wanted)
                if rd != rn:
                    pages.pop(rd, None)
                continue

        # Any other write to a register invalidates our tracked page.
        rd = word & 0x1F
        pages.pop(rd, None)

    return refs


def record(refs: dict[int, list[int]], addr: int, pc: int, wanted: set[int]) -> None:
    if addr in wanted:
        refs.setdefault(addr, []).append(pc)


def guess_function(blob: bytes, text: dict, site: int) -> int:
    """Nearest preceding `stp x29, x30, [sp, #-N]!` — the standard prologue."""
    code = blob[text["off"]:text["off"] + text["filesz"]]
    off = site - text["vaddr"]
    for probe in range(off & ~3, max(0, off - 0x2000), -4):
        word, = struct.unpack_from("<I", code, probe)
        # STP x29,x30,[sp,#imm]! pre-index, 64-bit: 1010 1001 1[imm7]11110 11111 11101
        if (word >> 22) & 0x3FF == 0x2A6 and (word & 0x1F) == 29 and ((word >> 10) & 0x1F) == 30:
            return text["vaddr"] + probe
    return text["vaddr"] + (off & ~3)


def sign_extend(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


if __name__ == "__main__":
    sys.exit(main())
