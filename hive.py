#!/home/linuxbrew/.linuxbrew/bin/python3
"""✦ Hive — System Dashboard for the mini PC ecosystem."""
import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

class Collectors:

    @staticmethod
    def services() -> list[dict]:
        svcs = [
            ("sentinel-watch", "system", "🛡 Sentinel Watch"),
            ("tailscaled", "system", "🔗 Tailscale"),
            ("openclaw-gateway", "user", "🧠 OpenClaw"),
            ("signal-cli", "user", "💬 Signal CLI"),
        ]
        results = []
        for name, scope, label in svcs:
            try:
                if scope == "system":
                    r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
                else:
                    r = subprocess.run(["systemctl", "--user", "is-active", name], capture_output=True, text=True, timeout=5)
                status = r.stdout.strip()
                icon = {"active": "✅", "inactive": "⬜", "failed": "❌"}.get(status, "❓")
                results.append({"label": label, "name": name, "status": status, "icon": icon})
            except:
                results.append({"label": label, "name": name, "status": "unknown", "icon": "❓"})
        return results

    @staticmethod
    def hardware() -> dict:
        data = {}
        try:
            load = os.getloadavg()
            data["cpu_load"] = f"{load[0]:.1f} {load[1]:.1f} {load[2]:.1f}"
            r = subprocess.run(["sensors", "-u"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.split("\n"):
                if "temp1_input" in line:
                    data["cpu_temp"] = f"{float(line.split(':')[1].strip()):.0f}°C"
                    break
        except:
            data["cpu_load"] = data["cpu_temp"] = "N/A"
        try:
            r = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
            parts = r.stdout.split("\n")[1].split()
            data["memory"] = f"{parts[2]} / {parts[1]}"
        except:
            data["memory"] = "N/A"
        try:
            r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            parts = r.stdout.split("\n")[1].split()
            data["disk"] = f"{parts[4]} used ({parts[2]} / {parts[1]})"
        except:
            data["disk"] = "N/A"
        try:
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            d, r = divmod(int(secs), 86400)
            h, m = divmod(r, 3600)
            data["uptime"] = f"{d}d {h}h {m // 60}m"
        except:
            data["uptime"] = "N/A"
        return data

    @staticmethod
    def network() -> dict:
        data = {}
        try:
            r = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True, timeout=5)
            data["ips"] = [l.strip().split()[1].split("/")[0] for l in r.stdout.split("\n") if "inet " in l and not l.strip().split()[1].startswith("127.")]
        except:
            data["ips"] = []
        try:
            r = subprocess.run(["tailscale", "status", "--active"], capture_output=True, text=True, timeout=5)
            data["tailscale"] = r.stdout.strip()
        except:
            data["tailscale"] = "N/A"
        return data

    @staticmethod
    def programs() -> list[dict]:
        """Notable user programs currently running."""
        notable = {
            "signal-cli": "💬 Signal Messaging",
            "obsidian": "📝 Obsidian Notes",
            "firefox": "🦊 Firefox",
            "chrome": "🌐 Chrome",
            "telegram": "✈️ Telegram",
            "spotify": "🎵 Spotify",
            "code": "💻 VS Code",
            "gnome-terminal": "📟 Terminal",
            "node": "🟢 Node.js",
            "python3": "🐍 Python",
            "sshd": "🔑 SSH Server",
            "signal-cli": "💬 Signal CLI",
            "hive": "📊 Hive Dashboard",
            "sentinel": "🛡 Sentinel Watch",
        }
        try:
            r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            found = []
            for line in r.stdout.split("\n"):
                for key, label in notable.items():
                    if key in line and "grep" not in line and "defunct" not in line:
                        cols = line.split()
                        if len(cols) >= 11:
                            found.append({
                                "label": label,
                                "pid": cols[1],
                                "cpu": cols[2],
                                "mem": cols[3],
                                "cmd": " ".join(cols[10:])[:50],
                            })
                        break
            # Deduplicate by label
            seen = set()
            unique = []
            for p in found:
                if p["label"] not in seen:
                    seen.add(p["label"])
                    unique.append(p)
            return sorted(unique, key=lambda x: float(x["mem"]), reverse=True)
        except:
            return []

    @staticmethod
    def alerts() -> list[str]:
        try:
            log = Path.home() / "Projects" / "sentinel-watch" / "log" / "sentinel.log"
            if log.exists():
                lines = [l.split("ALERT:")[-1].strip() for l in log.read_text().split("\n") if "ALERT:" in l]
                return lines[-5:]
        except:
            pass
        return []

    @staticmethod
    def system() -> dict:
        return {
            "hostname": os.uname().nodename,
            "os": "Ubuntu 26.04",
            "kernel": subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=5).stdout.strip(),
            "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        }

    @staticmethod
    def projects() -> list[dict]:
        return [
            {"name": "Onyx Agent", "desc": "Gemma 4 E4B + Ollama agent", "status": "on GitHub", "url": "https://github.com/warecattravage-beep/onyx-agent-v3"},
            {"name": "Sentinel Watch", "desc": "Security + system monitor", "status": "running", "url": "https://github.com/warecattravage-beep/sentinel-watch"},
            {"name": "Notion Diary", "desc": "Daily diary cron 23:00 KST", "status": "scheduled"},
            {"name": "Lumina", "desc": "AI assistant via Telegram", "status": "online"},
        ]


def _pcard(title: str, body: str) -> str:
    return f'<div class="card"><h3>{title}</h3>{body}</div>'

def _stat(label: str, value: str) -> str:
    return f'<div class="stat"><span class="label">{label}</span><span class="value">{value}</span></div>'

def _program_row(p: dict) -> str:
    return f'<div class="stat"><span class="label">{p["label"]}</span><span class="value">PID {p["pid"]} &middot; {p["cpu"]}%CPU &middot; {p["mem"]}%MEM</span></div>'


def _service_row(s: dict) -> str:
    cls = "ok" if s["status"] == "active" else "err"
    return f'<div class="stat"><span class="label">{s["icon"]} {s["label"]}</span><span class="value"><span class="badge badge-{cls}">{s["status"]}</span></span></div>'

def _project_row(p: dict) -> str:
    url = f' <a href="{p["url"]}" target=_blank>↗</a>' if "url" in p else ""
    return f'<div class="project"><span class="project-name">{p["name"]}</span><span class="project-desc">{p["desc"]}</span>{url}<span style="margin-left:auto;font-size:0.8rem;color:#8b949e;">{p["status"]}</span></div>'


def render() -> str:
    c = Collectors()
    hw = c.hardware()
    net = c.network()
    now = datetime.now(KST)

    cards = _pcard("System", _stat("Host", c.system()["hostname"]) + _stat("OS", c.system()["os"]) +
                   _stat("Kernel", c.system()["kernel"]) + _stat("Uptime", hw["uptime"]) + _stat("Time", c.system()["time"]))
    cards += _pcard("Hardware", _stat("CPU Temp", hw["cpu_temp"]) + _stat("CPU Load", hw["cpu_load"]) +
                    _stat("Memory", hw["memory"]) + _stat("Disk (/)", hw["disk"]))
    ips_html = '<div class="ip-list">' + "".join(f'<span class="ip-tag">{ip}</span>' for ip in net["ips"]) + '</div>'
    cards += _pcard("Network", _stat("IPs", ips_html) +
                    f'<div class="stat" style="display:block;"><span class="label">Tailscale</span><pre style="font-size:0.75rem;color:#8b949e;margin-top:4px;">{net["tailscale"][:200]}</pre></div>')
    cards += _pcard("Services", "".join(_service_row(s) for s in c.services()))
    progs = c.programs()
    if progs:
        cards += _pcard("Running Programs", "".join(_program_row(p) for p in progs))

    projects_html = "".join(_project_row(p) for p in c.projects())
    alerts_html = "".join(f'<div class="alert-item">{a}</div>' for a in c.alerts()) or '<div style="color:#3fb950">No recent alerts</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hive Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,system-ui,sans-serif; background:#0d1117; color:#c9d1d9; padding:20px; }}
  h1 {{ color:#58a6ff; font-size:1.5rem; margin-bottom:20px; }}
  h2 {{ color:#8b949e; font-size:1rem; text-transform:uppercase; letter-spacing:1px; margin:20px 0 10px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; }}
  .card h3 {{ color:#58a6ff; font-size:0.95rem; margin-bottom:8px; }}
  .stat {{ display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #21262d; font-size:0.85rem; }}
  .stat:last-child {{ border-bottom:none; }}
  .label {{ color:#8b949e; }}
  .value {{ color:#c9d1d9; text-align:right; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }}
  .badge-ok {{ background:#1b4725; color:#3fb950; }}
  .badge-err {{ background:#5c1010; color:#f85149; }}
  .project {{ display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid #21262d; }}
  .project:last-child {{ border-bottom:none; }}
  .project-name {{ color:#c9d1d9; font-weight:600; font-size:0.85rem; }}
  .project-desc {{ color:#8b949e; font-size:0.75rem; }}
  a {{ color:#58a6ff; text-decoration:none; }}
  .alert-item {{ padding:6px 0; border-bottom:1px solid #21262d; font-size:0.8rem; color:#f85149; }}
  .alert-item:last-child {{ border-bottom:none; }}
  .footer {{ text-align:center; color:#484f58; font-size:0.75rem; margin-top:30px; }}
  .ip-list {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .ip-tag {{ background:#21262d; padding:2px 8px; border-radius:4px; font-family:monospace; font-size:0.8rem; color:#8b949e; }}
</style>
</head>
<body>
<h1>Hive &mdash; {now.strftime('%b %d, %Y')}</h1>
<div class="grid">{cards}</div>

<h2>Projects</h2>
<div class="grid"><div class="card" style="grid-column:1/-1;">{projects_html}</div></div>

<h2>Recent Sentinel Alerts</h2>
<div class="grid"><div class="card" style="grid-column:1/-1;">{alerts_html}</div></div>

<div class="footer">Hive Dashboard &mdash; refresh in <span id="countdown">30</span>s</div>
<script>
let t=30;setInterval(function(){{
document.getElementById('countdown').textContent=--t;if(t<=0)location.reload();
}},1000);
</script>
</body>
</html>"""


async def handle(reader, writer):
    req = await reader.read(4096)
    path = req.decode(errors="ignore").split(" ")[1] if b" " in req else "/"
    if path == "/":
        body = render().encode()
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: " +
                     str(len(body)).encode() + b"\r\n\r\n" + body)
    elif path == "/api":
        c = Collectors()
        data = json.dumps({"services": c.services(), "hardware": c.hardware(),
                           "network": c.network(), "system": c.system(), "projects": c.projects()}).encode()
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " +
                     str(len(data)).encode() + b"\r\n\r\n" + data)
    else:
        writer.write(b"HTTP/1.1 404\r\n\r\n")
    await writer.drain()
    writer.close()


async def main():
    port = int(os.environ.get("HIVE_PORT", 9090))
    server = await asyncio.start_server(handle, "0.0.0.0", port)
    print(f"Hive Dashboard -> http://0.0.0.0:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
