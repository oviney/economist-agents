#!/bin/bash
pytest tests/reproduce_stage3.py -v > result.log 2>&1
cat result.log
