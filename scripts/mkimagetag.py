#!/usr/bin/env python3
"""Build and validate Freebox Player bank images (the `snapl` imagetag container).

`verify` is a faithful reimplementation of snapl's `boot_from_tag()`
(`comp08` @ 0x9fa09aa0), gate for gate, so an image can be checked offline before
it is ever served to a device. It takes the boot mode as an argument because that
argument is what decides whether signatures are enforced:

    mode 1  -> normal flash boot   (caller 0x9fa0a40c) -> signature required
    mode 0  -> network test-mode   (caller 0x9fa0acd0) -> unsigned images accepted

Field layout was recovered from the parser and confirmed against Free's own
production image (fbx7hd_bank1 1.5.24.2), whose partitions carry flags 0x5/0x5/0x1.

Usage:
    mkimagetag.py build --kernel Image --dtb board.dtb -o bank.img [--signed-flag]
    mkimagetag.py verify bank.img [--mode 0|1]
"""

import argparse
import struct
import sys
import zlib

MAGIC = 0x3658382B
VERSION = 2
PART_ARRAY = 0xBC
PART_STRIDE = 0x2C
MAX_PARTS = 8
CRC_LEN = 0x214
PAYLOAD_START = 0x1000
DTB_MAX = 0x400000

TYPE_KERNEL, TYPE_ROOTFS, TYPE_DTB = 0, 1, 3
FLAG_SIGNED, FLAG_COMPRESSED = 0x1, 0x4
FLAG_MASK = 0xFFFFFFFA  # snapl rejects any flag outside bits 0 and 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="pack a kernel + DTB into a bank image")
    build.add_argument("--kernel", required=True)
    build.add_argument("--dtb", required=True)
    build.add_argument("-o", "--out", required=True)
    build.add_argument("--signed-flag", action="store_true",
                       help="set flags bit 0 (claims signed; snapl will then demand a real signature)")

    check = sub.add_parser("verify", help="replay snapl's boot_from_tag() gates")
    check.add_argument("image")
    check.add_argument("--mode", type=int, choices=(0, 1), default=0)

    args = parser.parse_args()
    if args.cmd == "build":
        return build_image(args.kernel, args.dtb, args.out, args.signed_flag)
    return verify_image(args.image, args.mode)


def build_image(kernel_path: str, dtb_path: str, out_path: str, signed: bool) -> int:
    kernel = open(kernel_path, "rb").read()
    dtb = open(dtb_path, "rb").read()
    flags = FLAG_SIGNED if signed else 0

    kernel_off = PAYLOAD_START
    dtb_off = align(kernel_off + len(kernel), 0x1000)
    total = align(dtb_off + len(dtb), 0x1000)

    parts = [
        ("kernel", kernel_off, len(kernel), TYPE_KERNEL, flags),
        ("qcom-dtbs", dtb_off, len(dtb), TYPE_DTB, flags),
    ]

    header = bytearray(PAYLOAD_START)
    struct.pack_into(">III", header, 4, MAGIC, VERSION, total)
    struct.pack_into(">I", header, 0xB4, len(parts))
    for i, (name, off, size, ptype, pflags) in enumerate(parts):
        base = PART_ARRAY + i * PART_STRIDE
        struct.pack_into(">IIII", header, base, off, size, ptype, pflags)
        header[base + 0x18: base + 0x18 + len(name)] = name.encode()

    struct.pack_into(">I", header, 0, tag_crc(bytes(header)))

    image = bytearray(total)
    image[:PAYLOAD_START] = header
    image[kernel_off:kernel_off + len(kernel)] = kernel
    image[dtb_off:dtb_off + len(dtb)] = dtb
    open(out_path, "wb").write(image)

    print(f"wrote {out_path}  ({total:,} bytes)")
    for name, off, size, ptype, pflags in parts:
        print(f"  {name:12} off={off:#010x} size={size:>12,} type={ptype} flags={pflags:#06x}"
              f"  {'SIGNE' if pflags & FLAG_SIGNED else 'NON SIGNE'}")
    if not signed:
        print("\n-> partitions non signees : acceptees uniquement en mode 0 (test-mode).")
    return 0


