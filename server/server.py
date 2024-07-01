import socket
import threading
import os

from pathlib import Path

class Connection:
    def __init__(self, sock : socket.SocketType, is_auth : bool) -> None:
        self.sock = sock
        self.auth = is_auth

def close_conn(sock : socket.SocketType):
    for conn in connections:
        if conn.sock == sock:
            connections.remove(conn)
            break

    sock.shutdown(1)
    sock.close()


def check_authfile(uname : str, pword : str):
    if not Path("./data/.authfile").exists():
        return False, "Cannot authenticate at the moment."

    with open("./data/.authfile", "r") as authfile:
        line = authfile.readline()
        
        while line: # Ignore newline char
            creds = line.replace("\n", "").split(":")
            if len(creds) != 2:
                continue # Malformed credentials

            elif creds[0] == uname and creds[1] == pword:
                return True, None
            
            line = authfile.readline()
        
        return False, "Invalid username or password."


def update_auth_status(sock : socket.SocketType, is_auth: bool):
    for conn in connections:
        if conn.sock == sock:
            conn.auth = is_auth
            return
        
    print(f"[!] Failed to update auth status of {conn.sock.getpeername()}")


def auth(conn : socket.SocketType, msg : bytes):
    # Auth Request Format: <AUTH>.username.password
    tokens = msg.decode("utf-8").replace("\n","").split(".")
    if len(tokens) != 3:
        conn.send(str.encode("<BAD>.Malformed auth string."))
        return

    authentic, res_msg = check_authfile(uname= tokens[1], pword= tokens[2])
    if authentic:
        update_auth_status(conn, True)
        conn.send(str.encode(f"<AUTH_OK>.{res_msg}"))
    else:
        conn.send(str.encode(f"<AUTH_BAD>.{res_msg}"))
    

def is_auth_req(msg : bytes):
    return msg.decode("utf-8").startswith("<AUTH>")

def is_auth_conn(sock : socket.SocketType):
    for conn in connections:
        if conn.sock == sock:
            return conn.auth

    return False

def forward(msg : bytes):
    count = 0
    for conn in connections:
        if is_auth_conn(conn.sock):
            conn.sock.send(msg)
            count += 1
    
    print(f"[+] Sent {len(msg)} bytes to {count}/{len(connections)} hosts.")


def recv_msgs(conn : socket.socket):
    while cont_to_listen:
        try:
            msg = conn.recv(1024)
            print(f"[i] New message from {conn.getpeername()}.")

            if is_auth_req(msg):
                auth(conn, msg)

            elif is_auth_conn(conn):
                forward(msg)
            else:
                conn.send(str.encode("Not authenticated."))

        except ConnectionResetError:
            close_conn(conn)


def listen(host : str, port :int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4, TCP
    sock.bind((host, port))
    sock.listen()
    print(f"[i] Listening on {host}:{port}.")

    max_conns = 5
    while cont_to_listen:
        new_conn, conn_info = sock.accept()
        print(f"[i] Connection from {conn_info[0]}:{conn_info[1]}")

        if len(connections) >= max_conns:
            new_conn.send("Channel is full. Try again later.")
            close_conn(new_conn)
            continue

        new_receiver = threading.Thread(target=recv_msgs, args=(new_conn,))
        new_receiver.start()

        connections.append(Connection(new_conn, False))

# ________________________________________________________________________________________________

rq_prefixes = ["<AUTH>"] # Request prefixes for parsing client messages
rp_prefixes = ["<AUTH_OK>", "<AUTH_BAD>"] # Response prefixes for client to parse server messages

connections = [] # Connection type elements
cont_to_listen = True # Updatable by thread listen for KeyboarInterrupt to end server

if __name__=="__main__":
    host = "0.0.0.0"
    port = 178

    try: 
        listen(host, port)
    except KeyboardInterrupt:
        exit()

# TODO: Messages like <AUTH>.akdald.adkalwd. will fail because of ending dot(.)