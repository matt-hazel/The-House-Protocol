from house_protocol.alerts.discord import send_dm
from house_protocol.config import load_settings

s = load_settings()

send_dm(s.discord_user_id, s.discord_bot_token, "House Protocol test message")
print("sent")