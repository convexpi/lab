#!/usr/bin/env python3
"""Clear the PT_GNU_STACK executable bit on ELF shared objects under a directory.

Julia's bundled libraries (notably libopenlibm.so) are flagged as requiring an executable stack.
The sandboxed grader container refuses that at load time ("cannot enable executable stack as shared
object requires: Invalid argument"), so Julia cannot boot. The classic fix is `execstack -c`, but
that tool was removed from Debian bookworm — so we clear the flag directly. ELF64, x86_64 only,
which is what the grader image uses.

Usage: python3 clear_execstack.py <dir> [<dir> ...]
"""
import os
import struct
import sys

PT_GNU_STACK = 0x6474E551
PF_X = 0x1


def clear_in_file(path: str) -> bool:
    with open(path, "r+b") as f:
        data = bytearray(f.read())
        if data[:4] != b"\x7fELF" or data[4] != 2:  # ELF64 only
            return False
        enc = "<" if data[5] == 1 else ">"
        e_phoff = struct.unpack_from(enc + "Q", data, 0x20)[0]
        e_phentsize = struct.unpack_from(enc + "H", data, 0x36)[0]
        e_phnum = struct.unpack_from(enc + "H", data, 0x38)[0]
        changed = False
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            if struct.unpack_from(enc + "I", data, off)[0] == PT_GNU_STACK:
                flags_off = off + 4  # p_flags immediately follows p_type in ELF64
                flags = struct.unpack_from(enc + "I", data, flags_off)[0]
                if flags & PF_X:
                    struct.pack_into(enc + "I", data, flags_off, flags & ~PF_X)
                    changed = True
        if changed:
            f.seek(0)
            f.write(data)
        return changed


def main(dirs):
    cleared = 0
    for root in dirs:
        for dirpath, _, files in os.walk(root):
            for name in files:
                if ".so" not in name:
                    continue
                path = os.path.join(dirpath, name)
                try:
                    if clear_in_file(path):
                        print("cleared execstack:", path)
                        cleared += 1
                except Exception as exc:  # never fail the build over one odd file
                    print("skip", path, exc)
    print(f"clear_execstack: cleared {cleared} library/libraries")


if __name__ == "__main__":
    main(sys.argv[1:] or ["."])
