#!/usr/bin/env python3
"""Parse IL2CPP global-metadata.dat directly into script.json, dump.cs, and stringliteral.json.

Bypasses Il2CppDumper entirely. Reads the decrypted metadata file, parses all
type definitions, method definitions, field definitions, and string literals,
then writes output files with correct class-to-method mapping.

Usage:
    python parse_metadata.py <metadata_path> [output_dir]

Example:
    python parse_metadata.py /tmp/subway-extracted/global-metadata-final.dat metadata/
"""

import json
import os
import struct
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Metadata header layout
# ---------------------------------------------------------------------------

MAGIC = 0xFAB11BAF

# Header field indices (each is an offset/size pair at header position 8 + i*8)
HDR_STRING_LITERAL = 0
HDR_STRING_LITERAL_DATA = 1
HDR_STRING = 2
HDR_EVENTS = 3
HDR_PROPERTIES = 4
HDR_METHODS = 5
HDR_PARAM_DEFAULT_VALUES = 6
HDR_FIELD_DEFAULT_VALUES = 7
HDR_FIELD_PARAM_DEFAULT_DATA = 8
HDR_FIELD_MARSHALED_SIZES = 9
HDR_PARAMETERS = 10
HDR_FIELDS = 11
HDR_GENERIC_PARAMETERS = 12
HDR_GENERIC_PARAM_CONSTRAINTS = 13
HDR_GENERIC_CONTAINERS = 14
HDR_NESTED_TYPES = 15
HDR_INTERFACES = 16
HDR_VTABLE_METHODS = 17
HDR_INTERFACE_OFFSETS = 18
HDR_TYPE_DEFINITIONS = 19
HDR_IMAGES = 20
HDR_ASSEMBLIES = 21

# Struct sizes (determined empirically for this v29 metadata)
TYPEDEF_SIZE = 92
METHOD_SIZE = 32
FIELD_SIZE = 12
PARAM_SIZE = 12
IMAGE_SIZE = 40


# ---------------------------------------------------------------------------
# Low-level readers
# ---------------------------------------------------------------------------

