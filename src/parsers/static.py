import sys
import traceback
import os
import urllib3
from bs4 import BeautifulSoup as bs
import re 
import itertools
import fileinput
from urllib import request
from PIL import Image
import colorama
from colorama import Fore, Back, Style


STEP_TITLE = 0
STEP_BRAND = 1
STEP_BULLETS = 2
STEP_DESCR = 3
STEP_DETAILS = 4
STEP_TECH = 5
STEP_PRICE = 6
STEP_UPC = 7

INFO_TXT = "info.txt"
TEMP_TXT = "tmp.txt"

colorama.init()

def print_exception(msg = "Exception"):
    (trace_type, trace_val, stacktrace) = sys.exc_info()
    error(msg)
    error("-"*50)
    traceback.print_exception(trace_type,trace_val, stacktrace,limit=2, file=sys.stdout)
    error("-"*50)  
    

def save_product_page(url_root, product_id, use_cache=None):
    url = url_root + product_id
    save_to = product_id + "/" + product_id + ".html"
    info("Creating storage directory for product " + product_id)
    if not os.path.isdir(product_id):
        os.mkdir(product_id)
    else:
        info("Directory already exists in " + os.getcwd())  
        refresh_directory(product_id)  
    if use_cache:
        if os.path.isfile(save_to):
            info("Caching is on and found local copy of " + url)
            return bs(open(save_to,"r",encoding="UTF-8").read(), "html.parser")
    info("Opening URL " + url)
    html = _open(url)
    if html.status == 200:
        success("OK")
        data = html.data.decode("UTF-8")
        if use_cache:
            info("Saving local copy of " + url)
            with open(save_to, "w", encoding="UTF-8") as f:
                f.write(data)
        return bs(data, "html.parser")
    else:
        error("Could not find URL")
        return None
    
# def open_url(url_root, product_id, use_cache=None):
#     url = url_root + product_id
#     save_to = product_id + "/" + product_id + ".html"
#     print("Creating storage directory for product " + product_id)
#     if not os.path.isdir(product_id):
#         os.mkdir(product_id)
#     else:
#         print("Directory already exists in " + os.getcwd())  
#         refresh_directory(product_id)  
#     if use_cache:
#         if os.path.isfile(save_to):
#             print("Caching is on and found local copy of " + url)
#             return bs(open(save_to,"r",encoding="UTF-8").read(), "html.parser")
#     print("Opening URL " + url)
#     headers = construct_headers()
#     conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=headers)
#     html = conn.urlopen("GET",url)
#     if html.status == 200:
#         print("OK")
#         data = html.data.decode("UTF-8")
#         if use_cache:
#             print("Saving local copy of " + url)
#             with open(save_to, "w", encoding="UTF-8") as f:
#                 f.write(data)
#         return bs(data, "html.parser")
#     else:
#         print("Could not find URL")
#         return None

def open_aux_page(url):  
    html = _open(url)
    if html.status == 200:
        data = html.data.decode("UTF-8")
        return bs(data, "html.parser")
    return None
  
def _open(url):
    print("Opening URL " + url)
    headers = construct_headers()
    conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=headers)
    return conn.urlopen("GET",url)
  
  
def refresh_directory(product_id):
    print("Refreshing directory by removing old files")
    for root, dirs, files in os.walk(product_id):
        for current_file in files:
            exts = ('.png', '.jpg', ".txt")
            if any(current_file.lower().endswith(ext) for ext in exts):
                print("Removing %s" % os.path.join(root,current_file))
                os.remove(os.path.join(root, current_file))
    
