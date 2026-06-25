#!/usr/bin/env python3
"""Regenerate preview images for every prompt using vinano.ai (served through
the apiany.ai gateway).

Usage:
  python3 scripts/generate_images.py                 # generate all missing
  python3 scripts/generate_images.py --limit 30      # first 30 missing
  python3 scripts/generate_images.py --source meigen # only one source
  python3 scripts/generate_images.py --ids mk-1448 mg-2013268963266904438
  python3 scripts/generate_images.py --workers 6

The script is resumable: it skips any prompt whose target image already exists.
The API key is read from .secrets/apiany_key.txt (gitignored) or the
APIANY_API_KEY environment variable.
"""
import argparse, json, os, sys, time, threading, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROMPTS = os.path.join(REPO, "prompts", "prompts.json")
KEY_FILE = os.path.join(REPO, ".secrets", "apiany_key.txt")

BASE = "https://apiany.ai"            # vinano.ai render gateway
SYNC_EP = BASE + "/v1/images/generations/sync"

# Public engine label (as stored in prompts.json) -> internal render model id.
ENGINE_TO_MODEL = {
    "Vinano Image": "nano-banana",
    "Vinano Image Pro": "nano-banana-pro",
}
DEFAULT_MODEL = "nano-banana"

_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(*a, flush=True)


def get_key():
    k = os.environ.get("APIANY_API_KEY")
    if k:
        return k.strip()
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE).read().strip()
    sys.exit("No API key: set APIANY_API_KEY or create .secrets/apiany_key.txt")


def post_json(url, payload, key, timeout=240):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def fetch_url(url, dest, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "vinano-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, dest)
    return len(body)


def gen_one(entry, key, retries=3):
    dest = os.path.join(REPO, entry["image"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    model = ENGINE_TO_MODEL.get(entry.get("engine"), DEFAULT_MODEL)
    payload = {"model": model, "prompt": entry["prompt"]}
    last = None
    for attempt in range(1, retries + 1):
        try:
            status, body = post_json(SYNC_EP, payload, key)
            if status == 200 and body.get("data"):
                url = body["data"][0].get("url")
                if url:
                    n = fetch_url(url, dest)
                    return True, f"{entry['id']} OK ({n} bytes)"
                return False, f"{entry['id']} no url in response"
            if status == 202:
                # task still processing; treat as soft failure to retry later
                last = f"{entry['id']} still processing (202)"
            else:
                last = f"{entry['id']} HTTP {status}: {json.dumps(body)[:160]}"
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:160]
            last = f"{entry['id']} HTTPError {e.code}: {detail}"
            if e.code in (400, 401, 403):
                break  # not retryable
        except Exception as e:
            last = f"{entry['id']} ERR {type(e).__name__}: {e}"
        time.sleep(min(2 ** attempt, 15))
    return False, last or f"{entry['id']} failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max images to generate (0 = all missing)")
    ap.add_argument("--source", choices=["mkimage", "meigen"], help="restrict to one source")
    ap.add_argument("--category", help="restrict to one category")
    ap.add_argument("--ids", nargs="*", help="specific prompt ids")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--overwrite", action="store_true", help="regenerate even if image exists")
    args = ap.parse_args()

    key = get_key()
    data = json.load(open(PROMPTS, encoding="utf-8"))
    entries = data["prompts"]

    if args.source:
        entries = [e for e in entries if e["source"] == args.source]
    if args.category:
        entries = [e for e in entries if e["category"] == args.category]
    if args.ids:
        idset = set(args.ids)
        entries = [e for e in entries if e["id"] in idset]
    if not args.overwrite:
        entries = [e for e in entries if not os.path.exists(os.path.join(REPO, e["image"]))]
    if args.limit:
        entries = entries[:args.limit]

    total = len(entries)
    log(f"Generating {total} images with vinano.ai ({args.workers} workers)")
    if not total:
        return

    counters = {"ok": 0, "fail": 0, "done": 0}
    lock = threading.Lock()
    q = list(entries)
    qi = {"i": 0}

    def worker():
        while True:
            with lock:
                if qi["i"] >= len(q):
                    return
                e = q[qi["i"]]; qi["i"] += 1
            ok, msg = gen_one(e, key)
            with lock:
                counters["done"] += 1
                counters["ok" if ok else "fail"] += 1
                d = counters["done"]
            log(f"[{d}/{total}] {'OK ' if ok else 'XX '} {msg}")

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, args.workers))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    log(f"Done. ok={counters['ok']} fail={counters['fail']} total={total}")


if __name__ == "__main__":
    main()