class MetadataReader:
    """Reads IL2CPP metadata structures from a decrypted global-metadata.dat."""

    def __init__(self, path: str):
        with open(path, "rb") as f:
            self.data = f.read()

        self._parse_header()

    # -- header --

    def _parse_header(self):
        magic = self._u32(0)
        if magic != MAGIC:
            raise ValueError(
                f"Bad magic: 0x{magic:08X} (expected 0x{MAGIC:08X}). "
                "Is the metadata decrypted?"
            )

        self.version = self._i32(4)
        if self.version not in (24, 27, 29, 31):
            print(f"Warning: metadata version {self.version} — parser tested on v29")

        # Read all offset/size pairs
        self.sections: dict[int, tuple[int, int]] = {}
        for i in range(32):
            off = self._i32(8 + i * 8)
            size = self._i32(8 + i * 8 + 4)
            self.sections[i] = (off, size)

        self.string_offset, self.string_size = self.sections[HDR_STRING]
        self.sl_offset, self.sl_size = self.sections[HDR_STRING_LITERAL]
        self.sld_offset, self.sld_size = self.sections[HDR_STRING_LITERAL_DATA]
        self.method_offset, self.method_size = self.sections[HDR_METHODS]
        self.typedef_offset, self.typedef_size = self.sections[HDR_TYPE_DEFINITIONS]
        self.field_offset, self.field_size = self.sections[HDR_FIELDS]
        self.param_offset, self.param_size = self.sections[HDR_PARAMETERS]
        self.image_offset, self.image_size = self.sections[HDR_IMAGES]

        # Detect typedef size — try 92 first (v29 without extra trailing fields),
        # then 132 (v29 with bitfield+token after uint16 block)
        self.typedef_stride = self._detect_typedef_stride()

        self.type_count = self.typedef_size // self.typedef_stride
        self.method_count = self.method_size // METHOD_SIZE
        self.field_count = self.field_size // FIELD_SIZE
        self.param_count = self.param_size // PARAM_SIZE
        self.image_count = self.image_size // IMAGE_SIZE

    def _detect_typedef_stride(self) -> int:
        """Detect the correct typeDefinition struct size by probing the string table."""
        # Type 0 is always <Module>. Type 1 should be the first real class.
        # We know type 0's nameIndex from offset 0 of the typedef table.
        # Try strides of 92 and 132: whichever gives a valid string for type 1 wins.
        for candidate in (92, 132):
            if self.typedef_size % candidate != 0:
                continue
            base = self.typedef_offset + candidate
            name_idx = self._i32(base)
            if 0 <= name_idx < self.string_size:
                name = self.get_string(name_idx)
                if name and all(c.isprintable() for c in name):
                    return candidate
        # fallback
        return 92

    # -- primitive reads --

    def _i32(self, offset: int) -> int:
        return struct.unpack_from("<i", self.data, offset)[0]

    def _u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, offset)[0]

    def _u16(self, offset: int) -> int:
        return struct.unpack_from("<H", self.data, offset)[0]

    # -- string table --

    def get_string(self, name_index: int) -> str:
        if name_index < 0 or name_index >= self.string_size:
            return ""
        start = self.string_offset + name_index
        end = self.data.index(b"\x00", start)
        return self.data[start:end].decode("utf-8", errors="replace")

    # -- images --

    def read_images(self) -> list[dict]:
        images = []
        for i in range(self.image_count):
            base = self.image_offset + i * IMAGE_SIZE
            name_idx = self._i32(base)
            assembly_idx = self._i32(base + 4)
            type_start = self._i32(base + 8)
            type_count = self._u32(base + 12)
            # remaining fields vary by version
            name = self.get_string(name_idx)
            images.append({
                "index": i,
                "name": name,
                "assemblyIndex": assembly_idx,
                "typeStart": type_start,
                "typeCount": type_count,
            })
        return images

    # -- type definitions --

    def read_typedef(self, index: int) -> dict:
        """Read a single typeDefinition by index."""
        base = self.typedef_offset + index * self.typedef_stride
        s = self.typedef_stride

        # The v29 92-byte layout:
        #   17 x int32  (offsets 0..67)  = 68 bytes
        #   8  x uint16 (offsets 68..83) = 16 bytes
        #   2  x uint32 (offsets 84..91) = 8 bytes
        # Total = 92

        name_idx = self._i32(base + 0)
        ns_idx = self._i32(base + 4)
        byval_type = self._i32(base + 8)
        byref_type = self._i32(base + 12)
        declaring_type = self._i32(base + 16)
        parent_idx = self._i32(base + 20)
        element_type = self._i32(base + 24)
        generic_container = self._i32(base + 28)
        flags = self._u32(base + 32)
        field_start = self._i32(base + 36)
        method_start = self._i32(base + 40)
        event_start = self._i32(base + 44)
        property_start = self._i32(base + 48)
        nested_start = self._i32(base + 52)
        interfaces_start = self._i32(base + 56)
        vtable_start = self._i32(base + 60)
        iface_offsets_start = self._i32(base + 64)

        method_count = self._u16(base + 68)
        property_count = self._u16(base + 70)
        field_count = self._u16(base + 72)
        event_count = self._u16(base + 74)
        nested_count = self._u16(base + 76)
        vtable_count = self._u16(base + 78)
        interfaces_count = self._u16(base + 80)
        iface_offsets_count = self._u16(base + 82)

        bitfield = self._u32(base + 84)
        token = self._u32(base + 88)

        name = self.get_string(name_idx)
        namespace = self.get_string(ns_idx) if ns_idx >= 0 else ""

        return {
            "index": index,
            "name": name,
            "namespace": namespace,
            "nameIndex": name_idx,
            "namespaceIndex": ns_idx,
            "flags": flags,
            "fieldStart": field_start,
            "methodStart": method_start,
            "propertyStart": property_start,
            "eventStart": event_start,
            "nestedStart": nested_start,
            "parentIndex": parent_idx,
            "declaringTypeIndex": declaring_type,
            "genericContainerIndex": generic_container,
            "method_count": method_count,
            "property_count": property_count,
            "field_count": field_count,
            "event_count": event_count,
            "nested_count": nested_count,
            "vtable_count": vtable_count,
            "interfaces_count": interfaces_count,
            "token": token,
            "bitfield": bitfield,
        }

    # -- method definitions --

    def read_method(self, index: int) -> dict:
        """Read a single methodDef by index."""
        base = self.method_offset + index * METHOD_SIZE
        name_idx = self._i32(base + 0)
        declaring_type = self._i32(base + 4)
        return_type = self._i32(base + 8)
        param_start = self._i32(base + 12)
        generic_container = self._i32(base + 16)
        token = self._u32(base + 20)
        flags = self._u16(base + 24)
        iflags = self._u16(base + 26)
        slot = self._u16(base + 28)
        param_count = self._u16(base + 30)

        name = self.get_string(name_idx)

        return {
            "index": index,
            "name": name,
            "nameIndex": name_idx,
            "declaringType": declaring_type,
            "returnType": return_type,
            "parameterStart": param_start,
            "genericContainerIndex": generic_container,
            "token": token,
            "flags": flags,
            "iflags": iflags,
            "slot": slot,
            "parameterCount": param_count,
        }

    # -- field definitions --

    def read_field(self, index: int) -> dict:
        base = self.field_offset + index * FIELD_SIZE
        name_idx = self._i32(base + 0)
        type_idx = self._i32(base + 4)
        token = self._u32(base + 8)
        name = self.get_string(name_idx)
        return {
            "index": index,
            "name": name,
            "nameIndex": name_idx,
            "typeIndex": type_idx,
            "token": token,
        }

    # -- parameter definitions --

    def read_param(self, index: int) -> dict:
        base = self.param_offset + index * PARAM_SIZE
        name_idx = self._i32(base + 0)
        type_idx = self._i32(base + 4)
        token = self._u32(base + 8)
        name = self.get_string(name_idx)
        return {
            "index": index,
            "name": name,
            "nameIndex": name_idx,
            "typeIndex": type_idx,
            "token": token,
        }

    # -- string literals --

    def read_string_literals(self) -> list[dict]:
        """Read string literal table. Returns valid entries only."""
        count = self.sl_size // 8
        literals = []
        for i in range(count):
            base = self.sl_offset + i * 8
            data_idx = self._i32(base)
            length = self._i32(base + 4)

            # Validate — partially encrypted tables have garbage past a certain point
            if data_idx < 0 or length < 0 or data_idx + length > self.sld_size:
                continue

            start = self.sld_offset + data_idx
            raw = self.data[start : start + length]
            try:
                value = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            literals.append({
                "index": i,
                "value": value,
                "dataIndex": data_idx,
                "length": length,
            })
        return literals


