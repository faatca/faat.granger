import asyncio
import json
import logging
import aio_pika

log = logging.getLogger(__name__)


class MessageApp:
    def __init__(self, url, router, name, *, mode="tenacious", worker_count=10):
        self._url = url
        self._router = router
        self._name = name
        self._mode = mode
        self._prefetch_count = worker_count

    async def serve(self):
        connection, channel = await self._connect()
        queue_name = await self._initialize_schema(channel)
        await self._process_messages(channel, queue_name)

        try:
            # This doesn't feel ideal, but we want to wait while we're processing messages.
            while True:
                await asyncio.sleep(1)
        finally:
            await connection.close()

    async def _connect(self):
        log.debug("Connecting to broker")
        connection = await aio_pika.connect_robust(self._url)
        channel = await connection.channel()

        log.debug("Settings QOS")
        await channel.set_qos(prefetch_count=self._prefetch_count)
        return connection, channel

    async def _initialize_schema(self, channel):
        log.debug("Initializing exchanges, queues, and bindings")
        func = MODES.get(self._mode)
        if func:
            return await func(channel, self._name)
        if callable(self._mode):
            # Perhaps they passed in a schema initializing function of their own to use.
            return await self._mode(channel, self._name)
        raise ValueError(f"Unknown mode: {self._mode}")

    async def _process_messages(self, channel, queue_name):
        queue = await channel.get_queue(queue_name)

        async def process_message(message):
            async with message.process():
                log.debug(f"Processing message: {len(message.body)} bytes")
                path = message.properties.headers.get("PATH")
                if path is not None:
                    path = path.decode()
                handler, path_params = self._router.find_handler(path)
                request = Request(path, message.body, path_params)
                await handler(request)
                log.debug("Finished message")

        await queue.consume(process_message)


async def initialize_relaxed_schema(channel, name):
    exchange_name = name

    log.debug(f"Initializing exchange: {exchange_name}")
    exchange = await channel.declare_exchange(
        name=exchange_name, type=aio_pika.ExchangeType.FANOUT, durable=True
    )

    log.debug(f"Initializing queue")
    queue = await channel.declare_queue(queue="", exclusive=True, durable=True)
    queue_name = queue.name
    log.debug(f"Made consumer queue: {queue_name}")

    log.debug("Binding queue")
    queue.bind(exchange=exchange)
    return queue_name


async def initialize_tenacious_schema(channel, name):
    # If the message fails in the main queue, it's dead lettered into the retry queue.
    # After a couple minutes of waiting in the retry queue, the messages drop back into the main
    # exchange for processing.
    exchange_name = name
    retry_exchange_name = name + ".retry"
    queue_name = name + "_q"
    retry_queue_name = name + "_retry_q"

    log.debug(f"Initializing exchange: {exchange_name}")
    exchange = await channel.declare_exchange(
        name=exchange_name, type=aio_pika.ExchangeType.FANOUT, durable=True
    )

    log.debug(f"Initializing retry exchange: {retry_exchange_name}")
    retry_exchange = await channel.declare_exchange(
        name=retry_exchange_name, type=aio_pika.ExchangeType.FANOUT, durable=True
    )

    log.debug(f"Initializing queue: {queue_name}")
    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={"x-dead-letter-exchange": retry_exchange_name, "x-queue-mode": "lazy"},
    )

    log.debug(f"Initializing retry queue: {retry_queue_name}")
    retry_queue = await channel.declare_queue(
        retry_queue_name,
        durable=True,
        arguments={
            "x-queue-mode": "lazy",
            "x-dead-letter-exchange": exchange_name,
            "x-message-ttl": 2 * 60 * 1000,  # two minutes in milliseconds
        },
    )

    log.debug("Binding queue")
    await queue.bind(exchange=exchange)

    log.debug("Binding retry queue")
    await retry_queue.bind(exchange=retry_exchange)
    return queue_name


def initialize_existing_schema(channel, name):
    return name


MODES = {
    "relaxed": initialize_relaxed_schema,
    "tenacious": initialize_tenacious_schema,
    "existing": initialize_existing_schema,
}


class Request:
    def __init__(self, path, body, path_params):
        self.path = path
        self.body = body
        self.path_params = path_params
        self._json = UNASSIGNED

    def json(self):
        if self._json is UNASSIGNED:
            self._json = json.loads(self.body.decode())
        return self._json


UNASSIGNED = object()
