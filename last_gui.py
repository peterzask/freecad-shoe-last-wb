from PySide import QtGui
import FreeCAD as App
import FreeCADGui
import Part
import sys
import importlib

for _mod in ('helper_funcs', 'last_insole', 'last_profile', 'xs_base', 'xs_0',
             'xs_1','xs_2','xs_3','xs_4','xs_5','xs_6','xs_7','xs_8',
             'uv_0', 'make_wireframe'):
    sys.modules.pop(_mod, None)
import last_insole
import last_profile
import xs_base
import xs_0
import xs_1
import xs_2
import xs_3
import xs_4
import xs_5
import xs_6
import xs_7
import xs_8
import uv_0
import make_wireframe

def refresh_view():
    last_insole.doc.recompute()
    view = FreeCADGui.ActiveDocument.ActiveView
    view.viewFront()
    view.fitAll()

def refresh_view_top():
    last_insole.doc.recompute()
    view = FreeCADGui.ActiveDocument.ActiveView
    view.viewTop()
    view.fitAll()

#refresh_view()

class MacroLauncher(QtGui.QWidget):
    def __init__(self):
        super(MacroLauncher, self).__init__()
        self.initUI()

    def initUI(self):
        btn = QtGui.QPushButton('Last Insole Run/Rerun', self)
        btn.clicked.connect(self.run_insole)
        btn2 = QtGui.QPushButton('Last Profile Run/Rerun', self)
        btn2.clicked.connect(self.run_profile)
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
        btn_wf = QtGui.QPushButton('Wireframe preview (fast)', self)
        btn_wf.clicked.connect(self.run_wireframe)
        btn12 = QtGui.QPushButton('uv_0 nurb surface', self)
        btn12.clicked.connect(self.run_uv_0)
        btn13 = QtGui.QPushButton('xs_base', self)
        btn13.clicked.connect(self.run_xs_base)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(btn)                   # insole
        layout.addWidget(btn2)                  # profile
        layout.addWidget(btn3)
        layout.addWidget(btn4)
        layout.addWidget(btn5)
        layout.addWidget(btn6)
        layout.addWidget(btn7)
        layout.addWidget(btn8)
        layout.addWidget(btn9)
        layout.addWidget(btn10)
        layout.addWidget(btn11)
        layout.addWidget(btn_wf)
        layout.addWidget(btn12)
        layout.addWidget(btn13)
        self.setLayout(layout)
        self.setWindowTitle('Last Launcher')
        self.show()

    def run_insole(self):
        importlib.reload(last_insole)
        refresh_view_top()
        print("Insole rebuilt.")

    def run_profile(self):
        importlib.reload(last_profile)
        last_profile.main()
        refresh_view()
        print("Profile rebuilt...")

    def run_xs_base(self):
        importlib.reload(xs_base)
        refresh_view()
        print("xs_base rebuilt.")

    def run_xs_0(self):
        importlib.reload(xs_0)
        refresh_view()
        print("xs_0 rebuilt.")

    def run_xs_1(self):
        importlib.reload(xs_1)
        refresh_view()
        print("xs_1 rebuilt.")

    def run_xs_2(self):
        importlib.reload(xs_2)
        refresh_view()
        print("xs_2 rebuilt.")

    def run_xs_3(self):
        importlib.reload(xs_3)
        refresh_view()
        print("xs_3 rebuilt.")

    def run_xs_4(self):
        importlib.reload(xs_4)
        refresh_view()
        print("xs_4 rebuilt.")

    def run_xs_5(self):
        importlib.reload(xs_5)
        refresh_view()
        print("xs_5 rebuilt.")

    def run_xs_6(self):
        importlib.reload(xs_6)
        refresh_view()
        print("xs_6 rebuilt.")

    def run_xs_7(self):
        importlib.reload(xs_7)
        refresh_view()
        print("xs_7 rebuilt.")

    def run_xs_8(self):
        importlib.reload(xs_8)
        refresh_view()
        print("xs_8 rebuilt.")

    def run_wireframe(self):
        importlib.reload(make_wireframe)
        refresh_view()
        print("Wireframe rebuilt.")

    def run_uv_0(self):
        importlib.reload(uv_0)
        refresh_view()
        print("uv_0 rebuilt.")



    """
    def run_uHJ_xs(self):
        importlib.reload(slast_uHJh_xs)
        refresh_view()
        print("slast_uHJ_xs rebuilt.")

    def run_XS0(self):
        importlib.reload(slast_heel_0)
        refresh_view()
        print("slast_XS0 rebuilt.")
    """
gui = MacroLauncher()