def construct_headers():
    headers = {}
    headers['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    headers["Accept-Encoding"] = "gzip, deflate, sdch,br"
    headers["Accept-Language"] = "en-US, en;q=0.8"
    headers["DNT"] = "1"
    headers["Upgrade-Insecure-Requests"] = "1"
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36"
    return headers


def get_html_template():
    try:
        return bs(open("template.html","r",encoding="UTF-8").read(), "html.parser")
    except Exception as e:
        print_exception("Failed to open HTML template")
        
def modify_html_template(product_id, info_struct, longtail_key = None):
    html = get_html_template()
    if html == None:
        print("Failed to retrieve template. Cannot proceed")
        raise Exception("No template")
    
    if longtail_key == None:
        print("No keyword received. Template will not be complete")
        
    bullets = info_struct['bullets']
    product = info_struct['product']
    descr = info_struct['descr']
    if bullets == None or descr == None or product == None:
        print("Some required data is missing from info.txt. Cannot proceed")
        raise Exception("No information")
    
    try:
        title_tag = html.find("span", id="title")
        title_tag.string= product
        
        descr_tag = html.find("p",id="productDescription")
        descr_tag.string = descr
        
        if longtail_key != None:
            policy_key = html.find("span", id="longtailKeyword-shippingPolicy")
            policy_key.string = longtail_key
            policy_key = html.find("span", id="longtailKeyword-returnPolicy")
            policy_key.string = longtail_key
            
            list_tag = html.find("ul", id="bulletpoints")
            for bullet in bullets:
                li = html.new_tag("li")
                li.string = bullet
                list_tag.append(li)
                
        with open(product_id+"/info.txt", "ab") as f:
            f.write(html.prettify(encoding="UTF-8",))
        
        
    except Exception as e:
        print_exception("Failed to modify HTML template")
        
def parse_keywords(loc):
    try:
        keywords = {}
        keywords_nomixed = {}
        found_all = False
        with open(loc, "r", encoding="UTF-8") as f:
            lines = f.readlines()
            lines.reverse()
            for line in lines:
                line = line.strip()
                obj = re.search(r"longtailkeyword\s*\=\s*(.*)", line, re.IGNORECASE)
                if obj:
                    keyword = translate(obj.group(1))
                    print("Found it. Keyword is %s" % keyword )
                    if keyword == "":
                        raise Exception("No LongtailKeyword provided")
                    keywords["LongTailKeyword"] = keyword
                    keywords_nomixed["LongTailKeyword"] = keyword
                    found_all = True
                if found_all:
                    break
                obj = re.search(r"suggestedkeyword(\d*)\s*\=\s*(.*)", line, re.IGNORECASE)
                if obj:
                    index = obj.group(1)
                    keyword = translate(obj.group(2))
                    if keyword == "":
                        #raise Exception("No SuggestedKeyword provided")
                        continue
                    print("Found SuggestedKeyword%s = %s" %(index, keyword))
                    try:
                        keywords["SuggestedKeyword"] += [keyword]
                    except KeyError:
                        keywords["SuggestedKeyword"] = [keyword]
                    keywords_nomixed["SuggestedKeyword"+str(index)] = keyword
            print("Done")
            if len(keywords.keys()) == 0:
                print("No keywords were found in file. Did you forget to add keywords?")
                return None, None, 0
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],2)))
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],3)))
            return keywords, keywords_nomixed
                
    except Exception as e:
        print_exception("Exception "+ loc)
        return None,None, 0

def update_and_copy_info(product_id, keywords = None, dyn_title = False):
    step = -1
    title = ""
    brand = ""
    bullets = []
    descr = ""
    details = []
    tech = []
    price = 0.0
    create_policy = False
    upc = ""   
    tmp_path = product_id+"/"+TEMP_TXT
    info_path = product_id+"/"+INFO_TXT
    try:
        tmp_f = open(tmp_path, "r", encoding="UTF-8")
        lines = tmp_f.readlines()
        lines[0] = lines[0].replace("\ufeff","") # Remove BOM
        with open(info_path, "w", encoding="UTF-8") as info_f:
            for line in lines:
                line2 = line.replace("\n","")
