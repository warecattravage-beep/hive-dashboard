#!/home/linuxbrew/.linuxbrew/bin/python3
"""✦ Hive TUI — System Dashboard (terminal UI for SSH/manual use)."""
import asyncio, json, os, subprocess, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Label
from textual.reactive import reactive
from textual import events

KST = timezone(timedelta(hours=9))

# ── Collectors (same as web dashboard) ─────────────────────────

def get_services():
    svcs = [("sentinel-watch","system","🛡 Sentinel"),("tailscaled","system","🔗 Tailscale"),
            ("openclaw-gateway","user","🧠 OpenClaw"),("signal-cli","user","💬 Signal"),
            ("hive-dashboard","user","📊 Hive")]
    results = []
    for name, scope, label in svcs:
        try:
            cmd = ["systemctl"] if scope == "system" else ["systemctl", "--user"]
            r = subprocess.run(cmd + ["is-active", name], capture_output=True, text=True, timeout=5)
            s = r.stdout.strip()
            results.append((label, {"active":"✅","inactive":"⬜","failed":"❌"}.get(s,"❓"), s))
        except:
            results.append((label, "❓", "unknown"))
    return results

def get_hardware():
    d = {}
    try:
        d["load"] = os.getloadavg()
        r = subprocess.run(["sensors","-u"], capture_output=True, text=True, timeout=5)
        for l in r.stdout.split("\n"):
            if "temp1_input" in l:
                d["temp"] = f"{float(l.split(':')[1].strip()):.0f}°C"
                break
    except:
        d["load"] = (0,0,0); d["temp"] = "N/A"
    try:
        r = subprocess.run(["free","-h"], capture_output=True, text=True, timeout=5)
        p = r.stdout.split("\n")[1].split()
        d["mem"] = f"{p[2]}/{p[1]}"
    except:
        d["mem"] = "N/A"
    try:
        r = subprocess.run(["df","-h","/"], capture_output=True, text=True, timeout=5)
        p = r.stdout.split("\n")[1].split()
        d["disk"] = f"{p[4]} ({p[2]}/{p[1]})"
    except:
        d["disk"] = "N/A"
    try:
        with open("/proc/uptime") as f:
            s = float(f.read().split()[0])
        d_, r_ = divmod(int(s), 86400); h, m = divmod(r_, 3600)
        d["up"] = f"{d_}d {h}h {m//60}m"
    except:
        d["up"] = "N/A"
    return d

def get_network():
    try:
        r = subprocess.run(["ip","-4","addr","show"], capture_output=True, text=True, timeout=5)
        return [l.strip().split()[1].split("/")[0] for l in r.stdout.split("\n")
                if "inet " in l and not l.strip().split()[1].startswith("127.")]
    except:
        return []

def get_alerts():
    try:
        log = Path.home() / "Projects" / "sentinel-watch" / "log" / "sentinel.log"
        return [l.split("ALERT:")[-1].strip() for l in log.read_text().split("\n") if "ALERT:" in l][-3:]
    except:
        return []

def get_programs():
    notable = {"signal-cli":"💬 Signal","obsidian":"📝 Obsidian","firefox":"🦊 Firefox",
               "chrome":"🌐 Chrome","python3":"🐍 Python","node":"🟢 Node.js","code":"💻 VS Code",
               "sshd":"🔑 SSH","sentinel":"🛡 Sentinel","hive":"📊 Hive"}
    try:
        r = subprocess.run(["ps","aux"], capture_output=True, text=True, timeout=10)
        seen, res = set(), []
        for line in r.stdout.split("\n"):
            for key, label in notable.items():
                if key in line and "grep" not in line and label not in seen:
                    cols = line.split()
                    if len(cols) >= 11:
                        seen.add(label)
                        res.append((label, cols[1], cols[2], cols[3]))
                    break
        return res
    except:
        return []

# ── TUI App ──────────────────────────────────────────────────

class HiveApp(App):
    TITLE = "✦ Hive Dashboard"
    CSS = """
    Screen { background: #0d1117; }
    Header { background: #161b22; color: #58a6ff; }
    Footer { background: #161b22; }
    .panel { border: solid #30363d; height: auto; margin: 0 0 1 0; }
    .panel-title { background: #21262d; color: #58a6ff; text-style: bold; padding: 0 1; }
    .stat { color: #c9d1d9; }
    .label { color: #8b949e; }
    .ok { color: #3fb950; }
    .warn { color: #d29922; }
    .err { color: #f85149; }
    DataTable { height: auto; }
    #main { padding: 0 1; }
    #footer-label { color: #484f58; text-align: center; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main"):
            with Vertical(classes="panel"):
                yield Static("🖥 System", classes="panel-title")
                yield Static("", id="sys-info", classes="stat")
            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("⚙️ Hardware", classes="panel-title")
                    yield Static("", id="hw-info", classes="stat")
                with Vertical(classes="panel"):
                    yield Static("🌐 Network", classes="panel-title")
                    yield Static("", id="net-info", classes="stat")
            with Vertical(classes="panel"):
                yield Static("🔧 Services", classes="panel-title")
                yield DataTable(id="svc-table", classes="stat")
            with Vertical(classes="panel"):
                yield Static("🚀 Programs", classes="panel-title")
                yield DataTable(id="prog-table", classes="stat")
            with Vertical(classes="panel"):
                yield Static("🚨 Alerts", classes="panel-title")
                yield Static("", id="alert-info", classes="stat")
            yield Static("", id="footer-label")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(5, self.refresh_all)
        self.refresh_all()

    def refresh_all(self) -> None:
        now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
        hw = get_hardware()
        ips = get_network()
        svcs = get_services()
        progs = get_programs()
        alerts = get_alerts()
        host = os.uname().nodename

        # System
        self.query_one("#sys-info", Static).update(
            f"  Host: {host}  |  OS: Ubuntu 26.04  |  ⏱ {hw['up']}  |  🕐 {now}"
        )

        # Hardware
        self.query_one("#hw-info", Static).update(
            f"  🌡 {hw['temp']}  |  📊 CPU: {hw['load'][0]:.1f}  |  💾 {hw['mem']}  |  💿 {hw['disk']}"
        )

        # Network
        net_str = "  " + "  ".join(f"📍 {ip}" for ip in ips) if ips else "  No IPs"
        self.query_one("#net-info", Static).update(net_str)

        # Services
        table = self.query_one("#svc-table", DataTable)
        table.clear()
        table.add_columns("Service", "Status")
        table.add_rows([(l, f"{i} {s}") for l, i, s in svcs])

        # Programs
        ptable = self.query_one("#prog-table", DataTable)
        ptable.clear()
        ptable.add_columns("Program", "PID", "CPU%", "MEM%")
        ptable.add_rows([(l, p, c, m) for l, p, c, m in progs]) if progs else ptable.add_rows([("(none)", "", "", "")])

        # Alerts
        alert_str = "\n".join(f"  🔴 {a}" for a in alerts) if alerts else "  ✅ No recent alerts"
        self.query_one("#alert-info", Static).update(alert_str)

        # Footer
        self.query_one("#footer-label", Static).update(f"  ✦ Auto-refresh every 5s  |  Ctrl+C to exit")


if __name__ == "__main__":
    app = HiveApp()
    app.run()
