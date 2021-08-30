python receiver_part3.py 20000 8 > out.txt &
python sender_part3.py 127.0.0.1 20000 8 < test_big.txt