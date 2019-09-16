#!/bin/bash
source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n ner > ./logs/ner.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n chitchat_odqa > ./logs/chitchat_odqa.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n chitchat > ./logs/chitchat.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n odqa > ./logs/odqa.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n max_confidence > ./logs/max_confidence.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py service -n test_formatter > ./logs/test_formatter.log 2>&1 &

source ../../env/bin/activate &&
mkdir -p ./logs/ &&
python ../../core/run.py agent > ./logs/agent.log 2>&1 &