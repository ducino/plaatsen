import sys
import traceback
import random
import time
from glob import glob
from itertools import chain
from IPython import embed
from PyQt4 import QtGui, QtCore

def error(msg):
    print "ERROR: " + msg
    QtGui.QMessageBox.critical(None, "Error", msg)

def flatten(list_of_lists):
    return list(chain.from_iterable(list_of_lists))

def get_nb_seats(row):
    return sum(row) + len([1 for i in row if i == 0])

class Plaatsen:
    def __init__(self, class_cfg, image_folder):
        self.parse_class_config(class_cfg)
        self.load_images(image_folder)

        if sum(flatten(self.class_layout)) != len(self.images):
            error("Number of seats : {}\nNumber of images : {}".format(sum(flatten(self.class_layout)), len(self.images)))
            sys.exit(3)

    def parse_class_config(self, class_cfg):
        try:
            self.class_layout = []
            with open(class_cfg) as f:
                for line in f.readlines():
                    self.class_layout.append([int(i) for i in line.split(",")])
        except Exception, e:
            error("Error opening class config file: {}\n{}".format(class_cfg, e))
            traceback.print_exc()
            sys.exit(3)

    def load_images(self, image_folder):
        self.images = glob("{}/*".format(image_folder))
        random.shuffle(self.images)
        self.pixmaps = []
        for image in self.images:
            self.pixmaps.append(QtGui.QPixmap(image))

    def get_nb_rows(self):
        return len(self.class_layout)


STATE_SHOW_IMAGE = 0
STATE_FIND_SEAT = 1
STATE_FOUND_SEAT = 2
STATE_FOUND_ALL_SEATS = 3
STATE_IDLE = 4

class PlaatsenAnimator():
    def __init__(self, plaatsen):
        self.plaatsen = plaatsen
        self.pixmap_order = list(plaatsen.pixmaps)
        random.shuffle(self.pixmap_order)

        self.reset()
        self.widget = None
        self.timer = None

        self.selected_animation = 0
        self.animations = []
        self.animation_descriptions = []
        self.animations.append(self.linear_search)
        self.animation_descriptions.append("Lineair zoeken")
        self.animations.append(self.random_search)
        self.animation_descriptions.append("Willekeurig zoeken")
        self.animations.append(self.random_shuffle)
        self.animation_descriptions.append("Shuffle")

    def set_widget(self, widget):
        self.widget = widget
        if self.timer == None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(400)
            self.timer.timeout.connect(self.update)
            self.timer.start()

    def reset(self):
        self.speed = 1
        self.skip_pause = False
        self.clear_pixmaps()
        self.large_pixmap = None
        self.current_pixmap = 0
        self.current_seat = 0
        self.start_time = time.time()
        self.transition(STATE_IDLE)

    def set_period(self, period):
        self.timer.setInterval(period*self.speed)
    def inc_speed(self):
        self.speed -= 0.05
        if self.speed < 0.01:
            self.speed = 0.01
    def dec_speed(self):
        self.speed += 0.05

    def search(self):
        self.clear_pixmaps()
        self.pixmaps[self.current_seat] = self.pixmap_order[self.current_pixmap]

        if self.pixmaps[self.current_seat] == plaatsen.pixmaps[self.current_seat]:
            self.timer.setInterval(1000)
            self.current_seat = 0
            self.current_pixmap += 1
            self.transition(STATE_FOUND_SEAT)
            if self.current_pixmap == len(self.pixmaps):
                self.transition(STATE_FOUND_ALL_SEATS)
            elif self.skip_pause:
                self.transition(STATE_SHOW_IMAGE)
            return True
        else:
            return False

    def linear_search(self):
        self.set_period(600)

        if not self.search():
            self.current_seat += 1

    def random_search(self):
        self.set_period(100)

        if not self.search():
            self.current_seat = random.randint(0, len(plaatsen.pixmaps)-1)

    def random_shuffle(self):
        current_time = time.time() - self.start_time
        self.pixmaps = list(plaatsen.pixmaps)
        if current_time < 10:
            self.set_period(current_time*50)
            random.shuffle(self.pixmaps)
        else:
            self.transition(STATE_FOUND_ALL_SEATS)

    def clear_pixmaps(self):
        self.pixmaps = [None]*len(plaatsen.pixmaps)

    def transition(self, state):
        if state == STATE_FIND_SEAT:
            self.start_time = time.time()
        self.state = state

    def update(self):
        if self.state == STATE_SHOW_IMAGE:
            self.large_pixmap = self.pixmap_order[self.current_pixmap]
            self.timer.setInterval(1200)
            if self.skip_pause:
                self.transition(STATE_FIND_SEAT)
        elif self.state == STATE_FIND_SEAT:
            self.large_pixmap = None
            self.animations[self.selected_animation]()
        elif self.state == STATE_FOUND_ALL_SEATS:
            self.pixmaps = plaatsen.pixmaps
        self.widget.update()

    def next(self):
        if self.state == STATE_SHOW_IMAGE:
            self.transition(STATE_FIND_SEAT)
        elif self.state == STATE_FOUND_SEAT or self.state == STATE_IDLE:
            if self.selected_animation <= 1:
                self.transition(STATE_SHOW_IMAGE)
            else:
                self.transition(STATE_FIND_SEAT)
        self.widget.update()

    def skip(self):
        self.skip_pause = True
        self.next()

    def set_animation(self, animation):
        self.selected_animation = animation

