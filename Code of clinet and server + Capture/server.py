import socket
import threading

clients = {}   # name -> conn
partners = {}  # name -> partner_name
lock = threading.Lock()

def send_line(conn, s):
    try:
        conn.send((s + "\n").encode())
    except:
        pass

def broadcast_users():
    with lock:
        names = list(clients.keys())
        conns = list(clients.values())
    payload = "USERS " + ",".join(names)
    for c in conns:
        send_line(c, payload)

def disconnect(name, reason="DISCONNECTED"):
    with lock:
        conn = clients.pop(name, None)
        partner = partners.pop(name, None)
        partner_conn = None
        if partner:
            partners.pop(partner, None)
            partner_conn = clients.get(partner)

    if partner_conn:
        send_line(partner_conn, f"SYSTEM Other side disconnected. Chat closed.")
        try:
            partner_conn.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            partner_conn.close()
        except:
            pass
        with lock:
            clients.pop(partner, None)

    if conn:
        try:
            send_line(conn, f"SYSTEM {reason}")
        except:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            conn.close()
        except:
            pass

    broadcast_users()

def handle_client(conn, addr):
    name = None
    try:
        send_line(conn, "SYSTEM Welcome.")

        buffer = ""
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode(errors="ignore")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                if name is None:
                    if not line.startswith("HELLO "):
                        send_line(conn, "SYSTEM First command must be: HELLO <name>")
                        continue
                    candidate = line[6:].strip()
                    if not candidate:
                        send_line(conn, "SYSTEM Name cannot be empty.")
                        continue
                    with lock:
                        if candidate in clients:
                            send_line(conn, "SYSTEM Name already taken.")
                            continue
                        name = candidate
                        clients[name] = conn
                    send_line(conn, f"SYSTEM Hello {name}. Choose your fellow feline from list to start.")
                    broadcast_users()
                    continue

                # after HELLO:
                if line == "LIST":
                    with lock:
                        names = list(clients.keys())
                    send_line(conn, "USERS " + ",".join(names))

                elif line.startswith("CHAT "):
                    target = line[5:].strip()
                    if not target:
                        send_line(conn, "SYSTEM Usage: CHAT <name>")
                        continue
                    with lock:
                        target_conn = clients.get(target)
                        my_partner = partners.get(name)
                        target_partner = partners.get(target)

                    if target_conn is None:
                        send_line(conn, "SYSTEM User not found.")
                        continue
                    if target == name:
                        send_line(conn, "SYSTEM You cannot chat with yourself 🙂")
                        continue
                    if my_partner is not None:
                        send_line(conn, "SYSTEM You are already in a chat. Type QUIT to leave.")
                        continue
                    if target_partner is not None:
                        send_line(conn, "SYSTEM That user is busy.")
                        continue

                    with lock:
                        partners[name] = target
                        partners[target] = name

                    send_line(conn, f"SYSTEM Connected to {target}. Use MSG <text>.")
                    send_line(target_conn, f"SYSTEM {name} connected to you. Use MSG <text>.")

                elif line.startswith("MSG "):
                    text = line[4:]
                    with lock:
                        partner = partners.get(name)
                        partner_conn = clients.get(partner) if partner else None
                    if not partner_conn:
                        send_line(conn, "SYSTEM You are not in a chat. Use CHAT <name>.")
                        continue
                    send_line(partner_conn, f"CHAT {name}: {text}")

                elif line == "QUIT":
                    with lock:
                        partner = partners.pop(name, None)
                        if partner:
                            partners.pop(partner, None)
                            partner_conn = clients.get(partner)
                        else:
                            partner_conn = None
                    if partner_conn:
                        send_line(partner_conn, "SYSTEM Other side left the chat.")
                    send_line(conn, "SYSTEM You left the chat.")
                    # stay connected in lobby
                    broadcast_users()

                else:
                    send_line(conn, "SYSTEM Unknown command. Use: LIST / CHAT <name> / MSG <text> / QUIT")

    except Exception as e:
        # print("Server error:", e)
        pass
    finally:
        if name:
            disconnect(name, "Connection closed.")
        else:
            try:
                conn.close()
            except:
                pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 5000))
    s.listen(50)
    print("Server listening on 5000...")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
