import asyncio
import argparse
import logging
import os
import sys
import aio_pika

log = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Processes commands from message queue")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("exchange")
    parser.add_argument("path")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )

    url = os.environ["AMQP_URL"]
    body = sys.stdin.read().encode()

    log.info("Connecting to broker")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    exchange = await channel.get_exchange(args.exchange)
    log.info("Preparing message")
    message = aio_pika.Message(body=body, headers={"PATH": args.path})

    log.info("Posting")
    for i in range(args.count):
        log.debug("Posting message")
        await exchange.publish(message, routing_key='')

    log.info("Shutting down")
    await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
