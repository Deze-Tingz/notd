"""
notd - intentional clipboard capture
Company: Deze Tingz
Author: Val John @ Deze Tingz
"""

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
import winsound
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
CONFIG_HOME = Path(r"C:\notd")
CONFIG_DIR = CONFIG_HOME / "config"
CONFIG_PATH = CONFIG_DIR / "notd.config.json"

DEFAULT_CONFIG = {
    "project": "notd",
    "owner": "Deze Tingz",
    "root_dir": r"C:\notd_data",
    "text_file_type": "txt",
    "code_file_type": "md",
    "schema_enabled": True,
    "auto_type": True,
    "sounds_enabled": True,
    "success_sound": r"C:\Windows\Media\Windows Hardware Insert.wav",
    "fail_sound": r"C:\Windows\Media\Windows Hardware Fail.wav",
    "max_clip_chars": 200000,
    "hotkey": {
        "enabled": False,
        "ctrl": True,
        "alt": True,
        "shift": False,
        "win": False,
        "key": "N",
    },
    "mouse_capture": {
        "enabled": True,
        "button": "middle",
    },
}


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_dir(CONFIG_HOME)
    ensure_dir(CONFIG_DIR)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=4), encoding="utf-8")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")


# ============================================================
# AUDIO
# ============================================================
def play_sound(cfg: dict, key: str):
    if not cfg.get("sounds_enabled", False):
        return
    path = cfg.get(key, "")
    if path and os.path.isfile(path):
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


# ============================================================
# CLIPBOARD
# ============================================================
def get_clipboard_text(max_chars: int) -> str:
    try:
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
    except Exception:
        return ""
    if not text:
        return ""
    return text[:max_chars]


# ============================================================
# TYPE INFERENCE
# ============================================================
def infer_type(text: str) -> str:
    s = text.strip()
    if re.match(r"^https?://|^www\.", s):
        return "url"
    cmd_prefixes = (
        "git ", "cd ", "ls ", "dir ", "npm ", "pnpm ", "yarn ",
        "python ", "pip ", "pwsh ", "powershell ", "curl ", "docker ",
    )
    if any(s.startswith(p) for p in cmd_prefixes):
        return "command"
    if re.search(r"```|^\s*(function|class|def|import|using|#include)\b", s, re.MULTILINE):
        return "code"
    if re.search(r"Exception|Traceback|Error|ERR_|FATAL", s):
        return "error"
    return "text"


# ============================================================
# FILES
# ============================================================
def captures_dir(cfg: dict) -> Path:
    return Path(cfg["root_dir"]) / "captures"


def resolve_file(cfg: dict, bucket: str) -> Path:
    ext = cfg["code_file_type"] if bucket == "code" else cfg["text_file_type"]
    return captures_dir(cfg) / f"notd_raw.{ext}"


def format_entry(content: str, ctype: str) -> str:
    sep = "\u2501" * 26
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"{sep}\n"
        f"PROJECT: notd\n"
        f"OWNER: Deze Tingz\n"
        f"TIMESTAMP: {ts}\n"
        f"TYPE: {ctype}\n"
        f"\n"
        f"{content}\n"
        f"{sep}\n"
    )


# ============================================================
# COMMANDS
# ============================================================
def cmd_capture(cfg: dict, force_auto_type: bool = False):
    ensure_dir(Path(cfg["root_dir"]))
    ensure_dir(captures_dir(cfg))

    content = get_clipboard_text(cfg["max_clip_chars"])
    if not content or not content.strip():
        play_sound(cfg, "fail_sound")
        return

    if cfg["auto_type"] or force_auto_type:
        ctype = infer_type(content)
    else:
        ctype = "capture"

    bucket = "code" if ctype == "code" else "text"
    fpath = resolve_file(cfg, bucket)

    if str(fpath).endswith(".jsonl"):
        entry = json.dumps({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": ctype,
            "content": content,
        })
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    else:
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(format_entry(content, ctype))

    play_sound(cfg, "success_sound")


