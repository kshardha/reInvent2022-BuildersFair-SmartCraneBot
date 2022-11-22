from threading import Thread
from subprocess import Popen, TimeoutExpired
import time

DISPLAY_DELAY = 10
GOAL_CMD = ["./demo", "--led-rows=32", "--led-cols=64", "-D1", "./goal.ppm"]

class TextScroller:
    def __init__(self,command, text_ppm_file):
        self.text_ppm_file = text_ppm_file
        self.command = command

    def start_scroll_text(self, timeout=-1):
        try:
            self.process = Popen(self.command)
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
        th = Thread(target=self.start_scroll_text, args=[30])
        th.start()



if __name__ == '__main__':
    t = TextScroller(GOAL_CMD, "goal")
    t.run()
