#!/bin/bash
kill $(ps -aux | grep 'core/run.py service' | cut -d\  -f2)
kill $(ps -aux | grep 'core/run.py agent' | cut -d\  -f2)
