#!/usr/bin/env python3
"""team.py - universal model-team toolkit for Claude Code. Stdlib only.

  team.py detect                 scan device: local + cloud models, CLIs -> registry
  team.py plan [--size S|M|L]    pick a lean team from the registry (compact output)
  team.py run  AGENT "task"      run one agent (inbox auto-injected, output compressed)
  team.py tick [--rounds N]      let agents with unread mail answer each other (capped)
  team.py post FROM TO "msg"     agent-to-agent message (TO may be 'all' or 'lead')
  team.py inbox AGENT            read unread messages
  team.py mem show|add|compact   daily-compressed shared memory
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time, urllib.request
from datetime import date, datetime

HOME = os.environ.get("TEAM_HOME", os.path.expanduser("~/.agent-team/state"))  # shared by every agent tool
REG = os.path.join(HOME, "registry.json")
BUS = os.path.join(HOME, "bus.jsonl")
CUR = os.path.join(HOME, "cursors.json")
TEAMF = os.path.join(HOME, "team.json")   # role -> agent id (set by plan)
MEM = os.path.join(HOME, "memory.md")
OUT = os.path.join(HOME, "out")
MAX_MSG = 600          # chars per bus message (token guard)
MAX_INBOX = 8          # messages injected per run
MAX_SUMMARY = 700      # chars returned to the lead per run
os.makedirs(OUT, exist_ok=True)

# ---------- helpers ----------
def http(url, data=None, headers=None, timeout=4):
    req = urllib.request.Request(url, headers=headers or {})
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def load(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: json.dump(obj, f, separators=(",", ":"))

SKIP = re.compile(r"embed|whisper|tts|dall-e|image|moderation|rerank|audio|realtime|transcribe|vision-preview|guard", re.I)

def tier(name, local):
    n = name.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", n)
    if local and m:
        b = float(m.group(1)); return 1 if b <= 4 else 2 if b <= 14 else 3
    if re.search(r"haiku|mini|flash|nano|lite|small|instant|8b|7b|3b", n): return 1
    if re.search(r"opus|fable|\bpro\b|large|o1|o3|gpt-5(?!.*mini)|sonnet|r1|reasoner", n): return 3
    return 2

def caps(name):
    n = name.lower(); c = ["chat"]
    if re.search(r"cod(e|er)|deepseek|starcoder|qwen.*coder|codex|sonnet|opus|fable|gpt-5", n): c.append("code")
    if re.search(r"opus|fable|\bpro\b|o1|o3|r1|reasoner|gpt-5|sonnet", n): c.append("reason")
    if re.search(r"haiku|mini|flash|nano|lite|small|instant|\b[1-8]b\b", n): c.append("fast")
    return c

def family(name):
    n = name.lower()
    for f in ("claude|haiku|sonnet|opus|fable", "gpt|o1|o3|codex", "gemini|gemma", "llama", "qwen", "mistral|mixtral|codestral", "deepseek", "grok"):
        if re.search(f, n): return f.split("|")[0]
    return n.split(":")[0].split("-")[0]

def entry(provider, model, local, via, base=None, env=None, verified=True):
    return {"id": f"{provider}:{model}", "provider": provider, "model": model, "local": local,
            "tier": tier(model, local), "caps": caps(model), "family": family(model),
            "via": via, "base": base, "env": env, "verified": verified}

# ---------- detect ----------
OPENAI_LIKE = {  # provider: (base url, env var, defaults)
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", ["gpt-5", "gpt-5-mini"]),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", ["mistral-large-latest", "mistral-small-latest"]),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", ["deepseek-chat", "deepseek-reasoner"]),
    "xai": ("https://api.x.ai/v1", "XAI_API_KEY", ["grok-4", "grok-3-mini"]),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", ["anthropic/claude-sonnet-5-5", "google/gemini-2.5-flash"]),
}
LOCAL_SERVERS = {"lmstudio": "http://localhost:1234/v1", "llamacpp": "http://localhost:8080/v1",
                 "vllm": "http://localhost:8000/v1", "jan": "http://localhost:1337/v1"}

def detect():
    out = []
    # local: ollama
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not host.startswith("http"): host = "http://" + host
    try:
        for m in http(host + "/api/tags", timeout=1.5).get("models", []):
            if not SKIP.search(m["name"]): out.append(entry("ollama", m["name"], True, "http", host))
    except Exception:
        if shutil.which("ollama"):
            try:
                for ln in subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5).stdout.splitlines()[1:]:
                    nm = ln.split()[0] if ln.split() else ""
                    if nm and not SKIP.search(nm): out.append(entry("ollama", nm, True, "http", host))
            except Exception: pass
    # local: OpenAI-compatible servers
    for prov, base in LOCAL_SERVERS.items():
        try:
            for m in http(base + "/models", timeout=1.2).get("data", []):
                if not SKIP.search(m["id"]): out.append(entry(prov, m["id"], True, "openai", base))
        except Exception: pass
    # cloud: Anthropic
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        try:
            ms = [m["id"] for m in http("https://api.anthropic.com/v1/models?limit=50", headers={"x-api-key": k, "anthropic-version": "2023-06-01"}, timeout=5)["data"]]
            ok = True
        except Exception: ms, ok = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], False
        for m in ms: out.append(entry("anthropic", m, False, "anthropic", "https://api.anthropic.com", "ANTHROPIC_API_KEY", ok))
    # cloud: Gemini
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if k:
        try:
            ms = [m["name"].split("/")[-1] for m in http(f"https://generativelanguage.googleapis.com/v1beta/models?key={k}", timeout=5)["models"]
                  if "generateContent" in m.get("supportedGenerationMethods", [])]
            ok = True
        except Exception: ms, ok = ["gemini-2.5-pro", "gemini-2.5-flash"], False
        for m in ms:
            if not SKIP.search(m): out.append(entry("gemini", m, False, "gemini", None, "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_API_KEY", ok))
    # cloud: OpenAI-compatible
    for prov, (base, env, defaults) in OPENAI_LIKE.items():
        k = os.environ.get(env)
        if not k: continue
        try:
            ms = [m["id"] for m in http(base + "/models", headers={"Authorization": "Bearer " + k}, timeout=5)["data"]]
            ms = [m for m in ms if not SKIP.search(m)]
            ok = True
        except Exception: ms, ok = defaults, False
        if prov == "openrouter": ms = ms[:0] or defaults  # catalog is huge; keep curated
        for m in ms: out.append(entry(prov, m, False, "openai", base, env, ok))
    # CLIs (use their own login; no key needed)
    for cli, model in (("claude", "claude-cli"), ("codex", "codex-cli"), ("gemini", "gemini-cli")):
        if shutil.which(cli):
            e = entry("cli", model, False, "cli", cli); e["tier"] = 3; e["caps"] = ["chat", "code", "reason"]
            e["family"] = {"claude": "claude", "codex": "gpt", "gemini": "gemini"}[cli]
            out.append(e)
    # de-dupe + cap per provider (keep tier diversity) to keep registry lean
    seen, final, per = set(), [], {}
    for e in sorted(out, key=lambda e: (e["provider"], -e["tier"], e["model"])):
        if e["id"] in seen: continue
        seen.add(e["id"]); per.setdefault(e["provider"], 0)
        if per[e["provider"]] < 10: final.append(e); per[e["provider"]] += 1
    reg = {"ts": datetime.now().isoformat(timespec="seconds"), "agents": final}
    save(REG, reg)
    return reg

def get_reg():
    r = load(REG, None)
    return r if r and r.get("agents") else detect()

# ---------- plan ----------
ROLES = [  # (role, needs cap, preferred tier order, prefer local)
    ("scout", "fast", (1, 2, 3), True),     # search/summarize/grunt work: cheapest first
    ("coder", "code", (2, 3, 1), False),
    ("reviewer", "reason", (3, 2, 1), False),
    ("writer", "chat", (1, 2, 3), True),
]
SIZES = {"S": 2, "M": 3, "L": 4}

def plan(size):
    agents = get_reg()["agents"]
    if not agents: return {"team": [], "note": "no models detected; Claude works solo"}
    n, team, used = SIZES.get(size.upper(), 3), [], set()
    for role, cap, tiers, prefer_local in ROLES[:n]:
        pool = [a for a in agents if a["id"] not in used and cap in a["caps"]] or [a for a in agents if a["id"] not in used]
        if not pool: break
        # prefer: local (free) for cheap roles, different model family for diversity, tier order
        def score(a):
            t = tiers.index(a["tier"]) if a["tier"] in tiers else 9
            fam_pen = 1 if any(x["family"] == a["family"] for x in team) else 0
            loc = 0 if (a["local"] == prefer_local) else 1
            return (t + loc * (1 if prefer_local else 0.5), fam_pen, not a["verified"])
        best = min(pool, key=score)
        used.add(best["id"]); team.append({"role": role, "id": best["id"], "tier": best["tier"], "local": best["local"], "family": best["family"]})
    save(TEAMF, {t["role"]: t["id"] for t in team})
    for t in team: t.pop("family")
    return {"team": team, "lead": "claude (you)"}

# ---------- bus (agent <-> agent) ----------
def post(frm, to, body, topic=""):
    body = " ".join(body.split())[:MAX_MSG]
    msg = {"id": int(time.time() * 1000), "from": frm, "to": to, "topic": topic, "body": body}
    os.makedirs(HOME, exist_ok=True)
    with open(BUS, "a") as f: f.write(json.dumps(msg, separators=(",", ":")) + "\n")
    return msg

def inbox(agent, mark=True):
    cur = load(CUR, {}); last = cur.get(agent, 0); msgs = []
    try:
        for ln in open(BUS):
            m = json.loads(ln)
            if m["id"] > last and m["from"] != agent and m["to"] in (agent, "all"): msgs.append(m)
    except FileNotFoundError: pass
    msgs = msgs[-MAX_INBOX:]
    if mark and msgs:
        cur[agent] = max(m["id"] for m in msgs); save(CUR, cur)
    return msgs

# ---------- run ----------
SYS = ("You are '{name}', a teammate in an AI team led by Claude. Be terse. "
       "Do the task, then end with one line 'SUMMARY: <=50 words'. "
       "To message a teammate put a line '@<agent>: <msg>' (or '@lead:'). Only message if it unblocks work.")

def call(a, prompt, system):
    p, m, base = a["provider"], a["model"], a.get("base")
    key = os.environ.get(a["env"]) if a.get("env") else None
    if a["via"] == "http":  # ollama
        r = http(base + "/api/chat", {"model": m, "stream": False, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, timeout=600)
        return r["message"]["content"]
    if a["via"] == "openai":
        h = {"Authorization": "Bearer " + key} if key else {}
        r = http(base + "/chat/completions", {"model": m, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, h, 600)
        return r["choices"][0]["message"]["content"]
    if a["via"] == "anthropic":
        r = http(base + "/v1/messages", {"model": m, "max_tokens": 2048, "system": system, "messages": [{"role": "user", "content": prompt}]},
                 {"x-api-key": key, "anthropic-version": "2023-06-01"}, 600)
        return "".join(b.get("text", "") for b in r["content"])
    if a["via"] == "gemini":
        r = http(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
                 {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt}]}]}, timeout=600)
        return r["candidates"][0]["content"]["parts"][0]["text"]
    if a["via"] == "cli":
        cmd = {"claude": ["claude", "-p", system + "\n\n" + prompt], "codex": ["codex", "exec", system + "\n\n" + prompt],
               "gemini": ["gemini", "-p", system + "\n\n" + prompt]}[base]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=900).stdout
    raise RuntimeError("unknown transport " + a["via"])

def resolve(name):
    agents = get_reg()["agents"]
    name = load(TEAMF, {}).get(name, name)   # role alias -> agent id
    ms = [a for a in agents if a["id"] == name or a["model"] == name] or [a for a in agents if name in a["id"]]
    if not ms: sys.exit(f"no agent matches '{name}'. run: team.py detect")
    return ms[0]

def run(name, task, role=None, label=None):
    a = resolve(name); label = label or role or a["id"]
    mail = inbox(label)
    ctx = "\n".join(f"[{m['from']}] {m['body']}" for m in mail)
    prompt = (f"INBOX:\n{ctx}\n\n" if ctx else "") + f"TASK: {task}"
    try: text = call(a, prompt, SYS.format(name=label))
    except Exception as e: text = f"ERROR: {e}"
    # route @mentions to the bus; keep full text on disk, return only a summary
    for ln in text.splitlines():
        mt = re.match(r"\s*@([\w:.\-/]+):\s*(.+)", ln)
        if mt: post(label, mt.group(1), mt.group(2))
    path = os.path.join(OUT, f"{int(time.time())}-{re.sub(r'[^\w.-]', '_', label)}.md")
    open(path, "w").write(text)
    sm = re.search(r"SUMMARY:\s*(.+)", text, re.S)
    brief = (sm.group(1) if sm else text).strip()[:MAX_SUMMARY]
    return {"agent": label, "summary": " ".join(brief.split()), "full": path}

def tick(rounds):
    seen = {}
    for _ in range(rounds):
        names = set()
        try:
            cur = load(CUR, {})
            for ln in open(BUS):
                m = json.loads(ln)
                tgt = [m["to"]] if m["to"] not in ("all",) else [a for a in {x["id"] for x in get_reg()["agents"]}]
                for t in tgt:
                    if t != "lead" and m["from"] != t and m["id"] > cur.get(t, 0): names.add(t)
        except FileNotFoundError: pass
        if not names: break
        for n in sorted(names):
            try: seen[n] = run(n, "Reply to your inbox. If nothing is needed, say SUMMARY: ok.")
            except SystemExit: pass
    return seen

# ---------- memory: one compressed line per day, auto-compacted ----------
def mem_read():
    try: return [l.rstrip("\n") for l in open(MEM)]
    except FileNotFoundError: return []

def mem_add(text):
    today = date.today().isoformat(); lines = mem_read()
    text = " ".join(text.split())
    for i, l in enumerate(lines):
        if l.startswith(today + "|"):
            if text not in l: lines[i] = l + ";" + text
            break
    else: lines.append(f"{today}|{text}")
    open(MEM, "w").write("\n".join(lines) + "\n"); mem_compact(); return "ok"

def mem_compact(keep_days=7, cap=400):
    """Days older than keep_days merge into one line per ISO week; each line capped."""
    lines, today, daily, weeks = mem_read(), date.today(), [], {}
    for l in lines:
        k, _, v = l.partition("|")
        try: d = date.fromisoformat(k)
        except ValueError:
            wk = k; weeks.setdefault(wk, []).append(v); continue
        if (today - d).days > keep_days:
            y, w, _ = d.isocalendar(); weeks.setdefault(f"{y}-W{w:02d}", []).append(v)
        else: daily.append(f"{k}|{v[:cap]}")
    wl = [f"{k}|{';'.join(v)[:cap]}" for k, v in sorted(weeks.items())]
    open(MEM, "w").write("\n".join(wl + daily) + ("\n" if wl or daily else ""))

# ---------- cli ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("detect")
    p = sp.add_parser("plan"); p.add_argument("--size", default="M")
    p = sp.add_parser("run"); p.add_argument("agent"); p.add_argument("task"); p.add_argument("--role")
    p = sp.add_parser("tick"); p.add_argument("--rounds", type=int, default=2)
    p = sp.add_parser("post"); p.add_argument("frm"); p.add_argument("to"); p.add_argument("body")
    p = sp.add_parser("inbox"); p.add_argument("agent"); p.add_argument("--peek", action="store_true")
    p = sp.add_parser("mem"); p.add_argument("op", choices=["show", "add", "compact"]); p.add_argument("text", nargs="?", default="")
    a = ap.parse_args()
    if a.cmd == "detect":
        r = detect(); by = {}
        for e in r["agents"]: by.setdefault(("local " if e["local"] else "cloud ") + e["provider"], []).append(f"{e['model']}(t{e['tier']})")
        print(json.dumps({"found": len(r["agents"]), "by_source": by}, separators=(",", ":")))
    elif a.cmd == "plan": print(json.dumps(plan(a.size), separators=(",", ":")))
    elif a.cmd == "run": print(json.dumps(run(a.agent, a.task, a.role), separators=(",", ":")))
    elif a.cmd == "tick": print(json.dumps(tick(a.rounds), separators=(",", ":")))
    elif a.cmd == "post": post(a.frm, a.to, a.body); print("ok")
    elif a.cmd == "inbox": print("\n".join(f"[{m['from']}] {m['body']}" for m in inbox(a.agent, not a.peek)) or "(empty)")
    elif a.cmd == "mem":
        if a.op == "show": print("\n".join(mem_read()[-12:]) or "(empty)")
        elif a.op == "add": print(mem_add(a.text))
        else: mem_compact(); print("ok")

if __name__ == "__main__":
    main()
