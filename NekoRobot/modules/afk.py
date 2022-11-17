import html
import random
import time

from typing import Optional
from datetime import datetime
import humanize
from telegram import MessageEntity, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters, MessageHandler, run_async

from NekoRobot import dispatcher
from NekoRobot.modules.disable import (
    DisableAbleCommandHandler,
    DisableAbleMessageHandler,
)
from NekoRobot.modules.sql import afk_sql as sql
from NekoRobot.modules.users import get_user_id
from NekoRobot import REDIS
from telegram import Message, User
from NekoRobot.modules.helper_funcs.readable_time import get_readable_time
from NekoRobot.modules.helper_funcs.alternate import send_message


def is_user_afk(userid):
    rget = REDIS.get(f'is_afk_{userid}')
    return bool(rget)


def start_afk(userid, reason):
    REDIS.set(f'is_afk_{userid}', reason)
    
def afk_reason(userid):
    return strb(REDIS.get(f'is_afk_{userid}'))

def end_afk(userid):
    REDIS.delete(f'is_afk_{userid}')
    return True

# Helpers
def strb(redis_string):
    return str(redis_string)

AFK_GROUP = 7
AFK_REPLY_GROUP = 8

@run_async
def afk(update, context):
    args = update.effective_message.text.split(None, 1)
    user = update.effective_user
    if not user:  # ignore channels
        return

    if user.id == 777000:
        return
    start_afk_time = time.time()
    reason = args[1] if len(args) >= 2 else "none"
    start_afk(update.effective_user.id, reason)
    REDIS.set(f'afk_time_{update.effective_user.id}', start_afk_time)
    fname = update.effective_user.first_name
    try:
        update.effective_message.reply_text(
            "{} Is Nᴏᴡ Aᴡᴀʏ!".format(fname))
    except BadRequest:
        pass

@run_async
def no_longer_afk(update, context):
    user = update.effective_user
    message = update.effective_message
    if not user:  # ignore channels
        return

    if not is_user_afk(user.id):  #Check if user is afk or not
        return
    end_afk_time = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user.id}'))))
    REDIS.delete(f'afk_time_{user.id}')
    res = end_afk(user.id)
    if res:
        if message.new_chat_members:  # dont say msg
            return
        firstname = update.effective_user.first_name
        try:
            options = [
                "The Dead {} is here! Time Taken: {}",
                "Hey {}! Why weren't you online for {}?",
                "{} is back online!! Time Taken: {}",
                "OwO, Welcome back {} You've Missing Till {} ",
                "OwO, Welcome back {}, you left us for {} ",
            ]
            chosen_option = random.choice(options)
            update.effective_message.reply_text(
                chosen_option.format(firstname, end_afk_time),
            )
        except BaseException:
            pass
            


@run_async
def reply_afk(update, context):
    message = update.effective_message
    userc = update.effective_user
    userc_id = userc.id
    if message.entities and message.parse_entities(
        [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]):
        entities = message.parse_entities(
            [MessageEntity.TEXT_MENTION, MessageEntity.MENTION])

        chk_users = []
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name

                if user_id in chk_users:
                    return
                chk_users.append(user_id)

            elif ent.type == MessageEntity.MENTION:
                user_id = get_user_id(message.text[ent.offset:ent.offset +
                                                   ent.length])
                if not user_id:
                    # Should never happen, since for a user to become AFK they must have spoken. Maybe changed username?
                    return

                if user_id in chk_users:
                    return
                chk_users.append(user_id)

                try:
                    chat = context.bot.get_chat(user_id)
                except BadRequest:
                    print("Error: Could not fetch userid {} for AFK module".
                          format(user_id))
                    return
                fst_name = chat.first_name

            else:
                return

            check_afk(update, context, user_id, fst_name, userc_id)

    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        fst_name = message.reply_to_message.from_user.first_name
        check_afk(update, context, user_id, fst_name, userc_id)


def check_afk(update, context, user_id, fst_name, userc_id):
    if is_user_afk(user_id):
        reason = afk_reason(user_id)
        since_afk = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user_id}'))))
        if int(userc_id) == int(user_id):
            return
        if reason == "none":
            res = "{} is Dead!\nLast Liveliness: {} Ago.".format(fst_name, since_afk)
        else:
            res = "{} is afk!\nReason: {}\nLast seen: {} Ago.".format(fst_name, reason, since_afk)

        update.effective_message.reply_text(res)


def __user_info__(user_id):
    is_afk = is_user_afk(user_id)
    text = ""
    if is_afk:
        since_afk = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user_id}'))))
        text = "Tʜɪs ᴜsᴇʀ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴀғᴋ (ᴀᴡᴀʏ ғʀᴏᴍ ᴋᴇʏʙᴏᴀʀᴅ)."
        text += f"\nLᴀsᴛ Sᴇᴇɴ: {since_afk} Aɢᴏ."
       
    else:
        text = "Tʜɪs ᴜsᴇʀ ᴄᴜʀʀᴇɴᴛʟʏ ɪsɴ'ᴛ ᴀғᴋ (ɴᴏᴛ ᴀᴡᴀʏ ғʀᴏᴍ ᴋᴇʏʙᴏᴀʀᴅ)."
    return text

def __stats__():
    return f"• {len(REDIS.keys())} Total Keys in Redis Database."

def __gdpr__(user_id):
    end_afk(user_id)


AFK_HANDLER = DisableAbleCommandHandler("afk", afk)
AFK_REGEX_HANDLER = DisableAbleMessageHandler(
    Filters.regex(r"^(?i)brb(.*)$"), afk, friendly="afk"
)
NO_AFK_HANDLER = MessageHandler(Filters.all & Filters.group, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(Filters.all & Filters.group, reply_afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)

__mod_name__ = "Afk"

__help__ = """
   - /afk <ʀᴇᴀsᴏɴ>: ᴍᴀʀᴋ ʏᴏᴜʀsᴇʟғ ᴀs ᴀғᴋ.
   - brb <ʀᴇᴀsᴏɴ>: sᴀᴍᴇ ᴀs ᴛʜᴇ ᴀғᴋ ᴄᴏᴍᴍᴀɴᴅ, ʙᴜᴛ ɴᴏᴛ ᴀ ᴄᴏᴍᴍᴀɴᴅ.
   ᴡʜᴇɴ ᴍᴀʀᴋᴇᴅ ᴀs ᴀғᴋ, ᴀɴʏ ᴍᴇɴᴛɪᴏɴs ᴡɪʟʟ ʙᴇ ʀᴇᴘʟɪᴇᴅ ᴛᴏ ᴡɪᴛʜ ᴀ ᴍᴇssᴀɢᴇ sᴛᴀᴛɪɴɢ ᴛʜᴀᴛ ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ!
"""

__command_list__ = ["afk"]
__handlers__ = [
    (AFK_HANDLER, AFK_GROUP),
    (AFK_REGEX_HANDLER, AFK_GROUP),
    (NO_AFK_HANDLER, AFK_GROUP),
    (AFK_REPLY_HANDLER, AFK_REPLY_GROUP),
]
#------ishikki-akabane
