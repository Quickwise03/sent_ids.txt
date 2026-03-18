from telethon import TelegramClient
import os

# 🔐 Secrets
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

# 🤖 Create bot client
client = TelegramClient('bot', api_id, api_hash)

# 🚀 Start bot ONLY ONCE
client = client.start(bot_token=bot_token)


# 📤 SOURCE CHANNELS
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

# 📥 DESTINATION CHANNEL
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
    sent_ids = load_ids()
    new_ids = set(sent_ids)

    for channel in SOURCE_CHANNELS:
        try:
            messages = await client.get_messages(channel, limit=10)

            for msg in messages:
                if not msg.text:
                    continue

                msg_id = f"{channel}_{msg.id}"

                if msg_id in sent_ids:
                    continue

                text = msg.text.lower()

                if "job" in text or "hiring" in text or "vacancy" in text:
                    print("Sending:", msg.text[:50])
                    await client.send_message(DEST_CHANNEL, msg.text)
                    new_ids.add(msg_id)

        except Exception as e:
            print(f"Error in channel {channel}:", e)

    save_ids(new_ids)


with client:
    client.loop.run_until_complete(main())
