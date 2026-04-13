#!/usr/bin/env python3
"""Extract libil2cpp.so and global-metadata.dat from a Unity/IL2CPP APK.

Usage:
    python extract.py path/to/game.apk [output_dir]

Extracts the binary and metadata, then runs Il2CppDumper if available.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# Paths inside the APK
BINARY_PATHS = [
    "lib/arm64-v8a/libil2cpp.so",
    "lib/armeabi-v7a/libil2cpp.so",
    "lib/x86_64/libil2cpp.so",
    "lib/x86/libil2cpp.so",
]
METADATA_PATH = "assets/bin/Data/Managed/Metadata/global-metadata.dat"


def extract_apk(apk_path: str, output_dir: str = "extracted") -> tuple[str, str]:
    """Extract binary and metadata from APK. Returns (binary_path, metadata_path)."""
    apk_path = Path(apk_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not apk_path.exists():
        print(f"Error: APK not found: {apk_path}")
        sys.exit(1)

    if not zipfile.is_zipfile(apk_path):
        print(f"Error: Not a valid APK/ZIP file: {apk_path}")
        sys.exit(1)

    binary_path = None
    metadata_path = None

    with zipfile.ZipFile(apk_path, "r") as apk:
        names = apk.namelist()

        # Find the binary — prefer arm64
        for candidate in BINARY_PATHS:
            if candidate in names:
                apk.extract(candidate, output_dir)
                binary_path = output_dir / candidate
                print(f"Extracted: {candidate}")
                break

        if binary_path is None:
            print("Error: No libil2cpp.so found in APK.")
            print("This might not be a Unity/IL2CPP game.")
            sys.exit(1)

        # Find metadata
        if METADATA_PATH in names:
            apk.extract(METADATA_PATH, output_dir)
            metadata_path = output_dir / METADATA_PATH
            print(f"Extracted: {METADATA_PATH}")
        else:
            print("Error: No global-metadata.dat found in APK.")
            print("This might not be a Unity/IL2CPP game, or metadata may be encrypted.")
            sys.exit(1)

    # Copy to top-level for convenience
    top_binary = output_dir / "libil2cpp.so"
    top_metadata = output_dir / "global-metadata.dat"
    shutil.copy2(binary_path, top_binary)
    shutil.copy2(metadata_path, top_metadata)

    print(f"\nBinary:   {top_binary}")
    print(f"Metadata: {top_metadata}")

    return str(top_binary), str(top_metadata)


def run_il2cppdumper(binary_path: str, metadata_path: str, output_dir: str = "output"):
    """Run Il2CppDumper if available."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try different Il2CppDumper invocations
    commands = [
        # .NET CLI (macOS/Linux)
        ["dotnet", "Il2CppDumper.dll", binary_path, metadata_path, str(output_dir)],
        # Native exe (Windows)
        ["Il2CppDumper.exe", binary_path, metadata_path, str(output_dir)],
        # In PATH
        ["Il2CppDumper", binary_path, metadata_path, str(output_dir)],
    ]

    for cmd in commands:
        if shutil.which(cmd[0]):
            print(f"\nRunning: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True)
                print(f"\nIl2CppDumper output written to: {output_dir}/")

                # Verify
                dump_cs = output_dir / "dump.cs"
                if dump_cs.exists():
                    size = dump_cs.stat().st_size
                    print(f"dump.cs: {size:,} bytes")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Il2CppDumper failed: {e}")
                return False

    print("\nIl2CppDumper not found.")
    print("Install it from: https://github.com/Perfare/Il2CppDumper")
    print("  Windows: download .exe from releases")
    print("  macOS/Linux: dotnet Il2CppDumper.dll")
    print(f"\nManual command:")
    print(f"  Il2CppDumper {binary_path} {metadata_path} {output_dir}/")
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract.py <apk_path> [output_dir]")
        print()
        print("Extracts libil2cpp.so and global-metadata.dat from a Unity APK,")
        print("then runs Il2CppDumper if available.")
        sys.exit(1)

    apk_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted"

    binary_path, metadata_path = extract_apk(apk_path, output_dir)
    run_il2cppdumper(binary_path, metadata_path, os.path.join(output_dir, "output"))

    print("\nNext steps:")
    print("  1. Open libil2cpp.so in Ghidra")
    print("  2. Run auto-analysis (5-15 min)")
    print("  3. Script Manager > ghidra.py > point at output/script.json")
    print("  4. See setup/IL2CPP_SETUP.md for details")


if __name__ == "__main__":
    main()
