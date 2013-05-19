import PyQt4.QtGui as QG
import PyQt4.QtCore as QC

def chunk(seq, size):
    for i in xrange(0, len(seq), size):
        yield seq[i:i+size]


class TextSysTray(object):
    def __init__(self, parent, text, ntray=2, **kwargs):
        self.stray = [QG.QSystemTrayIcon(parent) for _ in xrange(ntray)]
        self._curr_text = None
        self.update_text(text, **kwargs)

    def show(self):
        for stray in self.stray:
            stray.show()

    def update_text(self, text, color=QC.Qt.black, chunk_size=1):
        if text == self._curr_text:
            return
        self._curr_text = text

        self.pix = []
        tc = chunk(text, chunk_size)
        for stray in self.stray[::-1]:
            pix = QG.QPixmap(24, 16)
            pix.fill(QC.Qt.transparent)
            self.pix.append(pix)

            painter = QG.QPainter()
            painter.begin(pix)
            painter.setPen(color)
            try:
                t = next(tc)
            except StopIteration:
                t = ''
            painter.drawText(pix.rect(), QC.Qt.AlignRight, t)
            painter.end()

            stray.setIcon(QG.QIcon(pix))


if __name__ == "__main__":
    app = QG.QApplication([])
    win = QG.QDialog()
    trayicon = TextSysTray(win, '888.8', chunk_size=3)
    trayicon.show()
    win.show()
    app.exec_()
