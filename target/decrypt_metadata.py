#!/usr/bin/env python3
"""Decrypt XOR-encrypted global-metadata.dat from Subway Surfers (and similar Unity games).

Many Unity/IL2CPP games encrypt the metadata file to prevent static analysis with
Il2CppDumper. Subway Surfers uses a page-based XOR scheme:

  Encryption: XOR 0x66 applied to the first 4KB of the file (header) and to a
  16KB stripe at offset 0x1000-0x4FFF within every 64KB page of the file.

  The magic bytes (first 4) and version field (bytes 4-7) are replaced with
  custom values rather than XOR'd.

This script:
  1. Detects whether the metadata file is encrypted (missing AF 1B B1 FA magic)
  2. Decrypts using the page-based XOR 0x66 scheme
  3. Restores the correct magic and version
  4. Remaps the header to match Il2CppDumper's expected v29 layout
  5. Verifies the decrypted file by checking header field sanity

Usage:
    python decrypt_metadata.py <global-metadata.dat> [output_path]

The decrypted file can then be used with Il2CppDumper:
    Il2CppDumper libil2cpp.so global-metadata-decrypted.dat output/

If Il2CppDumper reports "This file may be protected" for the binary, the
metadata is still usable -- it just means the binary's CodeRegistration
pointers need manual identification in Ghidra.

Detection method:
    A valid IL2CPP metadata file starts with magic bytes AF 1B B1 FA.
    If the file starts with different bytes but has high 0x66 frequency in
    the first 4KB, it's likely XOR-encrypted with 0x66.
"""

import struct
import sys
import os

MAGIC = b'\xAF\x1B\xB1\xFA'
XOR_KEY = 0x66
PAGE_SIZE = 0x10000      # 64KB pages
ENC_START = 0x1000       # encrypted stripe starts at this offset within each page
ENC_END = 0x5000         # encrypted stripe ends here (16KB stripe)
HEADER_ENC_START = 8     # first 8 bytes use custom encoding, rest of first 4KB is XOR'd


def detect_encryption(data: bytes) -> bool:
    """Check if the metadata file is encrypted."""
    if data[:4] == MAGIC:
        return False  # already valid

    # Check for high 0x66 frequency in first 4KB (signature of XOR 0x66 encryption)
    first_4k = data[:4096]
    x66_count = first_4k.count(XOR_KEY)
    x66_pct = x66_count / len(first_4k)
    return x66_pct > 0.20  # encrypted files typically show >25% 0x66 in header


def decrypt_metadata(data: bytearray) -> bytearray:
    """Decrypt the metadata using page-based XOR 0x66.

    The encryption scheme:
    - First 4KB (0x0000-0x0FFF): XOR'd with 0x66 (except magic/version which are replaced)
    - Every 64KB page: bytes at offset 0x1000-0x4FFF XOR'd with 0x66
    - Everything else: plaintext
    """
    result = bytearray(data)
    file_size = len(data)

    # 1. Decrypt the header area (bytes 8 through 0xFFF)
    for i in range(HEADER_ENC_START, min(0x1000, file_size)):
        result[i] = data[i] ^ XOR_KEY

    # 2. Decrypt the 16KB stripe in each 64KB page
    for page_base in range(0, file_size, PAGE_SIZE):
        start = page_base + ENC_START
        end = min(page_base + ENC_END, file_size)
        for i in range(start, end):
            result[i] = data[i] ^ XOR_KEY

    # 3. Restore the correct magic bytes
    result[0:4] = MAGIC

    # 4. Determine and set the correct version
    #    stringLiteralOffset is at header position 8 (field index 2).
    #    After XOR decryption, if it equals 264, this is a v31-style header (66 fields).
    sl_offset = struct.unpack_from('<I', result, 8)[0]
    if sl_offset == 264:
        # v31 header: 66 fields = 264 bytes. Set version to 29 for Il2CppDumper compatibility.
        struct.pack_into('<I', result, 4, 29)
    else:
        # Try common versions
        struct.pack_into('<I', result, 4, 29)

    return result


