"""远程读取 APK(zip) 中央目录，鉴别是否为 libGDX 正版 SWL。

用法: python remote_zip_list.py <url> [<url> ...]
原理: zip 中央目录在文件尾部，Range 请求只拉最后 ~256KB 即可解析全部条目名。
"""
import sys, struct, urllib.request

PROXY = "http://127.0.0.1:7897"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_range(url: str, start: int, end: int) -> bytes:
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{end}"})
    with opener.open(req, timeout=60) as r:
        return r.read()


def content_length(url: str) -> int:
    req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"})
    with opener.open(req, timeout=60) as r:
        cr = r.headers.get("Content-Range", "")
        return int(cr.split("/")[-1])


def list_entries(url: str) -> list:
    total = content_length(url)
    tail = fetch_range(url, max(0, total - 262144), total - 1)
    # EOCD64 优先，退化 EOCD
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("no EOCD")
    cd_size, cd_off = struct.unpack_from("<II", tail, eocd + 12)
    if cd_off + cd_size > total or cd_off < total - len(tail):
        # 中央目录不在已拉取尾部，按精确范围补拉
        need = fetch_range(url, cd_off, cd_off + cd_size - 1)
    else:
        need = tail[cd_off - (total - len(tail)):cd_off + cd_size - (total - len(tail))]
    entries = []
    i = 0
    while i < len(need) - 46:
        if need[i:i+4] != b"PK\x01\x02":
            i += 1
            continue
        nlen, elen, clen = struct.unpack_from("<HHH", need, i + 28)
        size = struct.unpack_from("<I", need, i + 24)[0]
        name = need[i+46:i+46+nlen].decode("utf-8", "replace")
        entries.append((name, size))
        i += 46 + nlen + elen + clen
    return entries


def summarize(name: str, entries: list) -> None:
    print(f"\n===== {name} ({len(entries)} entries) =====")
    exts = {}
    for n, _ in entries:
        e = n.rsplit(".", 1)[-1].lower() if "." in n else "(dir/none)"
        exts[e] = exts.get(e, 0) + 1
    print("ext:", dict(sorted(exts.items(), key=lambda x: -x[1])[:12]))
    hits = [n for n, _ in entries
            if any(k in n.lower() for k in ("ogg", "wav", "mp3", "sound", "audio", ".pack", ".atlas"))]
    for n in hits[:40]:
        print("  hit:", n)
    if not hits:
        top = {}
        for n, _ in entries:
            top.setdefault(n.split("/")[0], 0)
            top[n.split("/")[0]] += 1
        print("top:", dict(sorted(top.items(), key=lambda x: -x[1])[:10]))


if __name__ == "__main__":
    for url in sys.argv[1:]:
        try:
            summarize(url.rsplit("/", 1)[-1][:60], list_entries(url))
        except Exception as e:
            print(f"\n===== {url} =====\nERROR: {e}")
