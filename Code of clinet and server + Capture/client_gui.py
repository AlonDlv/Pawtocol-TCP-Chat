import socket
import threading
import queue
import tkinter as tk
from tkinter import messagebox


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pawtocol TCP Chat 🐾")

        self.sock = None
        self.connected = False
        self.rx_thread = None
        self.q = queue.Queue()

        self.in_chat = False
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self._poll)

    def _build(self):
        frm = tk.Frame(self.root, padx=10, pady=10)
        frm.pack(fill="both", expand=True)

        top = tk.Frame(frm)
        top.pack(fill="x")

        tk.Label(top, text="Server IP 🖧").grid(row=0, column=0, sticky="w")
        self.ip = tk.Entry(top, width=16)
        self.ip.insert(0, "127.0.0.1")
        self.ip.grid(row=0, column=1, padx=5)

        tk.Label(top, text="Port 🔌").grid(row=0, column=2, sticky="w")
        self.port = tk.Entry(top, width=8)
        self.port.insert(0, "5000")
        self.port.grid(row=0, column=3, padx=5)

        tk.Label(top, text="Name 🐱").grid(row=1, column=0, sticky="w")
        self.name = tk.Entry(top, width=16)
        self.name.grid(row=1, column=1, padx=5)

        self.btn_connect = tk.Button(top, text="Connect 😺", command=self.connect)
        self.btn_connect.grid(row=0, column=4, rowspan=2, padx=10, sticky="ns")

        mid = tk.Frame(frm)
        mid.pack(fill="both", expand=True)

        left = tk.Frame(mid)
        left.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left, text="Online cats 🐾").pack(anchor="w")
        self.users = tk.Listbox(left, height=10, width=22)
        self.users.pack(fill="y", expand=False)

        btns = tk.Frame(left)
        btns.pack(fill="x", pady=6)

        self.btn_refresh = tk.Button(btns, text="Refresh 😼", command=self.refresh_users, state="disabled")
        self.btn_refresh.pack(side="left", fill="x", expand=True)

        self.btn_chat = tk.Button(btns, text="Start Chat 🐈", command=self.start_chat, state="disabled")
        self.btn_chat.pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.chat = tk.Text(mid, height=18, state="disabled", wrap="word")
        self.chat.pack(side="left", fill="both", expand=True)

        bottom = tk.Frame(frm)
        bottom.pack(fill="x", pady=(10, 0))

        self.msg = tk.Entry(bottom)
        self.msg.pack(side="left", fill="x", expand=True)
        self.msg.bind("<Return>", lambda e: self.send_msg())

        self.btn_send = tk.Button(bottom, text="Send 😽", command=self.send_msg, state="disabled")
        self.btn_send.pack(side="left", padx=8)

        self.btn_leave = tk.Button(bottom, text="Leave Chat 🙀", command=self.leave_chat, state="disabled")
        self.btn_leave.pack(side="left")

    def log(self, text):
        self.chat.configure(state="normal")
        self.chat.insert("end", text + "\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def send_line(self, s):
        try:
            self.sock.send((s + "\n").encode())
        except:
            self.q.put(("DISCONNECT", "Meow… connection lost 🐾"))

    def connect(self):
        if self.connected:
            return

        ip = self.ip.get().strip()
        try:
            port = int(self.port.get().strip())
        except:
            messagebox.showerror("Hiss!", "Port must be a number 😾")
            return

        name = self.name.get().strip()
        if not name:
            messagebox.showerror("Nyah!", "Enter your name, little cat 🐱")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, port))
            self.connected = True

            self.btn_connect.config(state="disabled")
            self.btn_refresh.config(state="normal")
            self.btn_chat.config(state="normal")

            self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.rx_thread.start()

            self.send_line(f"HELLO {name}")
            self.log(f"[SYSTEM] Meow! Connected as {name} 😺")
            self.refresh_users()

        except Exception as e:
            self.connected = False
            try:
                if self.sock:
                    self.sock.close()
            except:
                pass
            self.sock = None
            messagebox.showerror("Hiss!", f"Connection failed 😿\n{e}")

    def _rx_loop(self):
        buf = ""
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                buf += data.decode(errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.q.put(("LINE", line))
        except:
            pass
        self.q.put(("DISCONNECT", "Server went to sleep… 🐈‍⬛"))

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "LINE":
                    self._handle_line(payload)
                elif kind == "DISCONNECT":
                    self._handle_disconnect(payload)
        except queue.Empty:
            pass

        self.root.after(50, self._poll)

    def _handle_line(self, line):
        if line.startswith("USERS "):
            names = line[6:]
            self.users.delete(0, "end")
            if names:
                for n in names.split(","):
                    if n:
                        self.users.insert("end", n)

        elif line.startswith("SYSTEM "):
            msg = line[7:].strip()
            self.log(f"[SYSTEM] {msg} 🐾")

            if ("Connected to " in msg) or ("connected to you" in msg):
                self.in_chat = True
                self.btn_send.config(state="normal")
                self.btn_leave.config(state="normal")

            if ("You left the chat." in msg) or ("Other side left the chat." in msg):
                self.in_chat = False
                self.btn_send.config(state="disabled")
                self.btn_leave.config(state="disabled")

        elif line.startswith("CHAT "):
            self.log(line[5:] + " 😽")

        else:
            self.log(line)

    def refresh_users(self):
        if self.connected:
            self.send_line("LIST")

    def start_chat(self):
        if not self.connected:
            return
        if self.in_chat:
            messagebox.showinfo("Meow!", "Already chatting — leave first 😼")
            return

        sel = self.users.curselection()
        if not sel:
            messagebox.showinfo("Nyah!", "Pick a cat from the list 🐾")
            return

        target = self.users.get(sel[0])
        myname = self.name.get().strip()

        if target == myname:
            messagebox.showinfo("Hiss!", "You can’t chat with yourself 😹")
            return

        self.send_line(f"CHAT {target}")

    def send_msg(self):
        if not self.connected or not self.sock:
            return
        if not self.in_chat:
            messagebox.showinfo("Meow!", "You’re not in a chat yet 🐈")
            return

        text = self.msg.get().strip()
        if not text:
            return

        myname = self.name.get().strip() or "Me"
        self.log(f"{myname}: {text} 😸")

        self.send_line(f"MSG {text}")
        self.msg.delete(0, "end")

    def leave_chat(self):
        if not self.connected:
            return
        if not self.in_chat:
            messagebox.showinfo("Nyah!", "No chat to leave 😺")
            return

        self.send_line("QUIT")
        self.in_chat = False
        self.btn_send.config(state="disabled")
        self.btn_leave.config(state="disabled")

    def _handle_disconnect(self, reason):
        if self.connected:
            self.connected = False
            self.in_chat = False

            self.btn_connect.config(state="normal")
            self.btn_refresh.config(state="disabled")
            self.btn_chat.config(state="disabled")
            self.btn_send.config(state="disabled")
            self.btn_leave.config(state="disabled")

            try:
                if self.sock:
                    self.sock.close()
            except:
                pass
            self.sock = None

            messagebox.showwarning("Meow…", reason)

    def on_close(self):
        try:
            if self.connected and self.in_chat:
                self.send_line("QUIT")
            if self.sock:
                self.sock.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap("icon.ico")
    ClientGUI(root)
    root.mainloop()
