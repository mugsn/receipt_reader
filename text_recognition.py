from PIL import Image

import pytesseract
import re #regex

import numpy as np
import cv2

#grayscale -> invert -> threshold -> 2d deskew (basically just rotation)
#todo: switch to 3d deskew to correct for actual perspective
def preprocess(pil_img):
    #resize image if one of the dimensions is less then 1000
    img_size = pil_img.size
    if img_size[0] < 1000 or img_size[1] < 1000:
        pil_img = pil_img.resize((img_size[0]*2, img_size[1]*2))
    #
    #convert PIL image to cv2
    cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    #convert image to grayscale and flip black and white
    gray_img= cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
    gray_img_inverted = cv2.bitwise_not(gray_img)

    #threshold image so every dark pixel is black (0), every light pixel is white (255)
    threshold_img = cv2.threshold(gray_img_inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    #grab coordinates of all non-black pixels, then form a bounding box
    coordinates = np.column_stack(np.where(threshold_img > 0))
    
    #minAreaRect returns between -90 and 0
    angle = cv2.minAreaRect(coordinates)[-1]
    
    if angle == 0:
        #convert cv2 image back to PIL
        final_img = Image.fromarray(cv2.cvtColor(threshold_img, cv2.COLOR_BGR2RGB))
    else:
        #straighten angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        #
        #get image center and create corrected rotation matrix
        img_h, img_w, *_ = cv2_img.shape #returns (number of rows of pixels, number of columns of pixels, number of channels)
        img_center = (img_w/2, img_h/2)
        rotation_matrix = cv2.getRotationMatrix2D(img_center, angle, 1.0)

        #take sin and cos of rotation_matrix, abs to make it them positive
        cos = np.abs(rotation_matrix[0][0])
        sin = np.abs(rotation_matrix[0][1])

        #calculate new width and height
        new_w = int((img_h * cos) + (img_w * sin)) 
        new_h = int((img_h * sin) + (img_w * cos)) 
 
        #update new values to the rotation_matrix
        rotation_matrix[0][2] += (new_w/2) - img_center[0]
        rotation_matrix[1][2] += (new_h/2) - img_center[1]

        #rotate the image
        rotated_img = cv2.warpAffine(threshold_img, rotation_matrix, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)
        
        #convert cv2 image back to PIL
        final_img = Image.fromarray(cv2.cvtColor(rotated_img, cv2.COLOR_BGR2RGB))
    #
    #final_img.save("test_prepro.jpg") #DEBUG
    
    return final_img
#
#main function for the whole text detection pass
#todo: add more regex options for different formats, such as dates with "-" or "/"
#todo: if there are multiple vat values, find the vat € amount as well
def detect_text_from_img(img):
    #preprocess the image
    processed_img = preprocess(img)
    
    #try to get img_info and parse out detected rotation, may fail due to insufficient dpi
    rotate = 0
    try:
        img_info = pytesseract.image_to_osd(processed_img)
        rotate = float(re.search(r"(?<=Rotate: )\d+", img_info).group(0))
    except Exception:
        pass
    #
    #rotate image if needed
    if rotate != 0:
        processed_img = processed_img.rotate(-rotate, expand=True, fillcolor="black")
    #
    
    #detect text with tesseract ocr
    text = pytesseract.image_to_string(processed_img, lang="eng+fin", config="--psm 6 --oem 3")
    
    #print(f"\n##Raw text##\n{text}") #DEBUG
    
    #initialize result data format
    result = {"date_time": None, "price": None, "vat": None}
    
    #search for date format strings (x.x.xxxx, xx.xx.xxxx, xx.x.xxxx, x.xx.xxxx)
    date_match = re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", text)
    if date_match:
        result["date_time"] = date_match.group()
        #search for time format strings (x:xx, xx:xx, xx:xx:xx)
        time_match = re.search(r"\b\d{1,2}\:\d{2}(\:\d{2}|)\b", text)
        if time_match:
            result["date_time"] += " " + time_match.group()
        else:
            result["date_time"] += " 00:00" #add blank time
        #
    #
    #search for price keywords
    price_keywords = ["summa", "amount", "yhteensä", "yht"]
    for keyword in price_keywords:
        index = text.lower().find(keyword)
        if index != -1:
            line_start = text.rfind('\n', 0, index) + 1
            line_end = text.find('\n', index)

            #remove leading and trailing whitespaces
            price_text = text[line_start:line_end].strip()
            
            #only get digits and decimals
            price_text_cleaned = ""
            for character in price_text:
                if character.isdigit() or character == "." or character == ",":
                    price_text_cleaned += character
                #
            #
            #convert price to float
            price_float = str_to_float(price_text_cleaned)
            formatted_price = "{:.2f}".format(price_float)
            
            #apply new price value if none or higher than previous
            if not result["price"]:
                result["price"] = formatted_price
            else: 
                if formatted_price > result["price"]:
                    result["price"] = formatted_price
                #
            #
        #
    #
    #find every occurence of vat keywords in text
    vat_keywords = ["alv", "vat", "%"]
    for keyword in vat_keywords:
        position = 0
        words_found = True
        while words_found:
            index = text.lower().find(keyword, position) #find keywords starting from index(position)
            if index != -1:
                line_start = text.rfind('\n', 0, index) + 1
                line_end = text.find('\n', index)
                position = line_end

                #remove leading and trailing whitespaces
                vat_text = text[line_start:line_end].strip()
                if "%" in vat_text:
                    vat_text = text[line_start:index+1].strip() #strip everything after %
                #
                #search for vat format (xx,xx%, xx.xx%, xx%)
                vat_text_match = re.search(r"\d{1,2}(\,|\.|)\d{0,2}(\%|\ \%)", vat_text)
                if vat_text_match:
                    vat_text_with_extras = vat_text_match.group()
                    
                    #only get digits and decimals
                    vat_text_cleaned = ""
                    for character in vat_text_with_extras:
                        if character.isdigit() or character == "." or character == ",":
                            vat_text_cleaned += character
                        #
                    #
                    #convert price to float
                    vat_float = str_to_float(vat_text_cleaned)
                    formatted_vat = "{:.2f}".format(vat_float)
                    
                    #apply new vat value if none or higher than previous
                    if not result["vat"]:
                        result["vat"] = formatted_vat
                    else: 
                        if formatted_price > result["vat"]:
                            result["vat"] = formatted_vat
                        #
                    #
                #
            else:
                words_found = False
            #
        #
    #
    return result
#
#convert "," to "." so python recognizes floats
def str_to_float(str):
    if "," in str:
        str = str.replace(",", ".")
    #
    return float(str)
#
