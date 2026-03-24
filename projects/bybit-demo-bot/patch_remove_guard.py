import re
from pathlib import Path

p = Path(r"C:\Users\ADMIN\.openclaw\workspace\projects\bybit-demo-bot\bot.py")
text = p.read_text(encoding="utf-8")

# 1) Make entry_signal always True (aggressive mode)
pattern_entry = re.compile(
    r"def entry_signal\(session: HTTP, cfg: BotConfig, symbol: str, bias: str, \*, first_trade: bool\) -> bool:\n"
    r"    \"\"\".*?\"\"\"\n\n"
    r"    if first_trade:\n"
    r"        return True\n\n"
    r"    now = time\.time\(\)\n"
    r"    sec_in_block = int\(now\) % \(15 \* 60\)\n"
    r"    return sec_in_block <= 20\n",
    re.S,
)

replacement_entry = (
    "def entry_signal(session: HTTP, cfg: BotConfig, symbol: str, bias: str, *, first_trade: bool) -> bool:\n"
    "    \"\"\"Entry trigger (demo aggressive mode).\n\n"
    "    With cooldown=0 and no 15m guard, we enter whenever flat and allowed by max_entries_per_hour.\n"
    "    \"\"\"\n\n"
    "    return True\n"
)

text, n1 = pattern_entry.subn(replacement_entry, text)

# 2) Remove 15m block guard
pattern_guard = re.compile(
    r"\n\s*# guard: only one entry per 15m block \(skip this guard for the very first trade\)\n"
    r"\s*block = int\(time\.time\(\)\) // \(15 \* 60\)\n"
    r"\s*if \(not first_trade\) and state\.get\(\"last_15m_block\"\) == block:\n"
    r"\s*\s*time\.sleep\(cfg\.poll_seconds\)\n"
    r"\s*\s*continue\n",
    re.S,
)
text, n2 = pattern_guard.subn("\n", text)

# 3) Remove writes to last_15m_block
text2 = text.replace('state["last_15m_block"] = int(time.time()) // (15 * 60)\n', '')

p.write_text(text2, encoding="utf-8")

print("PATCHED", {"entry_signal_replaced": n1, "guard_removed": n2})