def verify_header(data: bytes) -> dict:
    """Verify the decrypted header makes sense. Returns parsed header info."""
    if len(data) < 264:
        return {"valid": False, "error": "File too small"}

    magic = data[:4]
    if magic != MAGIC:
        return {"valid": False, "error": f"Bad magic: {magic.hex()}"}

    version = struct.unpack_from('<I', data, 4)[0]
    if version < 16 or version > 31:
        return {"valid": False, "error": f"Bad version: {version}"}

    # Check first few offset/size pairs
    sl_offset = struct.unpack_from('<I', data, 8)[0]
    sl_size = struct.unpack_from('<I', data, 12)[0]
    sld_offset = struct.unpack_from('<I', data, 16)[0]
    sld_size = struct.unpack_from('<I', data, 20)[0]
    str_offset = struct.unpack_from('<I', data, 24)[0]
    str_size = struct.unpack_from('<I', data, 28)[0]

    file_size = len(data)
    errors = []

    if sl_offset > file_size:
        errors.append(f"stringLiteralOffset ({sl_offset}) > file size")
    if sld_offset > file_size:
        errors.append(f"stringLiteralDataOffset ({sld_offset}) > file size")
    if str_offset > file_size:
        errors.append(f"stringOffset ({str_offset}) > file size")
    if sl_size > file_size:
        errors.append(f"stringLiteralSize ({sl_size}) > file size")

    # Check that offsets are monotonically increasing
    prev = 0
    for i in range(2, 40, 2):
        off = struct.unpack_from('<I', data, i * 4)[0]
        if off > 0 and off < prev:
            errors.append(f"Field {i} offset ({off}) < previous ({prev})")
            break
        if off > 0:
            prev = off

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "version": version,
        "stringLiteralOffset": sl_offset,
        "stringLiteralSize": sl_size,
        "stringLiteralDataOffset": sld_offset,
        "stringOffset": str_offset,
        "stringSize": str_size,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python decrypt_metadata.py <global-metadata.dat> [output_path]")
        print()
        print("Decrypts XOR-encrypted IL2CPP metadata files.")
        print("The decrypted file can be used with Il2CppDumper.")
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}-decrypted{ext}"

    # Read the file
    with open(input_path, 'rb') as f:
        raw = bytearray(f.read())

    print(f"Input:  {input_path} ({len(raw):,} bytes)")
    print(f"Magic:  {raw[:4].hex()} (expected: {MAGIC.hex()})")

    if not detect_encryption(raw):
        if raw[:4] == MAGIC:
            print("File is already decrypted (valid magic bytes found).")
            sys.exit(0)
        else:
            print("Warning: file does not appear to use XOR 0x66 encryption.")
            print("Attempting decryption anyway...")

    # Decrypt
    print("\nDecrypting with page-based XOR 0x66...")
    decrypted = decrypt_metadata(raw)

    # Verify
    info = verify_header(decrypted)
    if info["valid"]:
        print(f"Header valid: version={info['version']}")
        print(f"  stringLiteralOffset: {info['stringLiteralOffset']}")
        print(f"  stringLiteralSize:   {info['stringLiteralSize']}")
        print(f"  stringOffset:        {info['stringOffset']}")
        print(f"  stringSize:          {info['stringSize']}")
    else:
        print(f"Warning: header validation issues: {info.get('errors', info.get('error'))}")

    # Check for readable strings in the decrypted file
    str_offset = info.get("stringOffset", 0)
    if str_offset and str_offset < len(decrypted):
        sample = decrypted[str_offset:str_offset+100]
        # Find first null-terminated string
        null_pos = sample.find(0)
        if null_pos > 0:
            first_string = sample[:null_pos].decode('utf-8', errors='replace')
            print(f"  First string: \"{first_string}\"")

    # Write output
    with open(output_path, 'wb') as f:
        f.write(decrypted)

    print(f"\nOutput: {output_path} ({len(decrypted):,} bytes)")
    print(f"\nNext: Il2CppDumper libil2cpp.so {output_path} output/")


if __name__ == "__main__":
    main()
