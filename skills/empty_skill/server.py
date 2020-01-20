#!/usr/bin/env python
import logging
import time
import os
import copy
import traceback

from flask import Flask, request, jsonify
import sentry_sdk


SKILL_NAME = os.getenv("SKILL_NAME", "unknow_skill")
SKILL_PORT = int(os.getenv("SKILL_PORT", 3000))


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# for tests
# curl -X POST "http://localhost:3000/model" \
# -H "accept: application/json"  -H "Content-Type: application/json" \
# -d "{ \"args\": [ \"data\" ]}"
@app.route("/model", methods=["POST"])
def respond():
    st_time = time.time()
    logger.info(f"input data: {request.json}s")
    total_time = time.time() - st_time
    logger.info(f"{SKILL_NAME} exec time: {total_time:.3f}s")
    return jsonify([[f'{SKILL_NAME} return empty_answer', 0.5]])


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=SKILL_PORT)
