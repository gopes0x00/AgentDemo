#!/usr/bin/env python3
"""
VULNERABLE WEB SERVER - FOR EDUCATIONAL AND SECURITY DEMONSTRATION ONLY
DO NOT USE IN PRODUCTION ENVIRONMENTS

This server deliberately contains a command injection vulnerability 
to demonstrate security issues. It only listens on the specified private IP.
"""

import http.server
import socketserver
import urllib.parse
import subprocess
import os
import sys
import logging

# Define the specific IP and port to bind to
BIND_IP = "0.0.0.0"  # Change this to your private IP
PORT = 8080

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class VulnerableHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Basic routing
        if parsed_url.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # Simple form for demonstration
            self.wfile.write(b"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Command Execution Demo</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #333; }
                    .form-container { background: #f9f9f9; padding: 20px; border-radius: 5px; max-width: 600px; }
                    input[type=text] { width: 80%; padding: 8px; margin: 10px 0; }
                    input[type=submit] { background: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
                    pre { background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }
                    .warning { color: red; font-weight: bold; }
                </style>
            </head>
            <body>
                <h1>Command Execution Demo</h1>
                <div class="warning">WARNING: This server is vulnerable to command injection!</div>
                <p>This is a demonstration of an insecure application for educational purposes.</p>
                
                <div class="form-container">
                    <h2>Ping a host</h2>
                    <form action="/ping" method="get">
                        <label for="host">Host to ping:</label><br>
                        <input type="text" id="host" name="host" value="127.0.0.1"><br>
                        <input type="submit" value="Ping Host">
                    </form>
                </div>
            </body>
            </html>
            """)
            
        elif parsed_url.path == "/ping":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # VULNERABLE CODE - Command injection vulnerability!
            # This deliberately allows command injection through the 'host' parameter
            if "host" in query_params:
                host = query_params["host"][0]
                
                # INTENTIONALLY VULNERABLE - DO NOT USE IN PRODUCTION
                # The vulnerability is that we directly use user input in a shell command
                try:
                    # DELIBERATELY INSECURE - This allows command injection
                    command = f"ping -c 1 {host}"
                    logging.info(f"Executing command: {command}")
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                    
                    response = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Ping Results</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            h1 {{ color: #333; }}
                            pre {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }}
                            .warning {{ color: red; font-weight: bold; }}
                        </style>
                    </head>
                    <body>
                        <h1>Ping Results</h1>
                        <div class="warning">WARNING: This server is vulnerable to command injection!</div>
                        <p>Executed command: {command}</p>
                        <pre>{output.decode('utf-8', errors='replace')}</pre>
                        <p><a href="/">Back to home</a></p>
                    </body>
                    </html>
                    """
                    self.wfile.write(response.encode())
                except subprocess.CalledProcessError as e:
                    error_message = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Error</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            h1 {{ color: #333; }}
                            pre {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }}
                            .error {{ color: red; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">Error Executing Command</h1>
                        <p>The command failed with exit code: {e.returncode}</p>
                        <pre>{e.output.decode('utf-8', errors='replace')}</pre>
                        <p><a href="/">Back to home</a></p>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_message.encode())
            else:
                self.wfile.write(b"No host specified")
        else:
            self.send_error(404, "Page not found")
    
    def log_message(self, format, *args):
        logging.info("%s - %s", self.client_address[0], format % args)

def main():
    try:
        # Ensure we're binding to the specific IP
        server = socketserver.TCPServer((BIND_IP, PORT), VulnerableHandler)
        
        print(f"[+] Starting vulnerable web server on {BIND_IP}:{PORT}")
        print("[!] WARNING: This server is DELIBERATELY VULNERABLE to command injection")
        print("[!] DO NOT use in production or expose to untrusted networks")
        print("[!] For educational and security testing purposes only")
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Server shutdown requested")
        server.server_close()
        print("[+] Server shutdown complete")
    except OSError as e:
        if e.errno == 99:  # Cannot assign requested address
            print(f"[!] ERROR: Cannot bind to IP {BIND_IP}. Make sure this IP is assigned to your system.")
            sys.exit(1)
        else:
            raise

if __name__ == "__main__":
    main()