# ---------------------------------------------------------------------------
# High-level assembly
# ---------------------------------------------------------------------------

def full_class_name(td: dict) -> str:
    ns = td["namespace"]
    name = td["name"]
    if ns:
        return f"{ns}.{name}"
    return name


def method_il2cpp_name(class_name: str, method_name: str) -> str:
    """Build the ClassName$$MethodName format used by Il2CppDumper / GhidraMCP."""
    # IL2CPP naming: replace dots with underscores in the class path,
    # then join with $$ for the method.
    sanitized = class_name.replace(".", "_").replace("<", "_").replace(">", "_")
    return f"{sanitized}$${method_name}"


def access_string(flags: int) -> str:
    """Derive access modifier from IL2CPP flags (CIL MethodAttributes / TypeAttributes)."""
    access = flags & 0x7
    if access == 6:
        return "public"
    elif access == 5:
        return "internal"
    elif access == 4:
        return "protected"
    elif access == 3:
        return "protected internal"
    elif access == 1:
        return "private"
    return ""


def type_access_string(flags: int) -> str:
    vis = flags & 0x7
    if vis in (1, 2):  # Public, NestedPublic
        return "public"
    elif vis == 4:  # NestedFamily
        return "protected"
    elif vis == 3:  # NestedPrivate
        return "private"
    elif vis == 5:  # NestedAssembly
        return "internal"
    return ""


