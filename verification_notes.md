## Notes for current identity_verifiction.py
Just a few things that could be updated:

1. You could add the WAC logo to the email via formatting.
2. Maybe give the email more personality? I mean it looks sad ngl.

Up to you to design it further, I just made a basic verification email sort of design that would fit WAC


## How to actually set up variables needed in .env
Also a few notes on how to actually set up ```identity_verificiation.py``` designed by yours truly mister lindorlukio

Your .env should to include:
```
# SMTP Variables
SMTP_HOST= (What will be used like Google or personal website)
SMTP_PORT= (STMP PORT)
SMTP_USERNAME= (EMAIL)
SMTP_PASSWORD= (HOST APP PASSWORD in "")
SMTP_FROM= (EMAIL) again...
SMTP_FROM_NAME= (EMAIL DISPLAY NAME in "")

# Discord settings role / channel IDs
UNVERIFIED_ROLE_ID= (Discord role ID for unverified users)
VERIFIED_ROLE_ID= (Discord role ID for verified users)
VERIFICATION_CHANNEL_ID= (Verification channel for the bot to read)
```