def cmd_status(cfg: dict):
    hk = cfg.get("hotkey", {})
    mc = cfg.get("mouse_capture", {})
    print("notd - Deze Tingz")
    print(f"Config: {CONFIG_PATH}")
    print(f"Data:   {cfg['root_dir']}")
    print(f"Hotkey: ctrl={hk.get('ctrl')} alt={hk.get('alt')} key={hk.get('key')} enabled={hk.get('enabled')}")
    print(f"Mouse:  button={mc.get('button')} enabled={mc.get('enabled')}")


def cmd_open(cfg: dict):
    d = captures_dir(cfg)
    ensure_dir(d)
    os.startfile(str(d))


# ============================================================
# HOTKEY (Win32)
# ============================================================
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
HOTKEY_ID = 9001

user32 = ctypes.windll.user32

VK_MAP = {
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59, "Z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


WH_MOUSE_LL = 14
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208

# LRESULT is LONG_PTR (64-bit on x64 Windows)
LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)

kernel32 = ctypes.windll.kernel32

# Set proper function signatures — hooks
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.wintypes.HINSTANCE, ctypes.wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]

# Set proper function signatures — clipboard (pointer-sized returns on x64)
user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL
user32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.wintypes.BOOL
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL

_mouse_hook = None
_mouse_cfg = None


def _get_clipboard_win32() -> str:
    """Read clipboard using Win32 API directly (thread-safe, no tkinter)."""
    CF_UNICODETEXT = 13
    if not user32.OpenClipboard(None):
        return ""
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        p = kernel32.GlobalLock(h)
        if not p:
            return ""
        try:
            return ctypes.wstring_at(p)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def _capture_from_hook(cfg):
    """Capture using Win32 clipboard (avoids tkinter threading issues)."""
    content = _get_clipboard_win32()
    if not content or not content.strip():
        play_sound(cfg, "fail_sound")
        return
    max_chars = cfg.get("max_clip_chars", 200000)
    content = content[:max_chars]
    ctype = infer_type(content) if cfg.get("auto_type", True) else "capture"
    bucket = "code" if ctype == "code" else "text"
    fpath = resolve_file(cfg, bucket)
    ensure_dir(Path(cfg["root_dir"]))
    ensure_dir(captures_dir(cfg))
    with open(fpath, "a", encoding="utf-8") as f:
        f.write(format_entry(content, ctype))
    play_sound(cfg, "success_sound")


def _mouse_hook_proc(nCode, wParam, lParam):
    if nCode >= 0 and wParam in (WM_MBUTTONDOWN, WM_MBUTTONUP):
        if wParam == WM_MBUTTONDOWN:
            threading.Thread(target=_capture_from_hook, args=(_mouse_cfg,), daemon=True).start()
        return 1  # suppress both down and up to kill auto-scroll
    return user32.CallNextHookEx(_mouse_hook, nCode, wParam, lParam)


_mouse_callback = HOOKPROC(_mouse_hook_proc)


def cmd_listen(cfg: dict):
    global _mouse_hook, _mouse_cfg
    _mouse_cfg = cfg

    mc = cfg.get("mouse_capture", {})
    hk = cfg.get("hotkey", {})
    has_mouse = mc.get("enabled", False)
    has_hotkey = hk.get("enabled", False)

    if not has_mouse and not has_hotkey:
        print("Both mouse capture and hotkey are disabled in config.")
        return

    # Register keyboard hotkey if enabled
    if has_hotkey:
        mods = 0
        if hk.get("ctrl"):
            mods |= MOD_CTRL
        if hk.get("alt"):
            mods |= MOD_ALT
        if hk.get("shift"):
            mods |= MOD_SHIFT
        if hk.get("win"):
            mods |= MOD_WIN
        key_name = hk.get("key", "N").upper()
        vk = VK_MAP.get(key_name, 0x4E)
        if not user32.RegisterHotKey(None, HOTKEY_ID, mods, vk):
            print("Failed to register hotkey.")
        else:
            print(f"Keyboard hotkey active: {key_name}")

    # Install mouse hook if enabled
    if has_mouse:
        _mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL, _mouse_callback,
            ctypes.windll.kernel32.GetModuleHandleW(None), 0,
        )
        if not _mouse_hook:
            print("Failed to install mouse hook.")
        else:
            print("Middle mouse button capture active.")

    print("notd listening. Press Ctrl+C to stop.")

    try:
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                cmd_capture(cfg)
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        pass
    finally:
        if has_hotkey:
            user32.UnregisterHotKey(None, HOTKEY_ID)
        if _mouse_hook:
            user32.UnhookWindowsHookEx(_mouse_hook)