def is_static(flags: int) -> bool:
    return bool(flags & 0x10)


def is_abstract(flags: int) -> bool:
    return bool(flags & 0x400)


def is_virtual(flags: int) -> bool:
    return bool(flags & 0x40)


def is_sealed_type(flags: int) -> bool:
    return bool(flags & 0x100)


def is_abstract_type(flags: int) -> bool:
    return bool(flags & 0x80)


def is_interface_type(flags: int) -> bool:
    return bool(flags & 0x20)


def is_enum_type(flags: int) -> bool:
    # Enum types have a specific semantics flag — we check parent name instead
    return False


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_script_json(reader: MetadataReader) -> dict:
    """Generate script.json with correct class-to-method mapping."""
    print(f"  Parsing {reader.type_count} types, {reader.method_count} methods...")

    # Build type lookup from method's declaringType field
    # This is the AUTHORITATIVE source for which methods belong to which class.
    type_cache: dict[int, dict] = {}
    for ti in range(reader.type_count):
        type_cache[ti] = reader.read_typedef(ti)

    script_methods = []
    for mi in range(reader.method_count):
        method = reader.read_method(mi)
        dt = method["declaringType"]
        if dt < 0 or dt >= reader.type_count:
            # Orphan method — use raw name
            il2cpp_name = method["name"]
        else:
            td = type_cache[dt]
            cls = full_class_name(td)
            il2cpp_name = method_il2cpp_name(cls, method["name"])

        # Build parameter signature
        params = []
        for pi in range(method["parameterCount"]):
            param_idx = method["parameterStart"] + pi
            if 0 <= param_idx < reader.param_count:
                p = reader.read_param(param_idx)
                params.append(p["name"] if p["name"] else f"param{pi}")
            else:
                params.append(f"param{pi}")
        param_str = ", ".join(params)

        # Use method index as address placeholder — real RVAs require
        # CodeRegistration from the binary (not available in metadata alone)
        script_methods.append({
            "Address": mi,
            "Name": il2cpp_name,
            "Signature": f"void {il2cpp_name}({param_str})",
            "MethodToken": f"0x{method['token']:08X}",
            "TypeIndex": dt,
        })

    return {
        "ScriptMethod": script_methods,
        "ScriptString": [],
        "ScriptMetadata": [],
        "ScriptMetadataMethod": [],
        "Addresses": [],
    }


