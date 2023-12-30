from PIL import Image, ImageTk, ImageOps
import threading
import cv2
import platform, time

max_res = (4000, 4000) #hack, try big res so it scales down to largest supported res by camera

class Webcam():
    def __init__(self, master, win_size):
        self.master = master
        
        #variables
        self.cam = None
        self.thread_running = False
        self.current_frame = None
        self.previous_frame = None
        
        #get operating system
        os = platform.platform()
        
        #setting the capture source manually initializes the camera faster
        if "Windows" in os:
            self.cam = cv2.VideoCapture(0, cv2.CAP_DSHOW) #use directshow in windows
        elif "Linux" in os:
            self.cam = cv2.VideoCapture(0, cv2.CAP_V4L2) #use v4l2 in linux
        else: #mac, untested
            self.cam = cv2.VideoCapture(0) #should default to any available capture source
            #print("Other / Mac ?")
        #
        self.change_size(win_size)
    #
    #create seperate threads for getting camera frames and processing them
    def start_preview_thread(self):
        self.thread_running = True
        get_frames_thread = threading.Thread(target=self.get_preview_frame)
        get_frames_thread.start()
        
        show_frames_thread = threading.Thread(target=self.show_preview_frame)
        show_frames_thread.start()
    #
    #get new frame from cv2 camera
    def get_preview_frame(self):
        while self.thread_running:
            got_frame, frame = self.cam.read()
            if got_frame:
                self.current_frame = frame
            #
        #
    #
    #process frame: convert cv2 frame to PIL and resize it to fit application window 
    #then update main window tkinter label (seperate from image_gui refresh_image())
    def show_preview_frame(self):
        while self.thread_running:
            temp_frame = self.current_frame
            if temp_frame is not None and temp_frame is not self.previous_frame:
                
                new_size = self.master.get_size()
                
                new_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                new_frame = Image.fromarray(new_frame)
                new_frame = ImageOps.contain(new_frame, new_size, method=Image.Resampling.BICUBIC)
                new_frame = ImageTk.PhotoImage(new_frame)
                
                self.master.img_preview.configure(width=new_size[0], height=new_size[1], image=new_frame)
                self.master.img_preview.image = new_frame #hack to prevent garbage collection
                
                self.previous_frame = self.current_frame
            #
        #
    #
    #close camera object
    def close(self):
        self.thread_running = False
        self.cam.release()
    #
    #change camera resolution, or force max res if no resolution given
    def change_size(self, new_res=None):
        if not new_res:
            new_res = max_res
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, new_res[0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, new_res[1])
    #
    #shut down camera preview threads, then create a thread for capturing max res image
    def start_capture_thread(self):
        self.thread_running = False
        capture_thread = threading.Thread(target=self.capture_still)
        capture_thread.start()
    #
    #capture a max resolution image, convert cv2 img to PIL, return to image_gui
    def capture_still(self):
        self.change_size()
        time.sleep(1)
        got_frame, frame = self.cam.read()
        
        if got_frame:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
        #
        self.master.end_image_capture(img)
        #
    #
#
