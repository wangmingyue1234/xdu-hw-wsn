import threading

from main import main


if __name__ == '__main__':
    threading.main_thread().setName('main')
    main(False)
