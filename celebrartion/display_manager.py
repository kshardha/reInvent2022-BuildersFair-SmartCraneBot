from threading import Thread
from subprocess import Popen, TimeoutExpired
import time

DISPLAY_DELAY = 10
DEFAULT_DISPLAY_IMAGE="./test.ppm"
CELEBRATION_DISPLAY_IMAGE=""
CMD = ["./demo", "--led-rows=32", "--led-cols=64", "-D1"]

class TextScroller:
    def __init__(self, text_ppm_file):
        self.text_ppm_file = text_ppm_file
        self.test_text = "testing"

    def start_scroll_text(self, timeout=-1):
        try:
            self.process = Popen(CMD, shell=True)
            if timeout>0:
                self.process.wait(timeout)
        except TimeoutExpired as exp:
            self.process.kill()
        except Exception as ex:
            print(ex)

    def stop_scroll_text(self):
        try:
            if self.process is not None: 
                self.process.kill()
        except Exception as ex:
            print(ex)

    def process(self):
        return self.process

    def run(self):
        th = Thread(target=self.start_scroll_text, args=[])
        th.start()



if __name__ == '__main__':
    t = TextScroller(DEFAULT_DISPLAY_IMAGE, 30)
    t.run()