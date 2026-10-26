"""
Minimal Tertius API client: push a local project folder, compile it,
fetch the model. Standard library only.

    python3 tools/tertius_client.py projects
    python3 tools/tertius_client.py new dincase
    python3 tools/tertius_client.py push dincase tertius-project
    python3 tools/tertius_client.py compile dincase tertius-project \
        [--format glb|stl|step] [--out stl/Trunk_550.glb]
    python3 tools/tertius_client.py files dincase
    python3 tools/tertius_client.py pull dincase tertius-project

Environment: TERTIUS_URL (default production), TERTIUS_USER and
TERTIUS_PASSWORD (default demo / demo). The access token lasts 5 minutes;
it is fetched fresh for each run.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("TERTIUS_URL",
                      "https://tertius.gainengineering.com.au").rstrip("/")
INTUS = BASE + "/api/intus"
EXTUS = BASE + "/api/extus"
# Cloudflare in front of production refuses urllib's default User-Agent.
UA = {"User-Agent": "tertius-client/0.1"}


def token():
    form = urllib.parse.urlencode({
        "grant_type": "password", "client_id": "tertius-ui",
        "username": os.environ.get("TERTIUS_USER", "demo"),
        "password": os.environ.get("TERTIUS_PASSWORD", "demo"),
    }).encode()
    url = BASE + "/realms/tertius/protocol/openid-connect/token"
    req = urllib.request.Request(url, form, UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


class Api:
    def __init__(self):
        self.auth = dict(UA, Authorization="Bearer " + token())

    def call(self, method, url, body=None, raw=False):
        data = None if body is None else json.dumps(body).encode()
        headers = dict(self.auth)
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data, headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as e:
            sys.exit("%s %s: HTTP %d %s" % (method, url, e.code,
                                            e.read().decode()[:500]))


def project_files(folder):
    """The files of a local project folder that belong in Tertius."""
    return sorted(f for f in os.listdir(folder)
                  if f.endswith((".py", ".json"))
                  and os.path.isfile(os.path.join(folder, f)))


def read(folder, name):
    with open(os.path.join(folder, name), encoding="utf-8") as f:
        return f.read()


def cmd_projects(api, a):
    print("\n".join(api.call("GET", INTUS + "/projects")["projects"]))


def cmd_new(api, a):
    print(api.call("POST", "%s/projects/%s/new" % (INTUS, a.name)))


def cmd_files(api, a):
    print("\n".join(api.call("GET", "%s/projects/%s/files"
                             % (INTUS, a.name))["files"]))


def cmd_push(api, a):
    for f in project_files(a.folder):
        api.call("POST", "%s/projects/%s/save" % (INTUS, a.name),
                 {"file": f, "code": read(a.folder, f)})
        print("saved", f)


def cmd_pull(api, a):
    os.makedirs(a.folder, exist_ok=True)
    for f in api.call("GET", "%s/projects/%s/files" % (INTUS, a.name))[
            "files"]:
        q = urllib.parse.quote(f)
        code = api.call("GET", "%s/projects/%s/code?file=%s"
                        % (INTUS, a.name, q))["code"]
        with open(os.path.join(a.folder, f), "w", encoding="utf-8") as fh:
            fh.write(code)
        print("pulled", f)


def cmd_compile(api, a):
    cmd_push(api, a)
    # Artifacts are served from the active project only; this also makes
    # it the project the web UI opens on.
    api.call("POST", "%s/projects/%s/activate" % (INTUS, a.name))
    job = api.call("POST", "%s/projects/%s/compile" % (INTUS, a.name),
                   {"file": "design.py", "code": read(a.folder, "design.py"),
                    "export_format": a.format})
    url = "%s/projects/%s/compile/jobs/%s" % (INTUS, a.name, job["job_id"])
    t0 = time.time()
    while True:
        st = api.call("GET", url)
        if st["status"] in ("succeeded", "completed", "failed"):
            break
        if time.time() - t0 > a.timeout:
            sys.exit("compile still %s after %ds" % (st["status"],
                                                     a.timeout))
        time.sleep(2)
    print(json.dumps(st, indent=2))
    if st["status"] == "failed":
        sys.exit(1)
    if a.out and st.get("artifact_id"):
        data = api.call("GET", "%s/artifacts/%s/model"
                        % (EXTUS, st["artifact_id"]), raw=True)
        with open(a.out, "wb") as f:
            f.write(data)
        print("wrote %s (%d bytes)" % (a.out, len(data)))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("projects")
    for c in ("new", "files"):
        sub.add_parser(c).add_argument("name")
    for c in ("push", "pull", "compile"):
        s = sub.add_parser(c)
        s.add_argument("name")
        s.add_argument("folder")
        if c == "compile":
            s.add_argument("--format", default="glb")
            s.add_argument("--out")
            s.add_argument("--timeout", type=int, default=300)
    a = p.parse_args()
    globals()["cmd_" + a.cmd](Api(), a)


if __name__ == "__main__":
    main()
