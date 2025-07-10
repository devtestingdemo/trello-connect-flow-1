import os
import sys
from redis import Redis
from rq import Worker, Queue, Connection

# Ensure the backend directory is in the Python path
sys.path.append(os.path.dirname(__file__))

listen = ['trello-events']  # The queue(s) to listen to

redis_conn = Redis()

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()