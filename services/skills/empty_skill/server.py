#!/usr/bin/env python
import logging
import time
import os

from flask import Flask, request, jsonify


SERVICE_NAME = os.getenv("SERVICE_NAME", "unknow_skill")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 3000))


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
    logger.info(f"{SERVICE_NAME} exec time: {total_time:.3f}s")
    return jsonify([[f"{SERVICE_NAME} return empty_answer", 0.5]])


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=SERVICE_PORT)