#                 if line2 != "":
#                     continue
                for case in switch(line2.replace(" ","").replace(":","").lower()):                  
                    if case(""):
                        if step == STEP_DESCR and create_policy:
                            info_f.write(create_static_description(keywords["LongTailKeyword"]) + "\n")
                            create_policy= False
                        pass
                    elif case("title"):
                        step = STEP_TITLE
                    elif case("brand"):
                        step = STEP_BRAND
                    elif case("bulletpoints"):
                        step = STEP_BULLETS
                    elif case("productdescription"):
                        step = STEP_DESCR
                    elif case("details"):
                        step = STEP_DETAILS
                    elif case("technicaldetails"):
                        step = STEP_TECH
                    elif case("upc"):
                        step = STEP_UPC
                    elif case("price"):
                        step = STEP_PRICE
                       
                    elif case():        
                        for inner_case in switch(step):
                            if inner_case(STEP_TITLE):
                                if dyn_title and keywords != None:
                                    title = create_dynamic_title(keywords)
                                    line = title
                                else:
                                    title = line2
                                step = -1
                            elif inner_case(STEP_BRAND):
                                brand = line2
                                step = -1
                            elif inner_case(STEP_DESCR):
                                descr += line2 + "\n"
                                if keywords != None and "LongTailKeyword" in keywords.keys() and not create_policy:
                                    #descr += create_static_description(keywords["LongTailKeyword"] + "\n") # Add this line to template as well
                                    create_policy = True
                            elif inner_case(STEP_BULLETS):
                                bullets.append(line2)
                            elif inner_case(STEP_DETAILS):
                                details.append(line2)
                            elif inner_case(STEP_TECH):
                                tech.append(line2)
                            elif inner_case(STEP_UPC):
                                upc = line2
                                step = -1
                            elif inner_case(STEP_PRICE):
                                try:
                                    price = float(line2)
                                except Exception:
                                    print("Illegal price value! Setting to N/A")
                                    price="N/A"
                                step = -1
                        
                info_f.write(line)        
        if len(bullets) == 0:
            raise Exception("No bullets section was found. Could not locate 'Bulletpoints:' header")        
        if descr == "":
            raise Exception("No description section was found. Could not locate 'Product Description:' header")
        if title == "":
            raise Exception("No title section was found. Could not locate 'Title:' header")
        if brand == "":
            raise Exception("No brand section was found. Could not locate 'Brand:' header")
        tmp_f.close()
        info_f.close()
        
        # Remove temporary dir
        os.remove(tmp_path)
        
        return {'bullets': bullets,
                'descr' : descr,
                'product' : title,
                'brand' : brand,
                'details' : details,
                'tech_details' : tech,
                'price' : price,
                'UPC' : upc}    
                
                    
                    
    except Exception as e:
        print_exception()
        return None

def create_dynamic_title(keywords):
    try:
        title = keywords["LongTailKeyword"] + " "
        i = 0
        while i<len(keywords.keys()) - 1:
            title = title + keywords["SuggestedKeyword"+str(i+1)] + " "
            i += 1
        return title.strip()
    except Exception as e:
        print_exception("Could not create dynamic title! Most probably LongTailKeyword is missing")
        return "NO TITLE"
    
    
def translate(string_):
    intab="'/ \"\'\\"
    outtab="______"
    translation_tab = str.maketrans(intab, outtab) 
    return string_.translate(translation_tab)

def open_editor(doclocation):
    try:
        if sys.platform == 'win32':
            os.system(doclocation)
        else:
            os.system("%s %s" % (os.getenv("EDITOR"), doclocation))
    except Exception as e:
        print_exception()
        return False
    return True
    
def create_static_description(keyword):
    return "We only ship to the lower 48 states and do not combine shipping or offer local pickup. I do NOT ship to PO Boxes or APO'S. We offer a 30 days return policy on this " + keyword

def get_struct(info_struct, key):
    if key in info_struct.keys():
        return info_struct[key]
    else:
        return None    

def write_to_file(txt_location, info_struct):
    with open(txt_location, "w", encoding="UTF-8") as f:
        bullets = get_struct(info_struct, "bullets")
        brand = get_struct(info_struct, 'brand')
        descr = get_struct(info_struct,'descr')
        product = get_struct(info_struct,'product')
        details = get_struct(info_struct,'details')
        tech_details = get_struct(info_struct,'tech_details')
        price = get_struct(info_struct,'price')
        f.write("Title:\n")
        new_line(f,1)