def generate_dump_cs(reader: MetadataReader) -> str:
    """Generate dump.cs with correct class definitions, fields, and method lists."""
    print(f"  Generating dump.cs for {reader.type_count} types...")

    lines: list[str] = []

    # Read images for assembly grouping
    images = reader.read_images()
    # Build type-index-to-image map
    image_for_type: dict[int, dict] = {}
    for img in images:
        for ti in range(img["typeStart"], img["typeStart"] + img["typeCount"]):
            image_for_type[ti] = img

    current_image = None

    for ti in range(reader.type_count):
        td = reader.read_typedef(ti)
        cls = full_class_name(td)

        # Image / assembly header
        img = image_for_type.get(ti)
        if img and img != current_image:
            current_image = img
            lines.append(f"// Image: {img['name']}")
            lines.append("")

        # Namespace comment
        if td["namespace"]:
            lines.append(f"// Namespace: {td['namespace']}")

        # Type kind
        type_flags = td["flags"]
        access = type_access_string(type_flags)
        modifiers = []
        if access:
            modifiers.append(access)
        if is_abstract_type(type_flags):
            modifiers.append("abstract")
        if is_sealed_type(type_flags):
            modifiers.append("sealed")

        if is_interface_type(type_flags):
            modifiers.append("interface")
        else:
            modifiers.append("class")

        modifier_str = " ".join(modifiers)
        lines.append(f"{modifier_str} {td['name']} // TypeDefIndex: {ti}")
        lines.append("{")

        # Fields
        if td["field_count"] > 0 and td["fieldStart"] >= 0:
            for fi in range(td["field_count"]):
                field_idx = td["fieldStart"] + fi
                if field_idx >= reader.field_count:
                    break
                field = reader.read_field(field_idx)
                lines.append(f"\t{field['name']}; // 0x{field['token']:08X}")

        # Methods — use the type's methodStart + method_count (primary source)
        # AND cross-check with the method's declaringType field
        if td["method_count"] > 0 and td["methodStart"] >= 0:
            if td["field_count"] > 0:
                lines.append("")
            for mi_off in range(td["method_count"]):
                mi = td["methodStart"] + mi_off
                if mi >= reader.method_count:
                    break
                method = reader.read_method(mi)
                # Verify declaring type matches
                if method["declaringType"] != ti:
                    lines.append(
                        f"\t// WARNING: method {method['name']} has declaringType="
                        f"{method['declaringType']}, expected {ti}"
                    )

                # Build parameter list
                params = []
                for pi in range(method["parameterCount"]):
                    param_idx = method["parameterStart"] + pi
                    if 0 <= param_idx < reader.param_count:
                        p = reader.read_param(param_idx)
                        params.append(p["name"] if p["name"] else f"param{pi}")
                    else:
                        params.append(f"param{pi}")
                param_str = ", ".join(params)

                # Method modifiers
                mflags = method["flags"]
                mods = []
                acc = access_string(mflags)
                if acc:
                    mods.append(acc)
                if is_static(mflags):
                    mods.append("static")
                if is_abstract(mflags):
                    mods.append("abstract")
                elif is_virtual(mflags):
                    mods.append("virtual")
                mod_str = " ".join(mods)
                if mod_str:
                    mod_str += " "

                lines.append(
                    f"\t{mod_str}void {method['name']}({param_str}); "
                    f"// MethodIndex: {mi} Token: 0x{method['token']:08X}"
                )

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def generate_stringliteral_json(reader: MetadataReader) -> list[dict]:
    """Generate stringliteral.json from valid string literal entries.

    The IL2CPP string literal data is a single concatenated blob. Each
    entry is a (dataIndex, length) pair pointing into this blob. Entries
    can overlap — many are cumulative views of the same growing region.

    We deduplicate by value, skip empty strings and extremely long
    cumulative blobs, and filter out entries that look like garbage from
    partially encrypted metadata regions.
    """
    print("  Parsing string literals...")
    literals = reader.read_string_literals()
    print(f"  Found {len(literals)} valid string literal entries")

    MAX_LEN = 1024  # skip extremely long cumulative blobs

    result = []
    seen_values = set()
    for lit in literals:
        val = lit["value"]
        if not val or val in seen_values:
            continue
        if lit["length"] > MAX_LEN:
            continue
        # Skip strings that are mostly non-printable
        printable = sum(1 for c in val if c.isprintable() or c in "\n\r\t")
        if len(val) > 0 and printable / len(val) < 0.8:
            continue
        seen_values.add(val)
        result.append({
            "value": val,
            "address": f"0x{lit['dataIndex']:X}",
        })

    # Note: In partially decrypted metadata, the stringLiteral index table
    # may be corrupted, causing many entries to be overlapping views into
    # the same cumulative data blob. The type/method/field string tables
    # (separate from stringLiteralData) are unaffected and fully usable.
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(reader: MetadataReader, script: dict):
    """Run basic sanity checks on the generated output."""
    errors = 0

    # 1. Check method-to-type consistency
    type_cache = {}
    for ti in range(reader.type_count):
        type_cache[ti] = reader.read_typedef(ti)

    mismatches = 0
    for mi in range(reader.method_count):
        method = reader.read_method(mi)
        dt = method["declaringType"]
        if dt < 0 or dt >= reader.type_count:
            continue
        td = type_cache[dt]
        # Method should be within [methodStart, methodStart + method_count)
        if td["methodStart"] >= 0:
            if not (td["methodStart"] <= mi < td["methodStart"] + td["method_count"]):
                mismatches += 1

    if mismatches > 0:
        print(f"  WARNING: {mismatches} methods have declaringType mismatch "
              f"with their type's methodStart range")
        errors += 1
    else:
        print("  OK: All methods consistent with their declaring type")

    # 2. Check coin-related classes exist and have methods
    coin_classes = []
    for sm in script["ScriptMethod"]:
        name_lower = sm["Name"].lower()
        if "coinmanager" in name_lower:
            coin_classes.append(sm["Name"])

    if coin_classes:
        print(f"  OK: Found {len(coin_classes)} CoinManager methods:")
        for c in coin_classes[:5]:
            print(f"       {c}")
        if len(coin_classes) > 5:
            print(f"       ... and {len(coin_classes) - 5} more")
    else:
        print("  WARNING: No CoinManager methods found")
        errors += 1

    # 3. Spot-check that game classes aren't mixed with framework classes
    newtonsoft_methods = [
        sm for sm in script["ScriptMethod"]
        if "Newtonsoft" in sm["Name"]
    ]
    game_in_newtonsoft = [
        m for m in newtonsoft_methods
        if any(term in m["Name"].lower() for term in ["coin", "subway", "player"])
    ]
    if game_in_newtonsoft:
        print(f"  WARNING: {len(game_in_newtonsoft)} game methods incorrectly "
              f"assigned to Newtonsoft classes")
        errors += 1
    else:
        print("  OK: No game methods cross-contaminating Newtonsoft classes")

    # 4. Check total counts
    print(f"\n  Summary:")
    print(f"    Types:          {reader.type_count:>8,}")
    print(f"    Methods:        {reader.method_count:>8,}")
    print(f"    Fields:         {reader.field_count:>8,}")
    print(f"    Parameters:     {reader.param_count:>8,}")
    print(f"    Script entries: {len(script['ScriptMethod']):>8,}")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_metadata.py <metadata_path> [output_dir]")
        print()
        print("Parses IL2CPP global-metadata.dat into script.json, dump.cs,")
        print("and stringliteral.json with correct class-to-method mapping.")
        sys.exit(1)

    metadata_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    if not os.path.exists(metadata_path):
        print(f"Error: metadata file not found: {metadata_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Parsing: {metadata_path}")
    print(f"Output:  {output_dir}/")
    print()

    reader = MetadataReader(metadata_path)
    print(f"Metadata version: {reader.version}")
    print(f"TypeDef stride:   {reader.typedef_stride} bytes")
    print()

    # Generate script.json
    print("[1/3] Generating script.json...")
    script = generate_script_json(reader)
    script_path = os.path.join(output_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, separators=(",", ":"))
    size_mb = os.path.getsize(script_path) / (1024 * 1024)
    print(f"  Wrote {script_path} ({size_mb:.1f} MB, "
          f"{len(script['ScriptMethod']):,} methods)")
    print()

    # Generate dump.cs
    print("[2/3] Generating dump.cs...")
    dump_cs = generate_dump_cs(reader)
    dump_path = os.path.join(output_dir, "dump.cs")
    with open(dump_path, "w") as f:
        f.write(dump_cs)
    size_mb = os.path.getsize(dump_path) / (1024 * 1024)
    print(f"  Wrote {dump_path} ({size_mb:.1f} MB)")
    print()

    # Generate stringliteral.json
    print("[3/3] Generating stringliteral.json...")
    literals = generate_stringliteral_json(reader)
    literal_path = os.path.join(output_dir, "stringliteral.json")
    with open(literal_path, "w") as f:
        json.dump(literals, f, indent=2)
    print(f"  Wrote {literal_path} ({len(literals)} unique literals)")
    print()

    # Validate
    print("Validating...")
    errors = validate(reader, script)
    print()
    if errors:
        print(f"Done with {errors} warning(s). Review output for correctness.")
    else:
        print("Done. All checks passed.")


if __name__ == "__main__":
    main()
