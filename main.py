#!/usr/bin/env python3
import sys
import multiprocessing

from PyQt5.QtWidgets import QApplication

from start_window import StartWindow


def main():
    """Run the application"""
    data_dir = "data"
    config = "config.json"
    app = QApplication(sys.argv)
    window = StartWindow(data_dir, config)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # To avoid problems with stanza
    multiprocessing.set_start_method("spawn")

    main()
