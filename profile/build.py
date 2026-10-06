"""Builds dark_mode.svg / light_mode.svg (neofetch-style profile card).

Static info lives in INFO below; GitHub stats and visitor count are fetched
on every run (GitHub Actions, every 12h). Needs env GH_TOKEN.
"""
import datetime as dt
import html
import os
import re
import time
from pathlib import Path

import requests

USER = os.environ.get("USER_NAME", "fiori007")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
HEAD = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}
ROOT = Path(__file__).resolve().parent.parent
X = 405

WIDTH = 56  # chars from key start to end of value (values right-justified)

INFO = [
    ("header", "lucas@fiori"),
    ("kv", ["Education"], "B.Sc. in Computer Science"),
    ("kv", ["Focus"], "Data, Software, Automation, AI"),
    ("blank",),
    ("kv", ["Languages", "Programming"], "Python, Java, TypeScript, SQL"),
    ("kv", ["Languages", "Computer"], "HTML, CSS, JSON, YAML, Markdown"),
    ("kv", ["Languages", "Real"], "Portuguese, English, Spanish"),
    ("blank",),
    ("kv", ["Hobbies", "Software"], "Automation, AI Agents, Side Projects"),
    ("kv", ["Hobbies", "Data"], "Dashboards, Data Visualization"),
    ("blank",),
    ("header", "- Contact"),
    ("kv", ["Email", "Personal"], "lucasfmm54@gmail.com"),
    ("kv", ["LinkedIn"], "lucas-fiori"),
    ("kv", ["Profile", "Visitors"], "{visitors}"),
    ("blank",),
    ("header", "- GitHub Stats"),
    ("stats1",),
    ("stats2",),
    ("stats3",),
]

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff", cc="#616e7f", add="#3fb950", dele="#f85149"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069", cc="#c2cfde", add="#1a7f37", dele="#cf222e"),
}


