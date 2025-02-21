import http.server
import ssl
import socketserver
import os
from urllib.parse import parse_qs, urlparse

class TokenHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Create a simple HTML response
        html = """
        <html>
        <body>
            <h1>Authentication Complete</h1>
            <p>You can close this window and return to the application.</p>
            <script>
                window.close();
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

def run_https_server():
    # Generate self-signed certificate if it doesn't exist
    if not (os.path.exists('cert.pem') and os.path.exists('key.pem')):
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        # Write certificate and private key
        with open("cert.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open("key.pem", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

    # Create HTTPS server
    server_address = ('localhost', 8443)
    httpd = socketserver.TCPServer(server_address, TokenHandler)
    
    # Wrap socket with SSL
    httpd.socket = ssl.wrap_socket(
        httpd.socket,
        certfile='cert.pem',
        keyfile='key.pem',
        server_side=True
    )
    
    print(f"HTTPS Server running on https://localhost:8443")
    httpd.serve_forever()

if __name__ == '__main__':
    run_https_server()
