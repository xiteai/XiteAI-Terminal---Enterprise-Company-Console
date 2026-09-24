"""Start XiteAI Terminal once: python run.py (then open http://127.0.0.1:8710).

This is the plain server, for hosting it online (DEPLOY.md). On your own PC you
don't need it: dev.py keeps http://localhost:8710 running with the newest code.

Before binding: rebuild the UI if its source changed, and replace any older
copy of this server still holding the port (see server/bootstrap/freshness.py).
"""
from server.bootstrap import freshness, serving
from server.core import config

if __name__ == "__main__":
    url = f"http://{config.HOST}:{config.PORT}"
    print(f"UI: {freshness.ensure_ui()}")
    state = freshness.take_over(url, config.PORT)
    if state == "live":
        print(f"dev.py is already serving the newest code at {url}/console. Nothing to start.")
    elif state == "same":
        print(f"This version is already running at {url}")
    else:
        if state == "replaced":
            print("Stopped an older copy of the server that was still running.")
        print(f"Serving at {url}")
        serving.serve(serving.listen(config.HOST, config.PORT))
