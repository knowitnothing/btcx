import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

class TextSysTray(object):
    def __init__(self, parent, text):
        self.stray1 = QG.QSystemTrayIcon(parent) # Yep..
        self.stray2 = QG.QSystemTrayIcon(parent) # thad bad.
        self._curr_text = None
        self.update_text(text)

    def show(self):
        self.stray2.show()
        self.stray1.show()

    def update_text(self, text, color=QC.Qt.black):
        if text == self._curr_text:
            return
        self._curr_text = text
        pixmap1 = QG.QPixmap(24, 16)
        pixmap1.fill(QC.Qt.transparent)
        pixmap2 = QG.QPixmap(24, 16)
        pixmap2.fill(QC.Qt.transparent)

        painter = QG.QPainter()
        painter.begin(pixmap1)
        painter.setPen(color)
        painter.drawText(pixmap1.rect(), QC.Qt.AlignRight, str(text)[:3])
        painter.end()
        painter = QG.QPainter()
        painter.begin(pixmap2)
        painter.setPen(color)
        painter.drawText(pixmap2.rect(), QC.Qt.AlignLeft, str(text)[3:])
        painter.end()

        self.stray1.setIcon(QG.QIcon(pixmap1))
        self.stray2.setIcon(QG.QIcon(pixmap2))


if __name__ == "__main__":
    app = QG.QApplication([])
    win = QG.QDialog()
    trayicon = TextSysTray(win, '888.8')
    trayicon.show()
    win.show()
    app.exec_()
