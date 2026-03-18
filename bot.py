from telethon import TelegramClient
import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

bot_token = os.getenv("BOT_TOKEN")

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# 📤 SOURCE CHANNELS (add more anytime)
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

# 📥 YOUR CHANNEL
DEST_CHANNEL = -1003572048499


# 📂 Load already sent message IDs
def load_ids():
    try:
        with open("sent_ids.txt", "r") as f:
            return set(f.read().splitlines())
    except:
        return set()


# 💾 Save sent message IDs
def save_ids(ids):
    with open("sent_ids.txt", "w") as f:
        f.write("\n".join(ids))


# 🚀 MAIN FUNCTION
async def main():
    

    sent_ids = load_ids()
    new_ids = set(sent_ids)

    for channel in SOURCE_CHANNELS:
        try:
            messages = await client.get_messages(channel, limit=10)

            for msg in messages:
                if not msg.text:
                    continue

                msg_id = f"{channel}_{msg.id}"   # 🔥 unique per channel

                # ❌ Skip duplicates
                if msg_id in sent_ids:
                    continue

                text = msg.text.lower()

                # 🔥 Basic job filter
                if "job" in text or "hiring" in text or "vacancy" in text:
                    print("Sending:", msg.text[:50])

                    await client.send_message(DEST_CHANNEL, msg.text)

                    new_ids.add(msg_id)

        except Exception as e:
            print(f"Error in channel {channel}:", e)

    save_ids(new_ids)

    await client.disconnect()


# ▶️ RUN
with client:
    client.loop.run_until_complete(main())
