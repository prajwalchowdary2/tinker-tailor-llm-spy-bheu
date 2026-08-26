"""
LevelDB Storage Parser — Pure-Python SSTable and WAL Log Carver

Parses LevelDB storage files (.sst, .ldb, .log) without compiled C++
dependencies or database locks. Includes a pure-Python Snappy block
decompressor for reading compressed SSTables.

This module enables forensic carving of IndexedDB data from live
Chromium browser sessions without triggering LOCK file contention.
"""

import os
import struct
from typing import List, Tuple, Optional


SSTABLE_MAGIC = b'\x57\xfb\x80\x8b\x24\x75\x47\xdb'


def snappy_decompress(src: bytes) -> bytes:
    """
    Pure-Python Snappy block decompression.

    Implements the Snappy compressed format without external libraries,
    enabling zero-dependency forensic carving on incident response machines.
    """
    try:
        pos = 0
        dec_len = 0
        shift = 0
        while True:
            if pos >= len(src):
                return b""
            b = src[pos]
            pos += 1
            dec_len |= (b & 0x7f) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift >= 35:
                return b""

        out = bytearray()
        src_len = len(src)

        while pos < src_len:
            tag = src[pos]
            pos += 1
            tag_type = tag & 0x03

            if tag_type == 0x00:
                len_bits = tag >> 2
                if len_bits < 60:
                    lit_len = len_bits + 1
                elif len_bits == 60:
                    if pos + 1 > src_len:
                        break
                    lit_len = src[pos] + 1
                    pos += 1
                elif len_bits == 61:
                    if pos + 2 > src_len:
                        break
                    lit_len = int.from_bytes(src[pos:pos + 2], 'little') + 1
                    pos += 2
                elif len_bits == 62:
                    if pos + 3 > src_len:
                        break
                    lit_len = int.from_bytes(src[pos:pos + 3], 'little') + 1
                    pos += 3
                else:
                    if pos + 4 > src_len:
                        break
                    lit_len = int.from_bytes(src[pos:pos + 4], 'little') + 1
                    pos += 4

                if pos + lit_len > src_len:
                    break
                out.extend(src[pos:pos + lit_len])
                pos += lit_len
            else:
                if tag_type == 0x01:
                    lit_len = 4 + ((tag >> 2) & 0x07)
                    if pos >= src_len:
                        break
                    offset = ((tag & 0xe0) << 3) | src[pos]
                    pos += 1
                elif tag_type == 0x02:
                    lit_len = 1 + (tag >> 2)
                    if pos + 2 > src_len:
                        break
                    offset = int.from_bytes(src[pos:pos + 2], 'little')
                    pos += 2
                else:
                    lit_len = 1 + (tag >> 2)
                    if pos + 4 > src_len:
                        break
                    offset = int.from_bytes(src[pos:pos + 4], 'little')
                    pos += 4

                if offset == 0 or offset > len(out):
                    break

                for _ in range(lit_len):
                    out.append(out[-offset])

        return bytes(out)
    except Exception:
        return b""


def read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    """Read a Protocol Buffer-style varint from bytes at position pos."""
    val = 0
    shift = 0
    while True:
        if pos >= len(data):
            break
        b = data[pos]
        pos += 1
        val |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos


def parse_block_entries(block_data: bytes) -> List[Tuple[bytes, bytes]]:
    """Parse key-value entries from a LevelDB data block."""
    entries = []
    if len(block_data) < 4:
        return entries
    try:
        num_restarts = int.from_bytes(block_data[-4:], 'little')
        restarts_offset = len(block_data) - 4 - num_restarts * 4
        if restarts_offset < 0:
            return entries

        pos = 0
        last_key = b""
        while pos < restarts_offset:
            shared, pos = read_varint(block_data, pos)
            unshared, pos = read_varint(block_data, pos)
            value_len, pos = read_varint(block_data, pos)

            key_delta = block_data[pos:pos + unshared]
            pos += unshared

            value = block_data[pos:pos + value_len]
            pos += value_len

            key = last_key[:shared] + key_delta
            last_key = key

            entries.append((key, value))
    except Exception:
        pass
    return entries


def parse_sstable(file_path: str) -> List[Tuple[bytes, bytes]]:
    """
    Parse a LevelDB SSTable file, extracting all key-value entries.

    Handles Snappy-compressed data blocks and validates the SSTable
    magic number in the footer.
    """
    entries = []
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        if len(content) < 48:
            return entries

        footer = content[-48:]
        magic = footer[-8:]
        if magic != SSTABLE_MAGIC:
            return entries

        pos = 0
        metaindex_offset, pos = read_varint(footer, pos)
        metaindex_size, pos = read_varint(footer, pos)
        index_offset, pos = read_varint(footer, pos)
        index_size, pos = read_varint(footer, pos)

        index_block_data = content[index_offset:index_offset + index_size]

        if index_offset + index_size < len(content):
            index_compression_type = content[index_offset + index_size]
            if index_compression_type == 1:
                index_block_data = snappy_decompress(index_block_data)

        index_entries = parse_block_entries(index_block_data)

        for key, val in index_entries:
            block_offset, v_pos = read_varint(val, 0)
            block_size, v_pos = read_varint(val, v_pos)

            data_block_raw = content[block_offset:block_offset + block_size]
            if block_offset + block_size < len(content):
                compression_type = content[block_offset + block_size]
                if compression_type == 1:
                    decompressed = snappy_decompress(data_block_raw)
                    if decompressed:
                        entries.extend(parse_block_entries(decompressed))
                else:
                    entries.extend(parse_block_entries(data_block_raw))
    except Exception:
        pass
    return entries


def parse_log_file(file_path: str) -> List[Tuple[bytes, bytes]]:
    """
    Read a LevelDB write-ahead log file as a single raw binary blob.

    WAL logs contain sequential writes that have not yet been compacted
    into SSTables. These are the primary source of recently "deleted"
    data, since deletions are recorded as tombstones but the original
    data blocks remain in the log until compaction.
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        return [(b"wal_entry", content)]
    except Exception:
        return []


def carve_leveldb_directory(
    leveldb_dir: str,
    file_types: Optional[set] = None,
) -> List[Tuple[str, bytes, bytes, float]]:
    """
    Carve all key-value entries from a LevelDB directory.

    Returns list of (filename, key, value, mtime) tuples.
    Handles both SSTables (.ldb/.sst) and WAL logs (.log).
    """
    if file_types is None:
        file_types = {'.log', '.ldb', '.sst'}

    results = []
    if not leveldb_dir or not os.path.exists(leveldb_dir):
        return results

    try:
        for filename in os.listdir(leveldb_dir):
            ext = os.path.splitext(filename)[1]
            if ext not in file_types:
                continue

            file_path = os.path.join(leveldb_dir, filename)
            mtime = os.path.getmtime(file_path)

            if ext in ('.ldb', '.sst'):
                entries = parse_sstable(file_path)
            else:
                entries = parse_log_file(file_path)

            for key, value in entries:
                if len(value) >= 100:
                    results.append((filename, key, value, mtime))
    except Exception:
        pass

    return results