class PlaatsenWidget(QtGui.QWidget):
    def __init__(self, plaatsen, animator):
        super(PlaatsenWidget, self).__init__()
        self.plaatsen = plaatsen
        self.animator = animator
        self.animator.set_widget(self)
        self.seat_width = 3
        self.seat_height = 3
        self.margin = 1
        self.scale = 1
        self.height = 800
        self.width = 600
        self.msg = None
        self.msg_time = time.time()

    def resizeEvent(self, e):
        window_size = e.size()
        self.height = window_size.height()
        self.width  = window_size.width()
        class_height = (plaatsen.get_nb_rows()+1)*self.margin + plaatsen.get_nb_rows()*self.seat_height
        scale = float(self.height) / class_height

        for row in plaatsen.class_layout:
            row_width = (len(row)+1)*self.margin + get_nb_seats(row)*self.seat_width
            scale = min(scale, float(self.width)/row_width)

        self.scale = scale

    def margin_px(self):
        return int(self.scale * self.margin)
    def seat_width_px(self):
        return int(self.scale * self.seat_width)
    def seat_height_px(self):
        return int(self.scale * self.seat_height)

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Backspace:
            animator.reset()
        if e.key() == QtCore.Qt.Key_Space:
            animator.next()
        if e.key() == QtCore.Qt.Key_Escape:
            animator.skip()
        if e.key() == QtCore.Qt.Key_Plus:
            animator.inc_speed()
            self.message("Snelheid: {:.2f}".format(1./animator.speed))
        if e.key() == QtCore.Qt.Key_Minus:
            animator.dec_speed()
            self.message("Snelheid: {:.2f}".format(1./animator.speed))
        if e.key() >= QtCore.Qt.Key_1 and e.key() <= QtCore.Qt.Key_3:
            animator.set_animation(e.key() - QtCore.Qt.Key_1)
            self.message("Animatie: {}".format(animator.animation_descriptions[animator.selected_animation]))
            self.msg
        if e.key() == QtCore.Qt.Key_H:
            help = ["Space : Volgende stap",
                    "Escape : Toon alle stappen",
                    "Backspace : Reset animatie",
                    "+ : Versnel animatie",
                    "- : Vertraag animatie",
                    "H : Toon deze help",
                    "",
                    "Animaties:"]
            for i, label in enumerate(animator.animation_descriptions):
                help.append("{} : {}".format(i+1, label))
            QtGui.QMessageBox.information(self, "Help", "\n".join(help))
        self.update()

    def message(self, msg):
        self.msg = msg
        self.msg_time = time.time()
    def paintEvent(self, e):
        def fill_seat(r, g, b):
            qp.fillRect(x, y, self.seat_width_px(), self.seat_height_px(), QtGui.QColor(r, g, b))
        def image_rectangle(pixmap, x, y, max_width, max_height):
            scale = min(float(max_width) / pixmap.width(), float(max_height) / pixmap.height())
            pixmap_width = int(scale*pixmap.width())
            pixmap_height = int(scale*pixmap.height())
            offset_x = (max_width - pixmap_width)/2
            offset_y = (max_height - pixmap_height)/2
            qp.drawPixmap(x+offset_x+1, y+offset_y+1, pixmap_width, pixmap_height, pixmap)
        def image_seat(pixmap):
            if pixmap == None:
                return
            image_rectangle(pixmap, x, y, self.seat_width_px(), self.seat_height_px())

        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setPen(QtGui.QColor(0, 20, 0))

        height = (plaatsen.get_nb_rows()+1)*self.margin_px() + plaatsen.get_nb_rows()*self.seat_height_px()
        x = 0
        y = (self.height - height)/2 + self.margin_px()
        n = 0
        for row in plaatsen.class_layout:
            row_width = (len(row)+1)*self.margin_px() + get_nb_seats(row)*self.seat_width_px()
            x = (self.width - row_width)/2 + self.margin_px()
            for i in row:
                if i == 0:
                    fill_seat(46, 46, 46)
                    x += self.seat_width_px()
                else:
                    for j in range(i):
                        fill_seat(150, 150, 150)
                        qp.drawRect(x, y, self.seat_width_px(), self.seat_height_px())
                        image_seat(animator.pixmaps[n])
                        n += 1
                        x += self.seat_width_px()
                x += self.margin_px()
            y += self.margin_px() + self.seat_height_px()

        if animator.large_pixmap != None:
            image_rectangle(animator.large_pixmap, 0, 0, self.width, self.height)

        if self.msg != None and time.time() - self.msg_time < 1:
            qp.drawText(self.margin_px(), self.margin_px(), self.msg)

        qp.end()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: {} <class_config> <image_folder>".format(sys.argv[0])
        sys.exit(3)

    app = QtGui.QApplication(sys.argv)

    plaatsen = Plaatsen(sys.argv[1], sys.argv[2])
    animator = PlaatsenAnimator(plaatsen)
    w = PlaatsenWidget(plaatsen, animator)
    w.resize(800, 600)
    w.setWindowTitle("Plaatsen v3.0")
    w.show()

    sys.exit(app.exec_())