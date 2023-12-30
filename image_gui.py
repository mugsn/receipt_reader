import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd, messagebox as mb
import threading
from PIL import Image, ImageTk, ImageOps

#own scripts
import db_helper as db
import text_recognition as tr

#platform/os checks
import platform, io, subprocess

#check if a raspberry pi camera is connected
def raspberrypi_cam():
    if "Linux" in platform.platform():
        try:
            with io.open("/sys/firmware/devicetree/base/model", "r") as m:
                if "raspberry pi" in m.read().lower():
                    cmd_result = subprocess.getoutput("vcgencmd get_camera")
                    if "detected=1" in cmd_result:
                        return True
                    #
                #
            #
        #
        except Exception: 
            pass
        #
    #
    return False
#
#use raspberry pi cam specific image_capture script if detected
raspberrypi_cam = raspberrypi_cam()
if raspberrypi_cam:
    import image_capture_rpi as ic
else:
    import image_capture as ic
#

#default window sizes
main_window_size = [800, 600]
db_window_size = [500, 400]
icon_path = "icon.png"

class Main_window(tk.Tk):
    def __init__(self):
        super().__init__()
        
        #title, icon(True applies it to every subwindow as well), default window size
        self.title("Image GUI")
        self.iconphoto(True, tk.PhotoImage(file=icon_path))
        self.minsize(main_window_size[0], main_window_size[1])
        
        #variables
        self.full_image = None
        self.info_message = tk.StringVar()
        self.win_size = main_window_size
        self.after_id = None
        self.camera = None
        
        #bind window resize event
        self.bind("<Configure>", self.change_win_size)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        #bottom controls
        self.bottom_bar()
        
        #label for preview video and images
        self.img_preview = tk.Label(self)
        self.img_preview.pack()
        
        #force update so values get initialized, show placeholder logo in window
        self.update()
        self.refresh_img(Image.open(icon_path))
    #
    #create bottom bar, buttons and info text
    def bottom_bar(self):
        b_padding, b_height = 10, 2
        self.bot_bar = tk.Frame(self)
        self.bot_bar.pack(side=tk.BOTTOM)
        
        self.capture_b = tk.Button(self.bot_bar, text=" Open camera ", command=self.start_preview_thread, height=b_height)
        self.capture_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=b_padding, pady=b_padding)
        
        self.file_b = tk.Button(self.bot_bar, text=" Choose image ", command=self.open_file, height=b_height)
        self.file_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=b_padding, pady=b_padding)
        
        self.detect_b = tk.Button(self.bot_bar, text=" Detect text ", state=tk.DISABLED, command=self.detect_text_thread, height=b_height)
        self.detect_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=b_padding, pady=b_padding)
        
        self.database_b = tk.Button(self.bot_bar, text=" View database ", command=self.new_window, height=b_height)
        self.database_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=b_padding, pady=b_padding)
        
        self.info_t = tk.Label(self.bot_bar, textvariable=self.info_message)
        self.info_t.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=b_padding, pady=b_padding)
    #
    #spawn new window, if window already exists, focus it
    def new_window(self):
        if db.exists():
            self.info_message.set("")
            self.db_win = Database_window(self)
            self.database_b.configure(command=self.db_win.focus_force)
        else:
            self.info_message.set("No database found")
    #
    #create thread for text detection
    def detect_text_thread(self):
        if self.full_image:
            detect_text_thread = threading.Thread(target=self.detect_text)
            detect_text_thread.start()
        #
    #
    #run through text detection on image, and display textbox with relults
    #ask if user wants to save to database
    def detect_text(self):
        self.info_message.set("Detecting text...")
        self.detect_b.config(state=tk.DISABLED)
        
        result = tr.detect_text_from_img(self.full_image)
        
        msg_string = f"Date & Time: {result['date_time']}\nTotal Amount: {result['price']} €\nVAT: {result['vat']} %\nSave to database?"
        
        msg_box = mb.askyesno("Detected text", msg_string)
        
        if msg_box: #Yes
            success = db.add_row(result)
            if success:
                self.info_message.set("Data saved")
            else:
                self.info_message.set("Invalid data")
            #
        else: #No
            self.info_message.set("")
        #    
        self.detect_b.config(state=tk.NORMAL)
    #
    #change and/or resize the current image (seperate from cam preview)
    def refresh_img(self, new_img=None):
        new_size = self.get_size()
        
        if self.camera and not raspberrypi_cam:
            self.camera.change_size(new_size)
        #    
        if new_img:
            self.full_image = new_img
        else:
            new_img = self.full_image
        #
        new_img = ImageOps.contain(new_img, new_size, method=Image.Resampling.BICUBIC)
        new_img = ImageTk.PhotoImage(new_img)
        
        self.img_preview.configure(width=new_size[0], height=new_size[1], image=new_img)
        self.img_preview.image = new_img #hack to prevent garbage collection
        #
    #
    #dialogue for importing an already existing image
    def open_file(self):
        if self.camera:
            self.close_cam()
        filepath = fd.askopenfilename(filetypes=[("Images", ".jpg .png")])
        if filepath:
            self.img_preview.pack()
            self.refresh_img(Image.open(filepath))
            self.detect_b.config(state=tk.NORMAL)
        #
    #
    #create a thread for camera preview
    def start_preview_thread(self):
        cam_preview_thread = threading.Thread(target=self.start_preview)
        cam_preview_thread.start()
    #
    #start camera preview and change button functions
    def start_preview(self):
        self.detect_b.config(state=tk.DISABLED)
        self.camera = ic.Webcam(self, self.get_size())
        
        if self.camera.cam:
            self.info_message.set("")
            self.capture_b.configure(text=" Capture image ", command=self.start_image_capture)
            self.camera.start_preview_thread()
        else:
            self.info_message.set("No camera found")
        #
    #
    #close initialized camera object/thread
    def close_cam(self):
        if self.camera:
            self.camera.close()
            self.camera = None
        self.capture_b.configure(text=" Open camera ", command=self.start_preview_thread)
    #
    #create image capture thread for full resolution imagew
    def start_image_capture(self):
        self.info_message.set("Capturing image...")
        self.camera.start_capture_thread()
    #
    #called from image_capture object, after full res image capture has succeeded
    def end_image_capture(self, new_img):
        self.close_cam()
        self.info_message.set("")
        self.refresh_img(new_img)
        self.detect_b.config(state=tk.NORMAL)
    #
    #detect window resize event, schedule resize event if showing preview or image
    def change_win_size(self, event):
        widget = str(event.widget)
        if widget == ".": # "." is Toplevel
            if self.win_size[0] != event.width or self.win_size[1] != event.height:
                self.win_size = [event.width, event.height]
                
                if self.full_image or self.camera:
                    self.schedule_resize()
                #
            #
        #
    #
    #schedule image resize, if already scheduled, restart timer
    #need to do this because tkinter calls the resize event constantly when resizing, and not just once you release the mouse
    def schedule_resize(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        self.after_id = self.after(100, self.refresh_img)
    #
    #return available space inside window minus bottom bar size
    def get_size(self):
        return (self.win_size[0] - 4, (self.win_size[1] - self.bot_bar.winfo_height() - 4))
    #
    #close main window event to kill camera preview, otherwise keeps running because it's in a seperate thread
    def on_close(self):
        self.close_cam()
        self.destroy()
    #
#

class Database_window(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        
        #title and default window size
        self.title("Database viewer")
        self.minsize(db_window_size[0], db_window_size[1])
        
        #variables
        self.page_index = 0
        self.page_text = tk.StringVar()
        
        #bind window close event
        self.protocol("WM_DELETE_WINDOW", self.close)
        
        #main frame for scaling
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        #spreadsheet view
        self.tree_view()
        
        #bottom controls
        self.bottom_bar()
        
        #populate spreadsheet
        self.fill_rows(0)
    #
    #create spreadsheet view and scrollbar
    def tree_view(self):
        self.tree = ttk.Treeview(self.main_frame, columns=("id", "entry_date_time", "receipt_date_time", "price", "vat"), show="headings")
        
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.configure(yscroll=self.scrollbar.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=30, anchor=tk.E)
        
        self.tree.heading("entry_date_time", text="Entry Date & Time")
        self.tree.column("entry_date_time", width=120, anchor=tk.E)
        
        self.tree.heading("receipt_date_time", text="Receipt Date & Time")
        self.tree.column("receipt_date_time", width=120, anchor=tk.E)
        
        self.tree.heading("price", text="Price (€)")
        self.tree.column("price", width=80, anchor=tk.E)
        
        self.tree.heading("vat", text="VAT (%)")
        self.tree.column("vat", width=40, anchor=tk.E)
    #
    #create bottom bar with page buttons and page info
    def bottom_bar(self):
        self.ribbon = tk.Frame(self)
        self.ribbon.pack(side=tk.BOTTOM)
        
        self.previous_page_b = tk.Button(self.ribbon, text="<", command=lambda: self.fill_rows(-1))
        self.previous_page_b.pack(side=tk.LEFT, padx=40, pady=6)
        
        self.page_amount = tk.Label(self.ribbon, textvariable=self.page_text)
        self.page_amount.pack(side=tk.LEFT, padx=0, pady=6)
        
        self.next_page_b = tk.Button(self.ribbon, text=">", command=lambda: self.fill_rows(1))
        self.next_page_b.pack(side=tk.LEFT, padx=40, pady=6)
    #
    #populate the spreadsheet view with rows from the database
    def fill_rows(self, direction):
        count = db.count()
        if self.page_index >= 0 and self.page_index <= (count/db.fetch_amount) and count > 0:
            #clear the view when switching pages
            for old_row in self.tree.get_children():
                self.tree.delete(old_row) 
            #
            #get next X amount of rows (specified in db_helper)
            page_max = (self.page_index * db.fetch_amount) + db.fetch_amount
            if self.page_index + direction >= 0 and page_max <= count or direction < 0 and page_max >= count:
                if self.page_index > 0:
                    self.page_index += direction
                #
            #  
            rows = db.get_rows(self.page_index)
            self.refresh_page_text(count)
            #insert rows
            for row in rows:
                row = (row[0], row[1], row[2], "%0.2f" %(row[3]), row[4])
                self.tree.insert("", tk.END, values=row)
            #
        #
    #
    #refresh bottom bar info text
    def refresh_page_text(self, count):
        temp_str = ""
        page_min = self.page_index * db.fetch_amount
        if page_min + db.fetch_amount < count:
            temp_str = str(page_min) + "/" + str(page_min + db.fetch_amount) + " of " + str(count)
        else:
            temp_str = str(page_min) + "/" + str(count) + " of " + str(count)
        self.page_text.set(temp_str)
    #
    #window close event, change button behaviour from focus to opening the window again
    def close(self):
        self.master.database_b.configure(command=self.master.new_window)
        self.destroy()
    #
#
#run main GUI
def app_main(): 
    app = Main_window()
    app.mainloop()
#
