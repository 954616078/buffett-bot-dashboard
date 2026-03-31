"""Start a public ngrok tunnel for local dashboard."""

from __future__ import annotations

import time

from pyngrok import ngrok


def main() -> None:
    tunnel = ngrok.connect(8080, bind_tls=True)
    print(tunnel.public_url, flush=True)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        ngrok.kill()


if __name__ == "__main__":
    main()
