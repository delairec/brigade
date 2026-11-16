import sys
import time

from brigade.adapters.test_clients.replay_recording import ReplayClock, replay_recording

if __name__ == "__main__":
    replay_recording(sys.argv[1:], ReplayClock(read_epoch=time.time, sleep=time.sleep), sys.stdout)
