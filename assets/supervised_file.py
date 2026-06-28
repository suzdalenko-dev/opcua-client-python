import asyncio


async def supervised(factory, name):
    while True:
        try:
            await factory()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"{name} murio {e} error")
            await asyncio.sleep(22)
            