import sys, os
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.path.expanduser("~/00_ausr/work/freecad/macros")
if _here not in sys.path:
    sys.path.insert(0, _here)

from PySide import QtGui
import FreeCAD as App
import FreeCADGui
import importlib

# No top-level macro imports — all deferred to button handlers so
# errors in any module don't prevent the GUI from appearing.

def refresh_view():
    App.ActiveDocument.recompute()
    view = FreeCADGui.ActiveDocument.ActiveView
    view.viewFront()
    view.fitAll()

def refresh_view_top():
    App.ActiveDocument.recompute()
    view = FreeCADGui.ActiveDocument.ActiveView
    view.viewTop()
    view.fitAll()

class MacroLauncher(QtGui.QWidget):
    def __init__(self):
        super(MacroLauncher, self).__init__()
        self.initUI()

    def initUI(self):
        btn = QtGui.QPushButton('Last Insole Run/Rerun', self)
        btn.clicked.connect(self.run_insole)
        btn2 = QtGui.QPushButton('Last Profile Run/Rerun', self)
        btn2.clicked.connect(self.run_profile)
        btn_cc = QtGui.QPushButton('control_curves', self)
        btn_cc.clicked.connect(self.run_control_curves)
        btn3 = QtGui.QPushButton('xs_0 heel', self)
        btn3.clicked.connect(self.run_xs_0)
        btn4 = QtGui.QPushButton('xs_1 heel', self)
        btn4.clicked.connect(self.run_xs_1)
        btn5 = QtGui.QPushButton('xs_2 crown', self)
        btn5.clicked.connect(self.run_xs_2)
        btn6 = QtGui.QPushButton('xs_3 crown', self)
        btn6.clicked.connect(self.run_xs_3)
        btn7 = QtGui.QPushButton('xs_4 crown', self)
        btn7.clicked.connect(self.run_xs_4)
        btn8 = QtGui.QPushButton('xs_5 crown', self)
        btn8.clicked.connect(self.run_xs_5)
        btn9 = QtGui.QPushButton('xs_6 crown', self)
        btn9.clicked.connect(self.run_xs_6)
        btn10 = QtGui.QPushButton('xs_7 crown', self)
        btn10.clicked.connect(self.run_xs_7)
        btn11 = QtGui.QPushButton('xs_8 crown', self)
        btn11.clicked.connect(self.run_xs_8)
        btn11b = QtGui.QPushButton('xs_9 toe', self)
        btn11b.clicked.connect(self.run_xs_9)
        btn_wf = QtGui.QPushButton('Wireframe preview (fast)', self)
        btn_wf.clicked.connect(self.run_wireframe)
        btn12 = QtGui.QPushButton('uv_0 nurb surface', self)
        btn12.clicked.connect(self.run_uv_0)
        btn13 = QtGui.QPushButton('xs_base', self)
        btn13.clicked.connect(self.run_xs_base)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(btn)
        layout.addWidget(btn2)
        layout.addWidget(btn_cc)
        layout.addWidget(btn3)
        layout.addWidget(btn4)
        layout.addWidget(btn5)
        layout.addWidget(btn6)
        layout.addWidget(btn7)
        layout.addWidget(btn8)
        layout.addWidget(btn9)
        layout.addWidget(btn10)
        layout.addWidget(btn11)
        layout.addWidget(btn11b)
        layout.addWidget(btn_wf)
        layout.addWidget(btn12)
        layout.addWidget(btn13)
        self.setLayout(layout)
        self.setWindowTitle('Last Launcher')
        self.show()

    def run_insole(self):
        import last_insole
        importlib.reload(last_insole)
        refresh_view_top()
        print("Insole rebuilt.")

    def run_profile(self):
        import last_profile
        importlib.reload(last_profile)
        last_profile.main()
        refresh_view()
        print("Profile rebuilt...")

    def run_control_curves(self):
        import control_curves
        importlib.reload(control_curves)
        refresh_view()
        print("control_curves rebuilt.")

    def run_xs_base(self):
        import xs_base
        importlib.reload(xs_base)
        refresh_view()
        print("xs_base rebuilt.")

    def run_xs_0(self):
        import xs_0
        importlib.reload(xs_0)
        refresh_view()
        print("xs_0 rebuilt.")

    def run_xs_1(self):
        import xs_1
        importlib.reload(xs_1)
        refresh_view()
        print("xs_1 rebuilt.")

    def run_xs_2(self):
        import xs_2
        importlib.reload(xs_2)
        refresh_view()
        print("xs_2 rebuilt.")

    def run_xs_3(self):
        import xs_3
        importlib.reload(xs_3)
        #refresh_view()
        print("xs_3 rebuilt.")

    def run_xs_4(self):
        import xs_4
        importlib.reload(xs_4)
        refresh_view()
        print("xs_4 rebuilt.")

    def run_xs_5(self):
        import xs_5
        importlib.reload(xs_5)
        refresh_view()
        print("xs_5 rebuilt.")

    def run_xs_6(self):
        import xs_6
        importlib.reload(xs_6)
        refresh_view()
        print("xs_6 rebuilt.")

    def run_xs_7(self):
        import xs_7
        importlib.reload(xs_7)
        refresh_view()
        print("xs_7 rebuilt.")

    def run_xs_8(self):
        import xs_8
        importlib.reload(xs_8)
        refresh_view()
        print("xs_8 rebuilt.")

    def run_xs_9(self):
        import xs_9
        importlib.reload(xs_9)
        refresh_view()
        print("xs_9 rebuilt.")

    def run_wireframe(self):
        import make_wireframe
        importlib.reload(make_wireframe)
        refresh_view()
        print("Wireframe rebuilt.")

    def run_uv_0(self):
        import uv_0
        importlib.reload(uv_0)
        refresh_view()
        print("uv_0 rebuilt.")

gui = MacroLauncher()
