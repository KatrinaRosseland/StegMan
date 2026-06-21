import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
import threading
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import os
import sys
import socket
from PIL import Image
import io

# ==========================================
# 1. CORE COVERT CHANNEL LOGIC & CERT BUILDER
# ==========================================

def get_asset_path(relative_path):
    """ Helper to locate embedded assets when compiled via PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ensure_certificates_exist():
    """ Automatically generates key.pem and cert.pem if they are missing """
    if not os.path.exists("key.pem") or not os.path.exists("cert.pem"):
        print("[*] Security certificates missing. Generating fresh keys locally...")
        try:
            # Dynamically handle cryptography dependency for standalone runtimes
            try:
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization
            except ImportError:
                print("[*] Installing required cryptography library...")
                os.system("python -m pip install cryptography")
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization
            
            from datetime import datetime, timedelta
            
            # Generate Private Key
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            
            # Configure Certificate Details for Local Host Testing
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
            ])
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow() - timedelta(days=1)
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).sign(key, hashes.SHA256())
            
            # Save Private Key
            with open("key.pem", "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save Public Certificate
            with open("cert.pem", "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
                
            print("[+] Dynamic keypair generation completed successfully.")
        except Exception as e:
            print(f"[!] Critical Error generating runtime certificate: {e}")

# ==========================================
# 2. SERVER ENDPOINT & ENGINE
# ==========================================

class CovertHTTPSRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def decode_char_from_bytes(self, img_bytes):
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            pixels = img.load()
            bin_str = ""
            for i in range(8):
                r, g, b = pixels[i, 0]
                bin_str += str(r & 1)
            return chr(int(bin_str, 2))
        except Exception as e:
            return f"[Decoding Error: {e}]"

    def do_POST(self):
        if self.path == "/upload/profile_picture":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                start_idx = post_data.find(b'\x89PNG')
                if start_idx != -1:
                    image_bytes = post_data[start_idx:]
                    end_boundary_idx = image_bytes.find(b'\r\n----WebKitFormBoundary')
                    if end_boundary_idx != -1:
                        image_bytes = image_bytes[:end_boundary_idx]
                    
                    secret_char = self.decode_char_from_bytes(image_bytes)
                    print(f"[+] SUCCESS -> Extracted Guess: '{secret_char}'")
            except Exception as e:
                print(f"[!] Parsing error on incoming POST: {e}")
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"success"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_covert_server(port, target_bind):
    # Enforce certificate availability dynamically on startup
    ensure_certificates_exist()
    
    HTTPServer.address_family = socket.AF_INET
    if target_bind == "127.0.0.1":
        server_address = ("localhost", port)
    else:
        server_address = (target_bind, port)
        
    httpd = HTTPServer(server_address, CovertHTTPSRequestHandler)
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"\n[*] Secure HTTPS Listener active on {server_address}:{port} (TLS Enabled).")
    print("[*] Waiting for incoming client game connections...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down HTTPS server.")
# ==========================================
# 3. GAME CLIENT INTERFACE (GUI)
# ==========================================

class ModernCovertHangmanGUI:
    def __init__(self, root, target_host, target_port):
        self.root = root
        self.root.title("Project Hang-Bit: Covert Client")
        self.root.geometry("650x550")
        self.root.configure(bg="#f4f6f9")
        
        self.word_pool = ["PROJECT", "CIPHER", "COVERT", "NETWORK", "CHANNEL"]
        self.word_index = 0
        self.word = self.word_pool[self.word_index]
        self.guessed_letters = set()
        self.attempts_left = 6
        
        self.server_host = target_host
        self.server_port = int(target_port)
        self.carrier_path = get_asset_path('carrier.png')
        self.covert_path = 'covert.png'
        
        self.setup_fonts()
        self.setup_ui()
        
    def setup_fonts(self):
        self.title_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.word_font = tkfont.Font(family="Courier", size=26, weight="bold")
        self.status_font = tkfont.Font(family="Helvetica", size=12, slant="italic")
        self.btn_font = tkfont.Font(family="Helvetica", size=11, weight="bold")

    def setup_ui(self):
        self.top_panel = tk.Frame(self.root, bg="#ffffff", bd=1, relief="groove")
        self.top_panel.pack(fill="x", padx=15, pady=15)
        
        display_host = "localhost" if self.server_host == "127.0.0.1" else self.server_host
        self.status_label = tk.Label(
            self.top_panel, 
            text=f"Target Node: HTTPS://{display_host}:{self.server_port}", 
            font=self.status_font, bg="#ffffff", fg="#4a5568"
        )
        self.status_label.pack(anchor="w", padx=15, pady=8)
        
        self.attempts_label = tk.Label(
            self.top_panel, 
            text=f"Hearts Remaining: {self.attempts_left}", 
            font=self.title_font, bg="#ffffff", fg="#e53e3e"
        )
        self.attempts_label.pack(anchor="w", padx=15, pady=2)
        
        self.display_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.display_frame.pack(fill="x", pady=20)
        
        self.word_label = tk.Label(
            self.display_frame, 
            text=self.get_display_word(), 
            font=self.word_font, bg="#f4f6f9", fg="#1a202c"
        )
        self.word_label.pack(pady=10)
        
        self.keyboard_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.keyboard_frame.pack(pady=5)
        
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.buttons = {}
        for index, letter in enumerate(alphabet):
            row = index // 7
            col = index % 7
            btn = tk.Button(
                self.keyboard_frame, text=letter, width=6, height=2, font=self.btn_font,
                bg="#ffffff", fg="#2d3748", activebackground="#edf2f7",
                relief="flat", bd=1, highlightthickness=1,
                command=lambda l=letter: self.handle_guess(l)
            )
            btn.grid(row=row, column=col, padx=4, pady=4)
            self.buttons[letter] = btn
            
        self.control_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.control_frame.pack(fill="x", side="bottom", pady=20)
        
        self.restart_btn = tk.Button(
            self.control_frame, text="🔄 Restart Game Session", width=22, height=2,
            font=self.title_font, bg="#3182ce", fg="#ffffff", activebackground="#2b6cb0",
            relief="flat", cursor="hand2", command=self.reset_game
        )
        self.restart_btn.pack(anchor="center")

    def get_display_word(self):
        return " ".join([letter if letter in self.guessed_letters else "_" for letter in self.word])

    def handle_guess(self, letter):
        self.buttons[letter].config(bg="#ebf8ff", fg="#2b6cb0") 
        self.guessed_letters.add(letter)
        
        threading.Thread(target=self.covert_https_transmit, args=(letter,), daemon=True).start()
        
        if letter in self.word:
            self.word_label.config(text=self.get_display_word())
            if all(l in self.guessed_letters for l in self.word):
                self.status_label.config(text="Game Completed! Payload sent securely.", fg="#38a169")
                self.disable_all_buttons()
        else:
            self.attempts_left -= 1
            self.attempts_label.config(text=f"Hearts Remaining: {self.attempts_left}")
            if self.attempts_left <= 0:
                self.status_label.config(text=f"Out of moves! Solution: {self.word}", fg="#e53e3e")
                self.disable_all_buttons()

    def disable_all_buttons(self):
        for btn in self.buttons.values():
            btn.config(state="disabled", bg="#e2e8f0", fg="#a0aec0")

    def reset_game(self):
        self.word_index = (self.word_index + 1) % len(self.word_pool)
        self.word = self.word_pool[self.word_index]
        self.guessed_letters.clear()
        self.attempts_left = 6
        
        display_host = "localhost" if self.server_host == "127.0.0.1" else self.server_host
        self.status_label.config(text=f"Target Node: HTTPS://{display_host}:{self.server_port}", fg="#4a5568")
        self.attempts_label.config(text=f"Hearts Remaining: {self.attempts_left}")
        self.word_label.config(text=self.get_display_word())
        
        for letter, btn in self.buttons.items():
            btn.config(state="normal", bg="#ffffff", fg="#2d3748")

    def covert_https_transmit(self, letter):
        try:
            bin_char = format(ord(letter), '08b')
            img = Image.open(self.carrier_path).convert('RGB')
            pixels = img.load()
            
            for i in range(8):
                r, g, b = pixels[i, 0]
                new_r = (r & ~1) | int(bin_char[i])
                pixels[i, 0] = (new_r, g, b)
            img.save(self.covert_path)
            
            with open(self.covert_path, 'rb') as f:
                img_bytes = f.read()
                
            boundary = '----WebKitFormBoundaryCovertChannel'
            newline = b'\r\n'
            payload = [
                f'--{boundary}'.encode(),
                b'Content-Disposition: form-data; name="avatar"; filename="covert.png"',
                b'Content-Type: image/png',
                b'',
                img_bytes,
                f'--{boundary}--'.encode(),
                b''
            ]
            body = newline.join(payload)
            headers = {
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body)),
                'User-Agent': 'Mozilla/5.0'
            }
            
            context = ssl._create_unverified_context()
            connection_target = "localhost" if self.server_host == "127.0.0.1" else self.server_host
            
            conn = http.client.HTTPSConnection(connection_target, self.server_port, context=context, timeout=4)
            conn.request("POST", "/upload/profile_picture", body, headers)
            response = conn.getresponse()
            response.read()
            conn.close()
        except Exception as e:
            print(f"[-] Broadcast alert: Server offline. ({e})")
# ==========================================
# 4. PRIMARY LAUNCHER MENU
# ==========================================

class ChannelLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Hang-Bit Launcher")
        self.root.geometry("480x380")
        self.root.configure(bg="#ffffff")
        
        self.title_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.label_font = tkfont.Font(family="Helvetica", size=10)
        
        tk.Label(self.root, text="Select Operational Mode", font=self.title_font, bg="#ffffff", fg="#1a202c").pack(pady=15)
        
        self.btn_frame = tk.Frame(self.root, bg="#ffffff")
        self.btn_frame.pack(pady=10)
        
        self.client_btn = tk.Button(self.btn_frame, text="Run as Client Game", width=18, height=2, bg="#3182ce", fg="#ffffff", font=self.label_font, command=self.show_client_config)
        self.client_btn.grid(row=0, column=0, padx=10)
        
        self.server_btn = tk.Button(self.btn_frame, text="Run as Listening Server", width=18, height=2, bg="#4a5568", fg="#ffffff", font=self.label_font, command=self.show_server_config)
        self.server_btn.grid(row=0, column=1, padx=10)
        
        self.config_frame = tk.Frame(self.root, bg="#ffffff")
        self.config_frame.pack(pady=15, fill="x", padx=20)

    def show_client_config(self):
        for widget in self.config_frame.winfo_children():
            widget.destroy()
            
        self.test_mode = tk.StringVar(value="local")
        
        radio_frame = tk.Frame(self.config_frame, bg="#ffffff")
        radio_frame.pack(anchor="w", pady=5)
        
        tk.Radiobutton(radio_frame, text="Localhost Sandbox Testing", variable=self.test_mode, value="local", bg="#ffffff", font=self.label_font, command=self.update_client_inputs).grid(row=0, column=0, padx=10)
        tk.Radiobutton(radio_frame, text="Remote Server Deployment", variable=self.test_mode, value="remote", bg="#ffffff", font=self.label_font, command=self.update_client_inputs).grid(row=0, column=1)
        
        self.addr_label = tk.Label(self.config_frame, text="Target Connection Address:", bg="#ffffff", font=self.label_font)
        self.addr_label.pack(anchor="w", pady=(10, 0))
        
        self.host_entry = tk.Entry(self.config_frame, font=self.label_font, bd=1, relief="solid")
        self.host_entry.pack(fill="x", pady=4)
        
        tk.Label(self.config_frame, text="Target Port Connection:", bg="#ffffff", font=self.label_font).pack(anchor="w")
        self.port_entry = tk.Entry(self.config_frame, font=self.label_font, bd=1, relief="solid")
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(fill="x", pady=4)
        
        self.update_client_inputs()
        
        tk.Button(self.config_frame, text="🚀 Launch Covert Game Panel", bg="#38a169", fg="#ffffff", font=self.label_font, command=self.start_client).pack(pady=15)

    def update_client_inputs(self):
        self.host_entry.delete(0, tk.END)
        if self.test_mode.get() == "local":
            self.host_entry.insert(0, "127.0.0.1")
            self.host_entry.config(state="disabled")
        else:
            self.host_entry.insert(0, "")
            self.host_entry.config(state="normal")

    def show_server_config(self):
        for widget in self.config_frame.winfo_children():
            widget.destroy()
            
        self.test_mode = tk.StringVar(value="local")
        
        radio_frame = tk.Frame(self.config_frame, bg="#ffffff")
        radio_frame.pack(anchor="w", pady=5)
        
        tk.Radiobutton(radio_frame, text="Localhost Mode (127.0.0.1)", variable=self.test_mode, value="local", bg="#ffffff", font=self.label_font).grid(row=0, column=0, padx=10)
        tk.Radiobutton(radio_frame, text="Remote Listen (0.0.0.0)", variable=self.test_mode, value="remote", bg="#ffffff", font=self.label_font).grid(row=0, column=1)
        
        tk.Label(self.config_frame, text="Configure Local Port To Open:", bg="#ffffff", font=self.label_font).pack(anchor="w", pady=(10, 0))
        self.port_entry = tk.Entry(self.config_frame, font=self.label_font, bd=1, relief="solid")
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(fill="x", pady=4)
        
        tk.Button(self.config_frame, text="🛡️ Initialize Encryption Port", bg="#e53e3e", fg="#ffffff", font=self.label_font, command=self.start_server).pack(pady=15)

    def start_client(self):
        self.host_entry.config(state="normal")
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not host or not port:
            messagebox.showerror("Validation Error", "All parameter fields are required.")
            if self.test_mode.get() == "local":
                self.host_entry.config(state="disabled")
            return
            
        for widget in self.root.winfo_children():
            widget.destroy()
        ModernCovertHangmanGUI(self.root, host, port)

    def start_server(self):
        port_str = self.port_entry.get().strip()
        if not port_str:
            return
            
        port = int(port_str)
        bind_ip = "127.0.0.1" if self.test_mode.get() == "local" else "0.0.0.0"
        
        messagebox.showinfo(
            "Server Routing Instructions",
            f"Server configured for {self.test_mode.get().upper()} testing.\n\n"
            f"1. Binding targeting address: {bind_ip}\n"
            f"2. Core encryption files 'cert.pem' and 'key.pem' will auto-generate if missing.\n\n"
            f"Click OK to shift context over to the background socket listener."
        )
        
        self.root.destroy()
        run_covert_server(port, bind_ip)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChannelLauncher(root)
    root.mainloop()
