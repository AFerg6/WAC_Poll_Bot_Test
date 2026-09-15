import asyncio
import random
import re
import smtplib
import sqlite3
import time
import os
from email.message import EmailMessage
from email.utils import formataddr
 
import discord
from discord import app_commands
from discord.ext import commands
 
from config import TOKEN
from dotenv import load_dotenv
 
load_dotenv()
 
 
def _getenv_int(name: str):
    v = os.getenv(name)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None
 
 
# SMTP / role configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Grey Western Anime")
 
UNVERIFIED_ROLE_ID = _getenv_int("UNVERIFIED_ROLE_ID")
VERIFIED_ROLE_ID = _getenv_int("VERIFIED_ROLE_ID")
 
intents = discord.Intents.default()
intents.members = True
 
bot = commands.Bot(command_prefix="!", intents=intents)
 
DB_PATH = "identity_verification.db"
CODE_LENGTH = 6
# 30 minutes valid code
CODE_TTL_SECONDS = 30 * 60
# Minimum time is 1 min
CODE_RESEND_COOLDOWN_SECONDS = 60
UWO_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@uwo\.ca$")
 
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
 
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS verified_users (
        user_id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        created_at INTEGER NOT NULL
    )
    """
)
 
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS pending_verifications (
        user_id INTEGER PRIMARY KEY,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )
    """
)
 
conn.commit()
 
 
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()
 
 
def is_valid_uwo_email(email: str) -> bool:
    return bool(UWO_EMAIL_PATTERN.fullmatch(normalize_email(email)))
 
 
def create_code() -> str:
    return str(random.randint(10 ** (CODE_LENGTH - 1), (10 ** CODE_LENGTH) - 1))
 
 
def email_already_used(email: str) -> bool:
    normalized = normalize_email(email)
    cursor.execute("SELECT 1 FROM verified_users WHERE email = ?", (normalized,))
    return cursor.fetchone() is not None
 
 
