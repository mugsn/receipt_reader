# Receipt Reader
-A simple receipt reader with a GUI, made in python  

-Required external packages  
&emsp;-Pillow  
&emsp;-tkinter  
&emsp;-pytesseract and tesseract ocr  
&emsp;-numpy  
&emsp;-opencv  

-Run main_app.py to launch the program

# General notes
-Works on Windows or Linux (should work on mac, but hasn't been tested)  
-Simple tkinter GUI that allows you to either load an image file, or access your webcam to take a picture  
-Taking a picture works with any generic USB camera, or a raspberry pi camera module  

-Detects data from receipts (receipt date & time, total amount (€), VAT (%))  
&emsp;-Currently only detects the highest VAT %, instead of each seperate VAT %  

-Save detected data into a database, has a simple viewer to check the database  

# GUI
-Includes a status indicator text on the bottom right  
-Load image from file system, OR  
-Take a picture  
&emsp;-Includes a preview running at lower resolution for performance reasons  
&emsp;-Once you choose to take the picture, it will use the maximum supported camera resolution  

-UI shows a preview of your loaded/captured image  
-Once an image has been loaded, "Detect Text" button becomes clickable  
&emsp;-Runs through text detection and parsing  

-Once text detection and parsing has finished, shows a pop-up window with the found information  
&emsp;-Receipt date & time, receipt total amount(€), VAT(%)  
&emsp;-Asks the user if they want to save said data to the database (Yes/No)  
&emsp;&emsp;-(Only receipt date & time are allowed to be blank)  

-Simple database view window for checking data  

# OCR aka Text detection
-Runs through preprocessing first: resize (if needed) -> grayscale -> invert black and white -> threshold -> 2d deskew (rotation)  
&emsp;-Resize image if it's less than 1000 pixels height- OR width-wise  
&emsp;-Grayscale and invert black and white, OCR prefers white text on black background  
&emsp;-Threshold the image, so dark pixels become black (0) and light pixels become white (255)  
&emsp;-Check if image is tilted, if so, straighten it  

-Another rotation check for 90 degree flips (deskew straightens the text, but image might still be sideways, etc)  
-Finally, run main tesseract text detection function  

-Parse date & time, total price and VAT from the detected text  

# Sqlite database
-When saving data, checks for database  
&emsp;-Creates a database if it doesn't exist already  
-Save date, includes checking if it's valid  
-Fetch data to fill the database view in the GUI  

# Misc coding comments
-Used threads for any operation that takes longer than a few tenths of a second to keep UI responsive  
&emsp;(Wouldn't be that big of a deal, but the UI will crash if you try to do anything while it's waiting)  
-Split the camera preview into two threads: capture frame and show frame  
&emsp;-Biggest bottleneck is capturing a frame from the camera  
&emsp;-Showing the frame is very fast, but seperating it into it's own thread as well speeds up capture, because it doesn't have to wait to take capture another frame  
-Preprocessing the image as much as possible before trying OCR drastically increases success rate  

# Further development
-Improve text parsing to find all VAT %'s and VAT amounts  
-Improve text parsing to cover a lot more variations, since every receipt seems to be formatted differently  
-Add 3d deskew into preprocessing, for correcting depth on badly shot images  
&emsp;-Corner detection, homography  
-Improve camera preview performance  
-Make a settings page for the GUI  
-Add some more indicators to the GUI, like maybe a loading bar  