def verify_image(path: str, mode: int) -> int:
    """Replay each gate in the order snapl applies them."""
    blob = open(path, "rb").read()
    loaded = len(blob)
    ok = True

    def gate(label: str, passed: bool, detail: str = "") -> bool:
        nonlocal ok
        print(f"  [{'OK ' if passed else 'ECHEC'}] {label}{'  ' + detail if detail else ''}")
        ok = ok and passed
        return passed

    print(f"boot_from_tag(tag, size={loaded:#x}, mode={mode})\n")

    magic, version, total = struct.unpack_from(">III", blob, 4)
    if not gate("magic 0x3658382b", magic == MAGIC, f"lu {magic:#010x}"):
        return 1
    if not gate("version == 2", version == VERSION, f"lu {version}"):
        return 1
    if not gate("taille chargee >= total declare", loaded >= total,
                f"{loaded:#x} >= {total:#x}"):
        return 1

    nparts, = struct.unpack_from(">I", blob, 0xB4)
    if not gate(f"nb partitions <= {MAX_PARTS}", nparts <= MAX_PARTS, f"lu {nparts}"):
        return 1
    gate("CRC32 de l'en-tete", tag_crc(blob) == struct.unpack_from(">I", blob, 0)[0])

    parts = {}
    for i in range(nparts):
        base = PART_ARRAY + i * PART_STRIDE
        off, size, ptype, flags = struct.unpack_from(">IIII", blob, base)
        name = blob[base + 0x18: base + 0x28].split(b"\0")[0].decode(errors="replace")
        gate(f"partition {i} ({name}) dans les bornes",
             off <= total and size <= total and off + size <= total)
        gate(f"partition {i} flags autorises", not flags & FLAG_MASK, f"{flags:#06x}")
        gate(f"partition {i} type connu", ptype <= 3, f"type {ptype}")
        parts[ptype] = (name, flags)

    if not gate("partition Kernel presente", TYPE_KERNEL in parts):
        return 1
    if not gate("partition DTB presente", TYPE_DTB in parts):
        return 1

    print()
    return report_signature_policy(parts, mode, ok)


def report_signature_policy(parts: dict, mode: int, ok: bool) -> int:
    """The branch at 0x9fa09c8c — the whole point of this tool."""
    kernel_signed = bool(parts[TYPE_KERNEL][1] & FLAG_SIGNED)
    dtb_signed = bool(parts[TYPE_DTB][1] & FLAG_SIGNED)
    print(f"politique de signature (branchement @ 0x9fa09c8c) — mode={mode}")
    print(f"  kernel flags bit0 = {int(kernel_signed)}   dtb flags bit0 = {int(dtb_signed)}")

    if mode != 0:
        if not (kernel_signed and dtb_signed):
            print("  -> mode != 0 et image non signee : REJET")
            print('     "bad kernel or DTB for current bootmode."')
            return 1
        print("  -> verify_signature() APPELE : il faut une vraie signature RSA")
        return 0 if ok else 1

    if not kernel_signed:
        print("  -> mode 0 + kernel non signe : saut vers 0x9fa09cec")
        print("     verify_signature() N'EST JAMAIS APPELE")
    else:
        print("  -> kernel se declare signe : verification exigee malgre le mode 0")
    if not dtb_signed:
        print("  -> DTB non signe : verification sautee aussi (tbz w0,#0 @ 0x9fa09d30)")
    print(f"\n  VERDICT : {'image acceptee sans signature' if not kernel_signed else 'signature requise'}")
    return 0 if ok else 1


def tag_crc(blob: bytes) -> int:
    """snapl seeds with 0xFFFFFFFF and returns the raw register (no final inversion)."""
    return zlib.crc32(blob[4:4 + CRC_LEN], 0) ^ 0xFFFFFFFF


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


if __name__ == "__main__":
    sys.exit(main())
