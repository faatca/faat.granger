import asyncio
import argparse
import os
from faat.granger import MessageApp, Router
import logging

log = logging.getLogger(__name__)
routes = Router()


async def main():
    parser = argparse.ArgumentParser(description="Processes commands from message queue")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--mode", choices=["relaxed", "existing", "tenacious"], default="tenacious"
    )
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("exchange")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    logging.getLogger("pika").setLevel(logging.WARNING)

    app = MessageApp(
        url=os.environ["AMQP_URL"],
        router=routes,
        name=args.exchange,
        mode=args.mode,
        worker_count=args.workers,
    )
    await app.serve()


@routes.route("/users/<id:int>/enroll")
async def enroll_user(request):
    user_id = request.path_params["id"]
    print(f"Enroll user: {user_id!r}")
    await asyncio.sleep(1)


@routes.route("/users/<id:int>/terminate")
async def terminate_user(request):
    user_id = request.path_params["id"]
    print(f"Terminate user: {user_id!r}")
    print(request.json())
    await asyncio.sleep(1)


@routes.default
async def default_route(request):
    print(request.path)
    print(request.body)
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
