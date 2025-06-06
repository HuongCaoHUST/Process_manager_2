import npyscreen
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from _2_display_module.resource.resource_layout import ResourceBox
from _2_display_module.menu.menu_layout import MenuBox
from _2_display_module.process.process_layout import ProcessBox
from _1_auto_run.running_process import start_CRP_threads, destroy_CRP_threads
from _4_system_data import CRP_control
import threading
import time
class MainForm(npyscreen.Form):
    OK_BUTTON_TEXT = "Exit"
    def create(self):
        height, width = self.lines, self.columns
        self.welcome = self.add(npyscreen.TitleText, name="Welcome", value="This is Process Manager App", editable=False)
        
        try:
            # self.add(ProcessBox, max_height=15)
            self.process_box = self.add(ProcessBox, max_height=15)
            
            self.add(MenuBox, relx=2, rely=18, max_width=int(width * 0.35), max_height=6)
            self.resource_box = self.add(ResourceBox, relx=2+int(width*0.36), rely=18, max_height=6)
            start_CRP_threads(self.process_box, self.resource_box)
            
        except npyscreen.wgwidget.NotEnoughSpaceForWidget:
            self.process_box = self.add(npyscreen.TitleText, name="Error", value="Not enough space for process list")
        
        self.next_form = None
        self.add(npyscreen.ButtonPress, name="Go to Second Form", when_pressed_function=self.go_to_second_form)

    def beforeEditing(self):
        start_CRP_threads(self.process_box, self.resource_box)
    def go_to_second_form(self):
        destroy_CRP_threads()
        self.next_form = 'SECOND'
        self.editing = False
    def afterEditing(self):
        destroy_CRP_threads()
        if self.next_form:
            self.parentApp.setNextForm(self.next_form)
        else:
            self.parentApp.setNextForm(None)

    def on_ok(self):
        destroy_CRP_threads()
        self.parentApp.setNextForm(None)  # thoát chương trình
        self.editing = False
# class SecondForm(npyscreen.Form):
#     OK_BUTTON_TEXT = "Back"
#     def create(self):
#         self.add(npyscreen.TitleText, name="Second Form", value="This is the Second Form", editable=False)
#         self.add(npyscreen.TitleText, name="Sample", value="Hello from Second Form!")
#         self.add(npyscreen.ButtonPress, name="Back to Main Form", when_pressed_function=self.switch_to_main_form)
    
#     def switch_to_main_form(self):
#         self.parentApp.switchForm('MAIN')

#     def afterEditing(self):
#         self.parentApp.switchForm('MAIN')

class AutoUpdateProcessBox(npyscreen.BoxTitle):
    _contained_widget = npyscreen.MultiLine

    def __init__(self, screen, *args, **keywords):
        super().__init__(screen, *args, **keywords)
        self.name = "PROCESS DETAILS (Auto-Update)"
        self.editable = False
        self.scroll_exit = True
        self.pid = None
        self.update_thread = None
        self.running = False
        self.lock = threading.Lock()

    def set_pid(self, pid):
        with self.lock:
            self.pid = pid
            if pid is not None:
                self._start_auto_update()

    def _start_auto_update(self, interval=1.0):
        if self.running:
            self._stop_auto_update()
        
        self.running = True
        self.update_thread = threading.Thread(
            target=self._update_loop,
            args=(interval,),
            daemon=True
        )
        self.update_thread.start()

    def _stop_auto_update(self):
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=0.5)

    def _update_loop(self, interval):
        while self.running:
            with self.lock:
                current_pid = self.pid
                self._safe_update(current_pid)
            time.sleep(interval)

    def _safe_update(self, pid):
        if pid is None:
            return

        try:
            status = CRP_control.get_process_info(pid)
            if status < 0:
                self.entry_widget.values = [f"Error getting process info (code: {status})"]
            else:
                info = CRP_control.PID_properties
                rows = [
                    f"Name: {info['Name']}",
                    f"PID: {info['PID']} | PPID: {info['PPID']}",
                    f"Status: {info['Status']} | User: {info['Username']}",
                    f"CPU: {info['CPU Usage']}% (Core {info['CPU Num']})",
                    f"Memory: {info['MEM_VMS']}MB (RSS: {info['MEM_RSS']}MB, {info['MEM_Percent']}%)",
                    f"Runtime: {info['Runtime']}",
                    f"Threads: {info['Num Threads']} | I/O: R{info['I/O Read Count']}/W{info['I/O Write Count']}",
                    f"Last Update: {time.strftime('%H:%M:%S')}"
                ]
                self.entry_widget.values = rows
            
            # Thread-safe display update
            if hasattr(self, 'entry_widget'):
                self.entry_widget.display()
        except Exception as e:
            self.entry_widget.values = [f"Update error: {str(e)}"]
            self.entry_widget.display()

class ProcessMonitorForm(npyscreen.Form):
    
    def create(self):
        y, x = self.useable_space()
        
        # PID Input
        self.pid_input = self.add(
            npyscreen.TitleText,
            rely=2,
            relx=2,
            name="Enter PID:",
            use_two_lines=False
        )
        
        # Auto-updating Process Info
        self.process_box = self.add(
            AutoUpdateProcessBox,
            rely=5,
            relx=2,
            max_height=12,
            max_width=x-4
        )
        
        # Control Buttons
        self.add_btn = self.add(
            npyscreen.ButtonPress,
            rely=19,
            relx=2,
            name="Set PID",
            when_pressed_function=self.on_set_pid
        )
        
        self.exit_btn = self.add(
            npyscreen.ButtonPress,
            rely=19,
            relx=20,
            name="Exit",
            when_pressed_function=self.on_exit
        )

    def on_set_pid(self):
        try:
            pid = int(self.pid_input.value)
            self.process_box.set_pid(pid)
        except ValueError:
            self.process_box.entry_widget.values = ["Invalid PID!"]
            self.process_box.entry_widget.display()

    def on_exit(self):
        self.process_box._stop_auto_update()
        self.parentApp.switchForm('MAIN')

class MyApplication(npyscreen.NPSAppManaged):
   def onStart(self):
       self.addForm('MAIN', MainForm, name='PROCESS MANAGER SYSTEM')
       self.addForm('SECOND', ProcessMonitorForm, name='SECOND FORM')

if __name__ == '__main__':
   TestApp = MyApplication().run()