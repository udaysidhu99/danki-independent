import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel

def main():
    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("Danki Independent — MVP Shell")
    layout = QVBoxLayout()
    layout.addWidget(QLabel("Hello, Danki Independent!"))
    win.setLayout(layout)
    win.resize(400, 200)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
