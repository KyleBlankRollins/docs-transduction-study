"""Loopback fake OpenAI-compatible provider that logs request bodies (no auth logged)."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = sys.argv[2]
REPLY = sys.argv[3] if len(sys.argv) > 3 else '{"ok": true}'


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        with open(LOG, "a") as fh:
            fh.write(json.dumps({"path": self.path, "body": json.loads(body)}) + "\n")
        req = json.loads(body)
        if not req.get("stream"):
            out = {
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": req["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": REPLY},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            }
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        chunks = [
            {
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": REPLY}}
                ]
            },
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            {
                "choices": [],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        ]
        for c in chunks:
            c.update(
                {
                    "id": "x",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": req["model"],
                }
            )
            self.wfile.write(f"data: {json.dumps(c)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
