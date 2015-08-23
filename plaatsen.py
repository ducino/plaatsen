import sys
import traceback
from glob import glob
from itertools import chain
from IPython import embed
import random
from PyQt4 import QtGui, QtCore

def error(msg):
    print "ERROR: " + msg

def flatten(list_of_lists):
    return list(chain.from_iterable(list_of_lists))
    
def get_nb_seats(row):
    return sum(row) + len([1 for i in row if i == 0])
    
class Plaatsen:
    def __init__(self, class_cfg, image_folder):
        self.parse_class_config(class_cfg)
        self.load_images(image_folder)
        
        if sum(flatten(self.class_layout)) != len(self.images):
            error("Number of images: {}\nNumber of seats: {}".format(sum(flatten(self.class_layout)), len(self.images)))
            exit(3)
        
    def parse_class_config(self, class_cfg):
        try:
            self.class_layout = []
            with open(class_cfg) as f:
                for line in f.readlines():
                    self.class_layout.append([int(i) for i in line.split(",")])
        except:
            error("Error opening class config file: " + class_cfg)
            traceback.print_exc()
            exit(3)
           
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
        self.pixmaps = [None]*len(self.pixmap_order)
        self.large_pixmap = None
        
        self.state = STATE_IDLE
        self.current_pixmap = 0
        self.current_seat = 0
        self.widget = None
        self.timer = None
        self.skip_pause = False
        
    def update(self):
        if self.state == STATE_SHOW_IMAGE:
            self.large_pixmap = self.pixmap_order[self.current_pixmap]
            if self.skip_pause:
                self.state = STATE_FIND_SEAT
        elif self.state == STATE_FIND_SEAT:
            self.large_pixmap = None
            self.pixmaps = [None]*len(self.pixmap_order)
            self.pixmaps[self.current_seat] = self.pixmap_order[self.current_pixmap]
            
            if self.pixmaps[self.current_seat] == plaatsen.pixmaps[self.current_seat]:
                self.current_seat = 0
                self.current_pixmap += 1
                self.state = STATE_FOUND_SEAT
                if self.current_pixmap == len(self.pixmaps):
                    self.state = STATE_FOUND_ALL_SEATS
                elif self.skip_pause:
                    self.state = STATE_SHOW_IMAGE
            else:
                self.current_seat += 1
        elif self.state == STATE_FOUND_ALL_SEATS:
            self.pixmaps = plaatsen.pixmaps
        self.widget.update()

    def next(self, widget):
        if self.state == STATE_SHOW_IMAGE:
            self.state = STATE_FIND_SEAT
        elif self.state == STATE_FOUND_SEAT or self.state == STATE_IDLE:
            self.state = STATE_SHOW_IMAGE
            
        self.widget = widget
        if self.timer == None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(400)
            self.timer.timeout.connect(self.update)
            self.timer.start()
        
    def skip(self, widget):
        self.skip_pause = True
        self.next(widget)
        
class PlaatsenWidget(QtGui.QWidget):
    def __init__(self, plaatsen, animator):
        super(PlaatsenWidget, self).__init__()
        self.plaatsen = plaatsen
        self.animator = animator
        self.seat_width = 3
        self.seat_height = 3
        self.margin = 1
        self.scale = 1
        self.height = 800
        self.width = 600
    
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
        if e.key() == QtCore.Qt.Key_Space:
            animator.next(self)
        if e.key() == QtCore.Qt.Key_Escape:
            animator.skip(self)
        
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
            
        qp.end()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: {} <class_config> <image_folder>".format(sys.argv[0])
        exit(3)
    
    app = QtGui.QApplication(sys.argv)
    
    plaatsen = Plaatsen(sys.argv[1], sys.argv[2])
    animator = PlaatsenAnimator(plaatsen)
    w = PlaatsenWidget(plaatsen, animator)
    w.resize(800, 600)
    w.setWindowTitle("Plaatsen v3.0")
    w.show()
        
    sys.exit(app.exec_())