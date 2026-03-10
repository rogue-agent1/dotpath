#!/usr/bin/env python3
"""dotpath - Query and modify nested dicts/JSON with dot notation.

One file. Zero deps. Deep access.

Usage:
  dotpath.py get file.json "a.b.c"
  dotpath.py set file.json "a.b.c" "value"
  dotpath.py del file.json "a.b.c"
  dotpath.py keys file.json "a.b"
  dotpath.py exists file.json "a.b.c"
  echo '{}' | dotpath.py get - "key"
"""

import argparse
import json
import re
import sys


def parse_path(path: str) -> list:
    parts = []
    for seg in re.split(r'\.|\[', path):
        seg = seg.rstrip(']')
        if not seg:
            continue
        if seg.isdigit():
            parts.append(int(seg))
        else:
            parts.append(seg)
    return parts


def get_path(obj, parts):
    cur = obj
    for p in parts:
        if isinstance(cur, dict) and isinstance(p, str) and p in cur:
            cur = cur[p]
        elif isinstance(cur, (list, tuple)) and isinstance(p, int) and p < len(cur):
            cur = cur[p]
        else:
            return None, False
    return cur, True


def set_path(obj, parts, value):
    if not parts:
        return value
    cur = obj
    for i, p in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(cur, dict):
            if p not in cur:
                cur[p] = [] if isinstance(nxt, int) else {}
            cur = cur[p]
        elif isinstance(cur, list):
            while len(cur) <= p:
                cur.append(None)
            if cur[p] is None:
                cur[p] = [] if isinstance(nxt, int) else {}
            cur = cur[p]
    last = parts[-1]
    if isinstance(cur, dict):
        cur[last] = value
    elif isinstance(cur, list):
        while len(cur) <= last:
            cur.append(None)
        cur[last] = value
    return obj


def del_path(obj, parts):
    if not parts:
        return obj
    val, ok = get_path(obj, parts[:-1])
    if not ok:
        return obj
    last = parts[-1]
    if isinstance(val, dict) and last in val:
        del val[last]
    elif isinstance(val, list) and isinstance(last, int) and last < len(val):
        val.pop(last)
    return obj


def smart_value(s: str):
    if s == "null":
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass
    return s


def read_json(path: str):
    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path) as f:
        return json.load(f)


def main():
    p = argparse.ArgumentParser(description="Query/modify nested JSON with dot notation")
    sub = p.add_subparsers(dest="cmd")

    for name in ("get", "keys", "exists"):
        s = sub.add_parser(name)
        s.add_argument("file")
        s.add_argument("path")

    s = sub.add_parser("set")
    s.add_argument("file")
    s.add_argument("path")
    s.add_argument("value")
    s.add_argument("-i", "--inplace", action="store_true")

    s = sub.add_parser("del")
    s.add_argument("file")
    s.add_argument("path")
    s.add_argument("-i", "--inplace", action="store_true")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1

    obj = read_json(args.file)
    parts = parse_path(args.path)

    if args.cmd == "get":
        val, ok = get_path(obj, parts)
        if not ok:
            print("null")
            return 1
        if isinstance(val, (dict, list)):
            print(json.dumps(val, indent=2, ensure_ascii=False))
        else:
            print(val)
    elif args.cmd == "keys":
        val, ok = get_path(obj, parts)
        if ok and isinstance(val, dict):
            for k in val:
                print(k)
        elif ok and isinstance(val, list):
            for i in range(len(val)):
                print(i)
        else:
            return 1
    elif args.cmd == "exists":
        _, ok = get_path(obj, parts)
        print("true" if ok else "false")
        return 0 if ok else 1
    elif args.cmd == "set":
        obj = set_path(obj, parts, smart_value(args.value))
        out = json.dumps(obj, indent=2, ensure_ascii=False)
        if hasattr(args, "inplace") and args.inplace and args.file != "-":
            with open(args.file, "w") as f:
                f.write(out + "\n")
        else:
            print(out)
    elif args.cmd == "del":
        obj = del_path(obj, parts)
        out = json.dumps(obj, indent=2, ensure_ascii=False)
        if hasattr(args, "inplace") and args.inplace and args.file != "-":
            with open(args.file, "w") as f:
                f.write(out + "\n")
        else:
            print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
