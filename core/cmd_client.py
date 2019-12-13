import asyncio

async def run_cmd(register_msg):
    user_id = input('Provide user id: ')
    while True:
        msg = input(f'You ({user_id}): ').strip()
        if msg:
            response = await register_msg(utterance=msg, user_telegram_id=user_id, user_device_type='cmd',
                                          location='lab', channel_type='cmd_client',
                                          deadline_timestamp=None, require_response=True)
            print('Bot: ', response['dialog'].utterances[-1].text)

