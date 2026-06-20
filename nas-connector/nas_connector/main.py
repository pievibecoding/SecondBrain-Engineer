import asyncio
import signal
import sys
from nas_connector.config import config
from nas_connector.uploader import Uploader
from nas_connector.watcher import poll_once
from nas_connector.logger import logger
import os


async def run():
    # Validate mount path
    mount = config.NAS_MOUNT_PATH
    if not os.path.exists(mount) or not os.access(mount, os.R_OK):
        logger.error("NAS mount path invalid or not readable", mount_path=mount)
        sys.exit(1)

    uploader = Uploader(config.BACKEND_API_URL)
    shutting_down = False

    loop = asyncio.get_event_loop()

    def _stop():
        nonlocal shutting_down
        shutting_down = True

    loop.add_signal_handler(signal.SIGTERM, _stop)
    loop.add_signal_handler(signal.SIGINT, _stop)

    while not shutting_down:
        await poll_once(config.NAS_MOUNT_PATH, uploader)
        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)

    logger.info("Shutting down nas-connector")


def main():
    asyncio.run(run())


if __name__ == '__main__':
    main()
