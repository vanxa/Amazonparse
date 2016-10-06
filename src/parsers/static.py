import sys
import traceback
import os
import urllib3
from bs4 import BeautifulSoup as bs
import re 
import itertools
import fileinput
from urllib import request, parse
from PIL import Image

def print_exception(msg = "Exception"):
    (trace_type, trace_val, stacktrace) = sys.exc_info()
    print(msg)
    print("-"*50)
    traceback.print_exception(trace_type,trace_val, stacktrace,limit=2, file=sys.stdout)
    print("-"*50)  
    
    
def open_url(url_root, product_id, root_folder = None, use_cache=None):
    url = url_root + product_id
    print("Creating storage directory for product " + product_id)
    if not os.path.isdir(product_id):
        os.mkdir(product_id)
    else:
        print("Directory already exists in " + os.getcwd())    
    if use_cache:
        if os.path.isfile(product_id + "/" + product_id + ".html"):
            print("Caching is on and found local copy of " + url)
            return bs(open(product_id + "/" + product_id+".html","r",encoding="UTF-8").read(), "html.parser")
    kwargs = {'retries' : 1}
    print("Opening URL " + url)
    headers = construct_headers()
    conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=headers)
    html = conn.urlopen("GET",url)
    if html.status == 200:
        print("OK")
        data = html.data.decode("UTF-8")
        if use_cache:
            print("Saving local copy of " + url)
            with open(product_id + "/" + product_id+".html", "w", encoding="UTF-8") as f:
                f.write(data)
        return bs(data, "html.parser")
    else:
        print("Could not find URL")
        return None
    #return conn.urlopen("GET",url).data.decode("UTF-8")
    
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
    num_keywords = 0
    try:
        keywords = {}
        keywords_nomixed = {}
        with open(loc, "r", encoding="UTF-8") as f:
            for line in f.readlines():
                line = line.strip()
                obj = re.search(r"longtailkeyword\s*\=\s*(.*)", line, re.IGNORECASE)
                if obj:
                    keyword = translate_quotes(obj.group(1))
                    print("Found it. Keyword is %s" % keyword )
                    if keyword == "":
                        raise Exception("No LongtailKeyword provided")
                    keywords["LongTailKeyword"] = keyword
                    keywords_nomixed["LongTailKeyword"] = keyword
                obj = re.search(r"suggestedkeyword(\d*)\s*\=\s*(.*)", line, re.IGNORECASE)
                if obj:
                    num_keywords += 1
                    index = obj.group(1)
                    keyword = translate_quotes(obj.group(2))
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
            return keywords, keywords_nomixed, num_keywords
                
    except Exception as e:
        print_exception("Exception "+ loc)
        return None,None, 0


def translate_quotes(string_):
    translation_tab = {
        "\"" : "_", 
        "\'" : "_",
        "`"  : "_"
    }
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

def write_to_file(product_id, info_struct, num_keywords, key_struct = None, add_static_descr = False):
    with open(product_id+"/info.txt", "w", encoding="UTF-8") as f:
        bullets = get_struct(info_struct, "bullets")
        brand = get_struct(info_struct, 'brand')
        descr = get_struct(info_struct,'descr')
        product = get_struct(info_struct,'product')
        details = get_struct(info_struct,'details')
        tech_details = get_struct(info_struct,'tech_details')
        price = get_struct(info_struct,'price')
        f.write("Title:\n")
        new_line(f,1)
        f.write(product + " by " + brand)
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
        if add_static_descr:
            f.write(create_static_description(key_struct["LongTailKeyword"]) + "\n")
        new_line(f,2)
        f.write("Details:\n")
        new_line(f,1)
        if details == None or len(details) == 0:
            f.write("N/A\n")
        else:
            for detail in details:
                f.write(detail + "\n")
        new_line(f,2)
        f.write("Technical Details:\n")
        new_line(f,1)
        if tech_details == None or len(tech_details) == 0:
            f.write("N/A\n")
        else:    
            for detail in tech_details:
                f.write(detail + "\n")
        new_line(f,2)
        if info_struct['UPC'] != None:
            f.write("UPC:\n" + info_struct['UPC'] + "\n")
        new_line(f,2)
        f.write("Price:")
        new_line(f,1)
        if price == None:
            f.write("N/A")
        else:
            f.write(str(price))       
        new_line(f,2)    
        if key_struct == None:
            f.write("LongTailKeyword=\nSuggestedKeyword1=\nSuggestedKeyword2=\nSuggestedKeyword3=\nSuggestedKeyword4=")
        else:
            f.write("LongTailKeyword="+key_struct["LongTailKeyword"]+"\n")
            i = 0
            while i < num_keywords:
                kword = "SuggestedKeyword"+str(i+1)
                f.write(kword+"="+key_struct[kword]+"\n")
                i += 1        
        new_line(f,2)
        
    if key_struct != None:
    # Create template
        modify_html_template(product_id, info_struct, key_struct["LongTailKeyword"])
       

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
        

def get_images(product_id, images, info_struct):
    
    print("Parsing keyword data from file")
    keywords, keywords_nomixed, num_keywords = parse_keywords(product_id+"/info.txt")
    if keywords == None or keywords_nomixed == None:
        raise Exception("No keywords provided")
    
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
    info_struct['keyword'] = longtailkword
    write_to_file(product_id, info_struct, num_keywords, key_struct=keywords_nomixed, add_static_descr=True)
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