def is_user_already_verified(user_id: int) -> bool:
    cursor.execute("SELECT email FROM verified_users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None
 
 
def purge_expired_codes() -> None:
    now = int(time.time())
    cursor.execute(
        "DELETE FROM pending_verifications WHERE ? - created_at > ?",
        (now, CODE_TTL_SECONDS),
    )
    conn.commit()
 
 
async def assign_unverified_role(member: discord.Member) -> None:
    if UNVERIFIED_ROLE_ID is None:
        return
    guild = member.guild
    role = guild.get_role(UNVERIFIED_ROLE_ID)
    if role:
        await member.add_roles(role, reason="Member is awaiting identity verification")
 
 
def build_verification_email(code: str) -> tuple[str, str]:
    """Returns (plain_text_body, html_body) -- matches test_email.py exactly."""
    plain_text = (
        f"{code} is your WAC Verification code\n\n"
        "Here is your verification code:\n"
        f"{code}\n\n"
        f"Use /verify {code} to link your uwo email to your discord!\n\n"
        f"This code expires in {CODE_TTL_SECONDS // 60} minutes."
    )
 
    html = f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0; padding:0; background-color:#f4f4f7; font-family: Arial, Helvetica, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7; padding:40px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; padding:40px; text-align:center; border:10px solid #DCA1FF;">
            <tr>
              <td style="font-size:18px; font-weight:bold; color:#111111; padding-bottom:16px;">
                Verification code from Grey
              </td>
            </tr>
            <tr>
              <td style="font-size:15px; color:#444444; padding-bottom:20px;">
                Here is your verification code:
              </td>
            </tr>
            <tr>
              <td style="font-size:40px; font-weight:bold; letter-spacing:8px; color:#111111; padding-bottom:24px;">
                {code}
              </td>
            </tr>
            <tr>
              <td style="font-size:15px; color:#444444; padding-bottom:16px;">
                Use <strong>/verify {code}</strong> to link your uwo email to your discord!
              </td>
            </tr>
            <tr>
              <td style="font-size:12px; color:#999999;">
                This code expires in {CODE_TTL_SECONDS // 60} minutes.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return plain_text, html
 
 
def send_verification_email(email: str, code: str) -> None:
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise RuntimeError(
            "SMTP settings are missing. Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM to your .env file."
        )
 
    plain_text, html = build_verification_email(code)
 
    message = EmailMessage()
    message["Subject"] = f"{code} is your WAC Verification code"
    message["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM))
    message["To"] = email
    message.set_content(plain_text)
    message.add_alternative(html, subtype="html")
 
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT or 465) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
 
 
async def start_verification(member: discord.Member, email: str) -> str:
    """Attempts to send a verification code. Returns a message describing the result."""
    purge_expired_codes()
    normalized_email = normalize_email(email)
    now = int(time.time())
 
    existing_email = is_user_already_verified(member.id)
    if existing_email:
        return f"You are already verified with {existing_email}. Contact a server admin if you need to change your email."
 
    if not is_valid_uwo_email(normalized_email):
        return "Please use a valid @uwo.ca email address."
 
    if email_already_used(normalized_email):
        return "This @uwo.ca email has already been used to verify another account. Please contact the server admin."
 
    cursor.execute(
        "SELECT created_at FROM pending_verifications WHERE user_id = ?",
        (member.id,),
    )
    pending_row = cursor.fetchone()
    if pending_row is not None:
        seconds_since_last = now - pending_row[0]
        if seconds_since_last < CODE_RESEND_COOLDOWN_SECONDS:
            wait_seconds = CODE_RESEND_COOLDOWN_SECONDS - seconds_since_last
            return f"Please wait {wait_seconds} more second(s) before requesting another code."
 
    code = create_code()
 
    cursor.execute(
        """
        INSERT INTO pending_verifications (user_id, email, code, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            email = excluded.email,
            code = excluded.code,
            created_at = excluded.created_at
        """,
        (member.id, normalized_email, code, now),
    )
    conn.commit()
 
    try:
        await asyncio.to_thread(send_verification_email, normalized_email, code)
    except Exception as exc:
        cursor.execute("DELETE FROM pending_verifications WHERE user_id = ?", (member.id,))
        conn.commit()
        return f"I could not send the verification email. Please contact the server admin. Error: {exc}"
 
    return f"A verification code has been sent to {normalized_email}. Run `/verify` again with that code to finish."
 
 
async def complete_verification(member: discord.Member, submission: str) -> str:
    """Attempts to confirm a verification code. Returns a message describing the result."""
    purge_expired_codes()
    code = (submission or "").strip()
 
    cursor.execute(
        "SELECT email, code FROM pending_verifications WHERE user_id = ?",
        (member.id,),
    )
    row = cursor.fetchone()
 
    if row is None:
        return "You do not have a verification code pending. Run `/verify` with your @uwo.ca email first."
 
    stored_email, stored_code = row
    if code != stored_code:
        return "That code is incorrect or has expired. Please double-check it, or run `/verify` with your email again for a new code."
 
    try:
        cursor.execute(
            "INSERT INTO verified_users (user_id, email, created_at) VALUES (?, ?, ?)",
            (member.id, stored_email, int(time.time())),
        )
    except sqlite3.IntegrityError:
        conn.rollback()
        cursor.execute("DELETE FROM pending_verifications WHERE user_id = ?", (member.id,))
        conn.commit()
        return "This @uwo.ca email has already been used to verify another account. Please contact the server admin."
 
    cursor.execute("DELETE FROM pending_verifications WHERE user_id = ?", (member.id,))
    conn.commit()
 
    if VERIFIED_ROLE_ID is not None:
        guild = member.guild
        role = guild.get_role(VERIFIED_ROLE_ID)
        if role:
            await member.add_roles(role, reason="Member passed identity verification")
 
    if UNVERIFIED_ROLE_ID is not None:
        guild = member.guild
        role = guild.get_role(UNVERIFIED_ROLE_ID)
        if role and role in member.roles:
            await member.remove_roles(role, reason="Member passed identity verification")
 
    return f"Verification complete. You can now access the server with {stored_email}."
 
 
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f"Identity verification bot online: {bot.user}")
 
 
@bot.event
async def on_member_join(member: discord.Member):
    await assign_unverified_role(member)
 
 
@bot.tree.command(name="verify", description="Verify your @uwo.ca email, or submit the code you were emailed.")
@app_commands.describe(email_or_code="Your @uwo.ca email address, or the 6-digit code you received")
async def slash_verify(interaction: discord.Interaction, email_or_code: str):
    await interaction.response.defer(ephemeral=True)
    purge_expired_codes()
 
    text = (email_or_code or "").strip()
    if re.fullmatch(r"\d{6}", text):
        result = await complete_verification(interaction.user, text)
    else:
        result = await start_verification(interaction.user, text)
 
    await interaction.followup.send(result, ephemeral=True)
 
 
if __name__ == "__main__":
    bot.run(TOKEN)