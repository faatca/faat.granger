faat.granger package
====================

This package simplifies the effort required to set up a worker process around RabbitMQ.

This package is compatible with the [faat.corbin](https://github.com/faatca/faat.corbin) framework, except this package runs under asyncio.

It takes a platform independent, but opinionated approach to working with RabbitMQ.
Taking inspiration from modern web frameworks,
it simplifies the development of a worker applications to process messages.


## Installation ##

Install it with your favourite python package installer.

```cmd
py -m venv venv
venv\Scripts\pip install faat.granger
```

## Getting Started ##

The following example provides a basic look at how this framework can be used.

```python
import argparse
import asyncio
import logging
import os
from faat.granger import MessageApp, Router

log = logging.getLogger(__name__)
routes = Router()


async def main():
    parser = argparse.ArgumentParser(description="Render letters for a message queue")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )

    app = MessageApp(
        url=os.environ["AMQP_URL"],
        router=routes,
        name="greetings",
        mode="tenacious",
        worker_count=10,
    )
    asyncio.run(app.serve())


@routes.route("/reports/welcome-letter/<name>")
async def welcome_letter(request):
    name = request.path_params["name"]
    content = f"Hi {name}! Welcome."
    print(content)
    await asyncio.sleep(1)


@routes.route("/reports/dismissal/<id:int>")
async def terminate_user(request):
    letter_id = request.path_params["id"]
    data = request.json()
    print(f"-- Letter {letter_id} --")
    print(f"Hi {data['name']}. We are {data['emotion']} to see you go.")
    await asyncio.sleep(1)


@routes.default
async def default_route(request):
    log.warning(f"Unrecognized letter request: {request.path} - {request.body}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    main()
```

Post messages to the exchange however, you like.
However, the `PATH` variable should be included as a header on the posted message.

```python
import argparse
import asyncio
import logging
import os
import sys
import aio_pika

log = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Publish a messages for processing")
    parser.add_argument("-v", "--verbose", action="store_true")
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

    log.info("Posting message")
    message = aio_pika.Message(body=body, headers={"PATH": args.path})
    await exchange.publish(message, routing_key='')

    log.info("Shutting down")
    await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
```