# ---------------------------------------------------------------- data
def gql(query, variables=None):
    r = requests.post("https://api.github.com/graphql", json={"query": query, "variables": variables or {}}, headers=HEAD, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def github_stats():
    q = """query($login:String!,$after:String){ user(login:$login){ createdAt
      followers{totalCount}
      repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
      repositories(ownerAffiliations:OWNER, first:100, after:$after){ totalCount
        pageInfo{hasNextPage endCursor}
        nodes{ name isFork stargazerCount } } } }"""
    after, repos = None, []
    while True:
        u = gql(q, {"login": USER, "after": after})["user"]
        repos += u["repositories"]["nodes"]
        if not u["repositories"]["pageInfo"]["hasNextPage"]:
            break
        after = u["repositories"]["pageInfo"]["endCursor"]
    created = dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    commits, year = 0, created.year
    now = dt.datetime.now(dt.timezone.utc)
    cq = """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
      contributionsCollection(from:$from,to:$to){ totalCommitContributions restrictedContributionsCount } } }"""
    while year <= now.year:
        f = max(created, dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc))
        t = min(now, dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        c = gql(cq, {"login": USER, "from": f.isoformat(), "to": t.isoformat()})["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"]
        year += 1
    add = dele = 0
    for repo in repos:
        if repo["isFork"]:
            continue
        for _ in range(6):
            r = requests.get(f"https://api.github.com/repos/{USER}/{repo['name']}/stats/contributors", headers=HEAD, timeout=60)
            if r.status_code == 202:
                time.sleep(4)
                continue
            if r.status_code == 200 and isinstance(r.json(), list):
                for c in r.json():
                    if (c.get("author") or {}).get("login", "").lower() == USER.lower():
                        add += sum(w["a"] for w in c["weeks"])
                        dele += sum(w["d"] for w in c["weeks"])
            break
    return dict(
        repos=u["repositories"]["totalCount"],
        contrib=u["repositoriesContributedTo"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in repos),
        followers=u["followers"]["totalCount"],
        commits=commits, loc=add - dele, add=add, dele=dele,
    )


def visitors():
    try:
        svg = requests.get(f"https://komarev.com/ghpvc/?username={USER}", timeout=30).text
        nums = re.findall(r">\s*([\d,]+)\s*<", svg)
        return nums[-1] if nums else "—"
    except Exception:
        return "—"


# ---------------------------------------------------------------- svg
def esc(s):
    return html.escape(str(s), quote=False)


def kv_line(y, keys, value, extra_len=0):
    label = ".".join(keys)
    n = WIDTH - len(label) - 1 - len(value) - extra_len
    d = dots(n)
    key_svg = '<tspan class="cc">.</tspan>'.join(f'<tspan class="key">{esc(k)}</tspan>' for k in keys)
    return (f'<tspan x="{X}" y="{y}" class="cc">. </tspan>{key_svg}:'
            f'<tspan class="cc">{d}</tspan><tspan class="value">{esc(value)}</tspan>')


def dots(n):
    return ' ' + '.' * (n - 2) + ' ' if n > 2 else ' '


def fmt(n):
    return f"{n:,}"


def build(theme, s, vis):
    c = THEMES[theme]
    ascii_lines = (ROOT / "profile" / "ascii.txt").read_text(encoding="utf-8").splitlines()
    rows, y = [], 30
    for item in INFO:
        kind = item[0]
        if kind == "header":
            name = item[1]
            rows.append(f'<tspan x="{X}" y="{y}">{esc(name)}</tspan> -{"—" * (WIDTH - len(name) - 4)}-—-')
        elif kind == "blank":
            rows.append(f'<tspan x="{X}" y="{y}" class="cc">. </tspan>')
        elif kind == "kv":
            rows.append(kv_line(y, item[1], item[2].format(visitors=vis)))
        elif kind == "stats1":
            mid = f"{s['repos']} {{Contributed: {s['contrib']}}} | Stars:"
            n1 = 34 - len("Repos:") - len(f"{s['repos']} {{Contributed: {s['contrib']}}}")
            n2 = WIDTH - len("Repos:") - n1 - len(mid) - len(str(s['stars']))
            rows.append(f'<tspan x="{X}" y="{y}" class="cc">. </tspan><tspan class="key">Repos</tspan>:<tspan class="cc">{dots(n1)}</tspan>'
                        f'<tspan class="value">{s["repos"]}</tspan> {{<tspan class="key">Contributed</tspan>: <tspan class="value">{s["contrib"]}</tspan>}}'
                        f' | <tspan class="key">Stars</tspan>:<tspan class="cc">{dots(n2)}</tspan><tspan class="value">{s["stars"]}</tspan>')
        elif kind == "stats2":
            cm = fmt(s['commits'])
            n1 = 34 - len("Commits:") - len(cm)
            n2 = WIDTH - len("Commits:") - n1 - len(cm) - len(" | Followers:") - len(str(s['followers']))
            rows.append(f'<tspan x="{X}" y="{y}" class="cc">. </tspan><tspan class="key">Commits</tspan>:<tspan class="cc">{dots(n1)}</tspan>'
                        f'<tspan class="value">{cm}</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc">{dots(n2)}</tspan>'
                        f'<tspan class="value">{s["followers"]}</tspan>')
        elif kind == "stats3":
            tail = f"{fmt(s['loc'])} ( {fmt(s['add'])}++, {fmt(s['dele'])}-- )"
            n = WIDTH - len("Lines of Code on GitHub:") - len(tail)
            rows.append(f'<tspan x="{X}" y="{y}" class="cc">. </tspan><tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc">{dots(n)}</tspan>'
                        f'<tspan class="value">{fmt(s["loc"])}</tspan> ( <tspan class="addColor">{fmt(s["add"])}++</tspan>, '
                        f'<tspan class="delColor">{fmt(s["dele"])}--</tspan> )')
        y += 20
    height = max(30 + 20 * len(ascii_lines), y) + 10
    art = "\n".join(f'<tspan x="15" y="{30 + 20 * i}">{esc(l)}</tspan>' for i, l in enumerate(ascii_lines))
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="{height}px" font-size="16px">
<style>
@font-face {{ src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }}
.key {{fill: {c['key']};}}
.value {{fill: {c['value']};}}
.addColor {{fill: {c['add']};}}
.delColor {{fill: {c['dele']};}}
.cc {{fill: {c['cc']};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="{height}px" fill="{c['bg']}" rx="15"/>
<text x="15" y="30" fill="{c['text']}" class="ascii">
{art}
</text>
<text x="{X}" y="30" fill="{c['text']}">
{chr(10).join(rows)}
</text>
</svg>
"""


if __name__ == "__main__":
    stats = github_stats()
    vis = visitors()
    print(stats, "visitors:", vis)
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(build(theme, stats, vis), encoding="utf-8")
