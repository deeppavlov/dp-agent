#!/usr/bin/env python
import logging
import time
import os
import random

from flask import Flask, request, jsonify


SERVICE_NAME = os.getenv("SERVICE_NAME", "unknow_skill")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 3000))


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


greeting_begin_texts = [
    "Хорошо здоровается тот, кто здоровается первым.",
    "Я встретил Вас. Значит: «День добрый!»",
    "'Очень добрый день! А это там что? И это все мне ?!!' ©Маша и медведь",
    "'Я пришёл к тебе с приветом, топором и пистолетом.' ©Источник неизвестен",
    "Раньше когда люди здоровались, снимали шляпу, а сейчас при встречи вытаскивают наушники из ушей.",
]
greeting_body_text = (
    "Надеюсь у Вас хорошее настроение, я чат-бот и готов с вами "
    "пообщаться в свободной форме. Не могу гарантировать, но постараюсь отвечать на вопросы связанные с "
    "реальными фактами. Ответы на вопросы о фактах могут быть не совсем верными или даже совсем неверными, "
    "если это выходит за рамки моих знаний. К моему сожалению, я сейчас не так много знаю. "
    "Я с радостью постараюсь поддержать диалог на любую интересную для Вас тему."
)
greeting_end_texts = [
    "Как дела?",
    "О чем бы ты хотел поговорить с чат-ботом?",
    "Что делаешь?",
    "О чем хочешь поговорить?",
]
# for tests
# curl -X POST "http://localhost:3000/model" \
# -H "accept: application/json"  -H "Content-Type: application/json" \
# -d "{ \"args\": [ \"data\" ]}"
@app.route("/model", methods=["POST"])
def respond():
    st_time = time.time()
    # logger.info(f"input data: {request.json}s")
    batch_len = len(request.json["x"])
    response = [
        (f"{random.choice(greeting_begin_texts)}\n{greeting_body_text}\n{random.choice(greeting_end_texts)}", 1.0)
        for _ in range(batch_len)
    ]
    total_time = time.time() - st_time
    logger.info(f"{SERVICE_NAME} exec time: {total_time:.3f}s")
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=SERVICE_PORT)