# ============================================================
# CONFIG UI (tkinter)
# ============================================================
def cmd_config(cfg: dict):
    root = tk.Tk()
    root.title("notd Settings - Deze Tingz")
    root.geometry("500x350")
    root.resizable(False, False)

    # Data folder
    tk.Label(root, text="Data folder").place(x=20, y=20)
    root_var = tk.StringVar(value=cfg["root_dir"])
    tk.Entry(root, textvariable=root_var, width=50).place(x=20, y=45)

    def browse():
        from tkinter import filedialog
        d = filedialog.askdirectory()
        if d:
            root_var.set(d)

    tk.Button(root, text="Browse", command=browse).place(x=410, y=43)

    # Hotkey section
    hk = cfg.get("hotkey", {})
    tk.Label(root, text="Keyboard hotkey").place(x=20, y=90)

    key_var = tk.StringVar(value=hk.get("key", "N"))
    key_entry = tk.Entry(root, textvariable=key_var, width=10, state="readonly")
    key_entry.place(x=20, y=115)

    def on_key(event):
        key_var.set(event.keysym.upper())

    key_entry.bind("<Key>", on_key)
    key_entry.config(state="normal")

    ctrl_var = tk.BooleanVar(value=hk.get("ctrl", True))
    alt_var = tk.BooleanVar(value=hk.get("alt", True))
    shift_var = tk.BooleanVar(value=hk.get("shift", False))
    enable_var = tk.BooleanVar(value=hk.get("enabled", False))

    tk.Checkbutton(root, text="Ctrl", variable=ctrl_var).place(x=120, y=115)
    tk.Checkbutton(root, text="Alt", variable=alt_var).place(x=180, y=115)
    tk.Checkbutton(root, text="Shift", variable=shift_var).place(x=240, y=115)
    tk.Checkbutton(root, text="Enable hotkey", variable=enable_var).place(x=310, y=115)

    def save():
        cfg["root_dir"] = root_var.get()
        cfg["hotkey"] = {
            "enabled": enable_var.get(),
            "ctrl": ctrl_var.get(),
            "alt": alt_var.get(),
            "shift": shift_var.get(),
            "win": False,
            "key": key_var.get(),
        }
        save_config(cfg)
        root.destroy()

    tk.Button(root, text="Save", command=save).place(x=340, y=290)

    root.mainloop()


# ============================================================
# DISPATCH
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="notd - clipboard capture tool")
    parser.add_argument(
        "command",
        nargs="?",
        default="capture",
        choices=["capture", "config", "status", "open", "listen", "hotkey"],
    )
    parser.add_argument("--auto-type", action="store_true")
    parser.add_argument("--silent", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    if args.silent:
        cfg["sounds_enabled"] = False

    commands = {
        "capture": lambda: cmd_capture(cfg, force_auto_type=args.auto_type),
        "config": lambda: cmd_config(cfg),
        "status": lambda: cmd_status(cfg),
        "open": lambda: cmd_open(cfg),
        "listen": lambda: cmd_listen(cfg),
        "hotkey": lambda: cmd_listen(cfg),
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
