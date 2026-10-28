"""Local masked configuration form; no clipboard reading or network transmission."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.providers import key_plausible, local_config


def main():
    window = tk.Tk()
    window.title("短视频脚本 Agent — 千问本地配置")
    window.geometry("700x330")
    window.resizable(False, False)
    body = ttk.Frame(window, padding=22)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="配置 qwen-plus（密钥仅保存到本地 .env）", font=("Microsoft YaHei", 13)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
    ttk.Label(body, text="API 接口地址").grid(row=1, column=0, sticky="w", pady=7)
    endpoint = ttk.Entry(body, width=65)
    endpoint.insert(0, local_config(ROOT).get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    endpoint.grid(row=1, column=1, sticky="w")
    ttk.Label(body, text="API Key").grid(row=2, column=0, sticky="w", pady=10)
    key_entry = ttk.Entry(body, width=65, show="*")
    key_entry.grid(row=2, column=1, sticky="w")
    ttk.Label(body, text="点击 Key 输入框，按 Ctrl+V 粘贴创建时复制的完整密钥。\n使用控制台显示的 Base URL；工作空间 Key 支持带点号的新格式。\n不要粘贴列表中带星号的脱敏 Key。输入框显示星号正常。", wraplength=610).grid(row=3, column=0, columnspan=2, sticky="w", pady=12)
    status = tk.StringVar(value="等待输入；没有发送任何模型请求。")
    def save():
        key = key_entry.get().strip()
        base = endpoint.get().strip().rstrip("/")
        if not key_plausible(key):
            messagebox.showerror("未保存", "Key 不完整：请从百炼控制台完整复制以 sk- 开头的密钥。", parent=window)
            return
        from urllib.parse import urlsplit
        url = urlsplit(base)
        if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment or any(c in base for c in "\r\n\"'"):
            messagebox.showerror("未保存", "请填写正确的 HTTPS 兼容接口地址。", parent=window)
            return
        try:
            (ROOT / ".env").write_text(f"DASHSCOPE_API_KEY={key}\nQWEN_MODEL=qwen-plus\nQWEN_BASE_URL={base}\nQWEN_TIMEOUT_SECONDS=60\n", encoding="utf-8")
        except OSError:
            messagebox.showerror("未保存", "本地文件写入失败，请检查目录权限。", parent=window)
            return
        key_entry.delete(0, "end")
        status.set("已保存本地配置，未显示密钥。可关闭窗口并告诉 AI：配置好了。")
        messagebox.showinfo("已保存", "配置已保存到项目 .env。\n没有显示密钥；格式检查不等于接口认证成功。\n请关闭窗口并告诉 AI：配置好了。", parent=window)
    ttk.Button(body, text="保存本地配置", command=save).grid(row=4, column=1, sticky="e", pady=8)
    ttk.Label(body, textvariable=status, wraplength=640).grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
    key_entry.focus_set()
    window.mainloop()


if __name__ == "__main__":
    main()
