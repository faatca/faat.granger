faat.granger package
====================

This package simplifies the effort required to set up a worker process around RabbitMQ.

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

The

```python
import asyncio
import argparse
import os
from faat.granger import MessageApp, Router
import logging

log = logging.getLogger(__name__)
routes = Router()


async def main():
    parser = argparse.ArgumentParser(description="Render letters for a message queue")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    logging.getLogger("pika").setLevel(logging.WARNING)

    app = MessageApp(
        url=os.environ["AMQP_URL"],
        router=routes,
        name="greetings",
        mode="tenacious",
        worker_count=10,
    )
    await app.serve()


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
    print(f"Hi {data['name']}. We are {data['emotion']} to see you go."
    await asyncio.sleep(1)


@routes.default
async def default_route(request):
    log.warn(f"Unrecognized letter request: {request.path} - {request.body}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
```
