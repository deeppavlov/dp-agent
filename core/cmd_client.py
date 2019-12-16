from aioconsole import ainput


async def run_cmd(register_msg):
    user_id = await ainput('Provide user id: ')
    while True:
        msg = await ainput(f'You ({user_id}): ')
        msg = msg.strip()
        if msg:
            response = await register_msg(utterance=msg, user_telegram_id=user_id, user_device_type='cmd',
                                          location='lab', channel_type='cmd_client',
                                          deadline_timestamp=None, require_response=True)
            print('Bot: ', response['dialog'].utterances[-1].text)
