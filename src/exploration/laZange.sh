#!/bin/bash
git clone https://github.com/AlessandroZ/LaZagne.git
cd LaZagne
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd Linux/
python3 laZagne.py