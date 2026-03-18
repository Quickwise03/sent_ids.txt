from telethon import TelegramClient
import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

client = TelegramClient('session', api_id, api_hash)

SOURCE_CHANNELS = [
    -1001160330973,
    -1001256565029,
    -1001603220106,
    -1002594747501,
    -1001286809069,
    -1002049500142,
    -1001538889184,
    -1001433351995
]

DEST_CHANNEL = -1003572048499

def load_ids():
    try:
        with open("sent_ids.txt", "r") as f:
            return set(f.read().splitlines())
    except:
        return set()

def save_ids(ids):
    with open("sent_ids.txt", "w") as f:
        f.write("\n".join(ids))

async def main():
    await client.start()

    sent_ids = load_ids()
    new_ids = set(sent_ids)

    for channel in SOURCE_CHANNELS:
    messages = await client.get_messages(channel, limit=10)

    for msg in messages:
        if not msg.text:
            continue

        msg_id = str(msg.id)

        if msg_id in sent_ids:
            continue

        if "job" in msg.text.lower():
            await client.send_message(DEST_CHANNEL, msg.text)
            new_ids.add(msg_id)

    for msg in messages:
        if not msg.text:
            continue

        msg_id = str(msg.id)

        if msg_id in sent_ids:
            continue

        if "job" in msg.text.lower():
            await client.send_message(DEST_CHANNEL, msg.text)
            new_ids.add(msg_id)

    save_ids(new_ids)

    await client.disconnect()

with client:
    client.loop.run_until_complete(main())
