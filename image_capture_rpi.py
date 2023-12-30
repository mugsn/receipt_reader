from PIL import Image, ImageTk, ImageOps
import threading
import cv2
from picamera2 import Picamera2

#resolutions used for camera module v2
max_res = (1640, 1232)
preview_res = (640, 480)

#slow opencv embedded preview, or fast, but seperate picamera2 qt window
use_embedded_preview = True 

#this script is used just for raspberry pi cameras
#could also maybe use "sudo modprobe bcm2835-v4l2"
#to enable raspberry pi camera as a generic usb camera, to use the other script
#but requires sudo
class Webcam():
    def __init__(self, master, win_size):
        self.master = master
        
        #variables
        self.cam = None
        self.thread_running = False
        self.current_frame = None
        self.previous_frame = None
        
        #initialize picamera2
        self.cam = Picamera2()
        
        #configure preview and capture resolutions
        self.config = self.cam.create_preview_configuration(
        main={"size": max_res}, 
        lores={"size": preview_res},
        display="lores")
        
        #set camera configuration
        self.cam.configure(self.config)
        
        #start the camera
        if use_embedded_preview:
            self.cam.start()
        #
    #
    #create seperate threads for getting camera frames and processing them
    def start_preview_thread(self):
        if use_embedded_preview:
            self.thread_running = True
            
            get_frames_thread = threading.Thread(target=self.get_preview_frame)
            get_frames_thread.start()
            
            show_frames_thread = threading.Thread(target=self.show_preview_frame)
            show_frames_thread.start()
        else:
            self.cam.start_preview(Preview.QTGL)
            self.cam.start()
        #
    #
    #get new frame from cv2 camera
    #*way slower than the picamera2 library qt previews, but those can't be embedded
    def get_preview_frame(self):
        while self.thread_running:
            frame = self.cam.capture_array("lores")
            self.current_frame = frame
        #
    #
    #process frame: convert cv2 frame to PIL and resize it to fit application window 
    #then update main window tkinter label (seperate from image_gui refresh_image())
    def show_preview_frame(self):
        while self.thread_running:
            temp_frame = self.current_frame
            if temp_frame is not None and temp_frame is not self.previous_frame:
                
                new_size = self.master.get_size()
                
                new_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_YUV420p2RGB)
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
        self.cam.close()
    #
    #shut down camera preview threads, then create a thread for capturing max res image
    def start_capture_thread(self):
        self.thread_running = False
        capture_thread = threading.Thread(target=self.capture_still)
        capture_thread.start()
    #
    #capture a max resolution image, convert cv2 img to PIL, return to image_gui
    def capture_still(self):
        frame = self.cam.capture_array("main")
        
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        
        self.master.end_image_capture(img)
        #
    #
#
