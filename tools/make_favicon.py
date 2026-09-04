"""Generate dashboard/favicon.png. Standard library only; run once."""
import struct
import zlib

W = H = 32
GROUND, CHALK, VERDIGRIS = (0x0E, 0x14, 0x17), (0xE9, 0xE6, 0xDD), (0x74, 0xB8, 0xA8)

rows = []
for y in range(H):
    row = bytearray([0])
    for x in range(W):
        c = GROUND
        if 6 <= y <= 25 and 5 <= x <= 19:
            c = CHALK
        if 6 <= y <= 25 and 24 <= x <= 26:
            c = VERDIGRIS
        row += bytes(c)
    rows.append(bytes(row))


def chunk(tag: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + tag + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))


with open("dashboard/favicon.png", "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
            + chunk(b"IEND", b""))
print("wrote dashboard/favicon.png")
