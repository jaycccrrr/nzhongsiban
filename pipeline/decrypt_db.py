# -*- coding: utf-8 -*-
"""Decrypt message_0.db + WAL using captured enc_key, produce plain sqlite db."""
import os, sys, hashlib, hmac as hmac_mod, struct, shutil

PAGE_SZ = 4096
RESERVE_SZ = 80
SQLITE_HDR = b'SQLite format 3\x00'
from Crypto.Cipher import AES

def decrypt_page(enc_key, page_data, pgno):
    iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + 16]
    if pgno == 1:
        encrypted = page_data[16 : PAGE_SZ - RESERVE_SZ]
        return SQLITE_HDR + AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted) + b'\x00' * RESERVE_SZ
    encrypted = page_data[: PAGE_SZ - RESERVE_SZ]
    return AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted) + b'\x00' * RESERVE_SZ

def decrypt_db(db_path, out_path, enc_key):
    size = os.path.getsize(db_path)
    pages = (size + PAGE_SZ - 1) // PAGE_SZ
    with open(db_path, 'rb') as fin, open(out_path, 'wb') as fout:
        for pgno in range(1, pages + 1):
            pd = fin.read(PAGE_SZ)
            if len(pd) < PAGE_SZ:
                pd += b'\x00' * (PAGE_SZ - len(pd))
            fout.write(decrypt_page(enc_key, pd, pgno))
    return pages

def decrypt_wal(wal_path, out_wal_path, enc_key):
    """WAL frame: pgno(4,BE)+unk(4)+salt(16)+page(4096). Decrypt page part."""
    hdr_sz = 32  # WAL header
    frame_sz = 4 + 4 + 16 + PAGE_SZ
    size = os.path.getsize(wal_path)
    with open(wal_path, 'rb') as fin, open(out_wal_path, 'wb') as fout:
        hdr = fin.read(hdr_sz)
        fout.write(hdr)
        n = 0
        while True:
            fh = fin.read(24)
            if len(fh) < 24:
                break
            page = fin.read(PAGE_SZ)
            if len(page) < PAGE_SZ:
                page += b'\x00' * (PAGE_SZ - len(page))
            pgno = struct.unpack('>I', fh[:4])[0]
            fout.write(fh)
            fout.write(decrypt_page(enc_key, page, pgno))
            n += 1
    return n

if __name__ == '__main__':
    key_file, db_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    enc_key = None
    base = os.path.basename(db_path)
    with open(key_file, encoding='utf-8') as f:
        for line in f:
            rel, k = line.strip().split('\t')
            if os.path.basename(rel) == base and 'biz_' not in os.path.basename(rel):
                enc_key = bytes.fromhex(k)
                break
    if enc_key is None:
        print("no key for", base); sys.exit(1)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, base)
    n = decrypt_db(db_path, out, enc_key)
    print("decrypted %s: %d pages" % (base, n))
    wal = db_path + '-wal'
    if os.path.exists(wal) and os.path.getsize(wal) > 32:
        nframes = decrypt_wal(wal, out + '-wal', enc_key)
        print("decrypted WAL: %d frames" % nframes)
