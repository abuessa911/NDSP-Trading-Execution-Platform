"""Explicit test-only JWKS fixture; not provider login, MFA or token revocation."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
jwk.update(kid="test-only", alg="RS256", use="sig")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"keys": [jwk]}).encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9090), Handler).serve_forever()