#         f.write(product + " by " + brand)
        f.write(product)
        new_line(f,2)
        f.write("Brand:\n")
        new_line(f,1)
        f.write(brand)
        new_line(f,2)
        f.write("Bulletpoints:\n")
        new_line(f,1)
        if bullets == None or len(bullets) == 0:
            f.write("N/A\n")
        else:
            for bullet in bullets:
                f.write(bullet + "\n")
        new_line(f,2)
        f.write("Product Description:\n")
        new_line(f,1)
        if descr == None:
            f.write("N/A\n")
        else:
            f.write(descr + "\n")
        new_line(f,2)
        f.write("Details:\n")
        new_line(f,1)
        if details == None or len(details) == 0:
            f.write("N/A\n")
        else:
            for detail in details:
                f.write(detail + "\n")
            f.write("Brand Name: "+ brand + "\n")
        new_line(f,2)
        f.write("Technical Details:\n")
        new_line(f,1)
        if tech_details == None or len(tech_details) == 0:
            f.write("N/A\n")
        else:    
            for detail in tech_details:
                f.write(detail + "\n")
        new_line(f,2)
        if info_struct['UPC'] != None or info_struct['UPC'] == "":
            f.write("UPC:\n" + info_struct['UPC'] + "\n")
        new_line(f,2)
        f.write("Price:")
        new_line(f,1)
        if price == None:
            f.write("N/A")
        else:
            f.write(str(price))       
        new_line(f,2)    
        f.write("LongTailKeyword=\nSuggestedKeyword1=\nSuggestedKeyword2=\nSuggestedKeyword3=\nSuggestedKeyword4=")
        new_line(f,2)
       

def new_line(f, numlines=1):
    f.write("\n"*numlines)  
    
def find_upc_from_file(product_id, filename):
    try:
        upc = None
        found = False
        for line in fileinput.input(filename, inplace=True):
            if line != "":
                split = line.split(":")
                if len(split) > 1 and split[1].replace("\n","") == "" and not found:
                    upc = split[0]
                    sys.stdout.write(split[0]+":"+product_id+"\n")
                    found = True
                else:
                    sys.stdout.write(line)
        return upc          

    except Exception as e:
        print_exception("No UPC file present, skipping")
        return None
    
def parse_product_file(filename):
    with open(filename,"r") as f:
        product_list = [line for line in f.read().split("\n") if line != ""]
    return product_list
        

def get_images(product_id, images, keywords): 
    a = 0
    print("Got " + str(images.keys()) + " keys")
    keys = images.keys()
    size = None
    if "hiRes" in keys:
        size = "hiRes"
    elif "large" in keys:
        size = "large"
    elif "medium" in keys:
        size = "medium"
    elif "thumb" in keys:
        size = "thumb"
    print("Getting %s size images" % size)
    for item in images[size]:
        print("Saving %s to temporary location %s" % ( item, product_id+"/"+str(a)+".jpg") )
        request.urlretrieve(item, product_id+"/"+str(a)+".jpg")
        a += 1
    print("Done. Resizing and renaming images.")
    img_count = a
    a = 0
    longtailkword = keywords["LongTailKeyword"]
    if longtailkword == "":
        raise Exception("No keyword supplied")
    while a < img_count:
        name = longtailkword
        if a >= len(keywords["SuggestedKeyword"]):
            print("There are more images saved than keywords! Will set the name to %s%d" %(name, a))
            name += str(a)
        else:
            kword = keywords["SuggestedKeyword"][a]
            if isinstance(kword, str):
                name += " " + kword
            elif isinstance(kword, tuple):
                name += " " + kword[0] + " "+ kword[1]
            else:
                print("Was expecting either string or tuple, got %s " % str(type(kword)))    
        im = Image.open(product_id+"/"+str(a)+".jpg")
        size = min(im.size)
        if size < 500:
            print("Resizing image to 500x500")
            im = im.resize((500,500))
        elif size > 900 and size < 1500:
            print("Resizing image to 1500x1500")
            im = im.resize((1500,1500))
        print("Saving image to %s.jpg" % (name))
        try:
            im.save(product_id+"/"+name+".jpg")
            os.remove(product_id+"/"+str(a)+".jpg")
        except Exception as e:
            print_exception("Exception")
        a += 1
        
# This class provides the functionality we want. You only need to look at
# this if you want to know how this works. It only needs to be defined
# once, no need to muck around with its internals.
class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration
    
    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args: # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False

def warn(msg):
    print(Fore.YELLOW + msg + Style.RESET_ALL)

def error(msg):
    print(Fore.RED + msg + Style.RESET_ALL)
    
def success(msg):
    print(Fore.GREEN + msg + Style.RESET_ALL)
        
def info(msg):
    print(msg)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[34m'
    OKGREEN = '\033[32m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'