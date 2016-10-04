import urllib3
from urllib import request, parse
import re
import os
import sys
from bs4 import BeautifulSoup as bs
import optparse
from PIL import Image
import itertools
import traceback

USE_CACHE = False
AUTO_OPEN_EDITOR = False

info_struct = {}

def open_url(asin, use_cache=None):
    url = "https://www.amazon.com/gp/product/" + asin
    print("Creating storage directory for product " + asin)
    if not os.path.isdir(asin):
        os.mkdir(asin)
    else:
        print("Directory already exists in " + os.getcwd())    
    if USE_CACHE or use_cache != None:
        if os.path.isfile(asin + "/" + asin + ".html"):
            print("Caching is on and found local copy of " + url)
            return bs(open(asin + "/" + asin+".html","r",encoding="UTF-8").read(), "html.parser")
    kwargs = {'retries' : 1}
    print("Opening URL " + url)
    headers = construct_headers()
    conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=headers)
    html = conn.urlopen("GET",url)
    if html.status == 200:
        print("OK")
        data = html.data.decode("UTF-8")
        if USE_CACHE:
            print("Saving local copy of " + url)
            with open(asin + "/" + asin+".html", "w", encoding="UTF-8") as f:
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
  
def process_asin(asin):
    global info_struct
    print("Processing " + asin)
    try:
        html = open_url(asin)
        if html != None:
            print("Getting product information")
#             done = False
#             if os.path.isfile(asin+"/info.txt"):
#                 while True:
#                     q = input("Info file already exists in %s. Re-process the information (y/N/q)? ").lower()
#                     if q == "y":
#                         done = parse_url_for_info(html, asin)
#                         break
#                     elif q == "" or q == None or q == "n":
#                         done = True
#                         break
#                     elif q == "q":
#                         print("Quitting")
#                         return False
#             
#             else:
            done = parse_url_for_info(html,asin)
            if not done:
                print("There was an exception raised. Exiting")
                return False
            
            if AUTO_OPEN_EDITOR:
                open_editor(os.path.join(os.getcwd(),asin,"info.txt"))
            else:
                input("The info file has been created in %s . Press any key to continue with image download, once you're done editing the data" % asin+"/info.txt")
            
            print("Parsing keyword data from file")
            print("Getting images")
            keywords, keywords_nomixed = parse_keywords(asin+"/info.txt")
            if keywords == None or keywords_nomixed == None:
                raise Exception("No keywords provided")
            images = parse_url_for_images(html)
            if images == None:
                print("Something went wrong for asin " + asin)
                return False
           
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
                print("Saving %s to temporary location %s" % ( item, asin+"/"+str(a)+".jpg") )
                request.urlretrieve(item, asin+"/"+str(a)+".jpg")
                a += 1
            print("Done. Resizing and renaming images.")
            img_count = a
            a = 0
            longtailkword = keywords["LongTailKeyword"]
            if longtailkword == "":
                raise Exception("No keyword supplied")
            info_struct['keyword'] = longtailkword
            write_to_file(asin, key_struct=keywords_nomixed, add_static_descr=True)
            while a < img_count:
                name = longtailkword
                if a > len(keywords["SuggestedKeyword"]):
                    print("There are more images saved than keywords! Will set the name to %s%d" %(name, a))
                    name += str(a)
                else:
                    kword = keywords["SuggestedKeyword"][a]
                    if isinstance(kword, str):
                        name += " " + re.escape(kword)
                    elif isinstance(kword, tuple):
                        name += " " + re.escape(kword[0]) + " "+ re.escape(kword[1])
                    else:
                        print("Was expecting either string or tuple, got %s " % str(type(kword)))    
                im = Image.open(asin+"/"+str(a)+".jpg")
                size = min(im.size)
                if size < 500:
                    print("Resizing image to 500x500")
                    im = im.resize((500,500))
                elif size > 900 and size < 1500:
                    print("Resizing image to 1500x1500")
                    im = im.resize((1500,1500))
                print("Saving image to %s.jpg" % (name))
                try:
                    im.save(asin+"/"+name+".jpg")
                    os.remove(asin+"/"+str(a)+".jpg")
                except Exception as e:
                    print_exception("Exception")
                a += 1
            return True
        else:
            print("Skipping processing")
            return True
    except Exception as e:
        print_exception("Exception while processing asin "+ asin)
        return False

def get_html_template():
    try:
        return bs(open("template.html","r",encoding="UTF-8").read(), "html.parser")
    except Exception as e:
        print_exception("Failed to open HTML template")
        
def modify_html_template(asin, longtail_key = None):
    global info_struct
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
                
        with open(asin+"/info.txt", "ab") as f:
            f.write(html.prettify(encoding="UTF-8",))
        
        
    except Exception as e:
        print_exception("Failed to modify HTML template")
        
def parse_keywords(loc):
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
                return None, None
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],2)))
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],3)))
            return keywords, keywords_nomixed
                
    except Exception as e:
        print_exception("Exception "+ loc)
        return None,None


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

def run():
    print("Starting AZParser.")
    asin_list = parse_asin_file()
    for asin in asin_list:
        process_asin(asin)
    input("Parser has finished")
    print("Goodbye!")
        
############################################# PRODUCT DETAILS ##################################################


def parse_url_for_info(html, asin = "."):
    global info_struct
    try:
        info_struct['bullets'] = find_bullets(html)
        info_struct['descr'] = find_description(html)
        info_struct['product'] = find_product_name(html)
        info_struct['brand'] = find_brand(html)
        info_struct['details'] = find_details(html)
        info_struct['tech_details'] = find_tech_details(html)
        info_struct['price'] = find_price(html)
        info_struct['UPC'] = find_upc_from_file(asin)
        write_to_file(asin)                      
        return True
    except Exception as e:
        print_exception()
        return False
        
def find_upc_from_file(asin):
    try:
        with open("UPC.txt","r") as f:
            datalines = f.read().split("\n")
            for line in datalines:
                if line != "" and asin in line:
                    try:
                        return line.split(":")[0].strip() # Assuming line format UPC : ASIN   
                    except Exception as e:
                        print_exception("Could not parse UPC file")
                        return None
    except Exception as e:
        print_exception("No UPC file present, skipping")
        return None
    
def write_to_file(asin, key_struct = None, add_static_descr = False):
    global info_struct
    with open(asin+"/info.txt", "w", encoding="UTF-8") as f:
        bullets = info_struct['bullets']
        brand = info_struct['brand']
        descr = info_struct['descr']
        product = info_struct['product']
        details = info_struct['details']
        tech_details = info_struct['tech_details']
        price = info_struct['price']
        f.write("Title:\n"+product + " by " + brand + "\n")
        new_line(f,1)
        f.write("Bulletpoints:")
        new_line(f,1)
        if bullets == None or len(bullets) == 0:
            f.write("N/A\n")
        else:
            for bullet in bullets:
                f.write(bullet + "\n")
        new_line(f,2)
        f.write("Product Description:")
        new_line(f,1)
        if descr == None:
            f.write("N/A\n")
        else:
            f.write(descr + "\n")
        if add_static_descr:
            f.write(create_static_description(key_struct["LongTailKeyword"]) + "\n")
        new_line(f,2)
        f.write("Details:")
        new_line(f,1)
        if details == None or len(details.keys()) == 0:
            f.write("N/A\n")
        else:
            for key in details.keys():
                f.write(key + " : " + details[key] + "\n")
        if info_struct['UPC'] != None:
            f.write("UPC : " + info_struct['UPC'] + "\n")
        new_line(f,2)
        f.write("Technical Details:")
        new_line(f,1)
        if tech_details == None or len(tech_details.keys()) == 0:
            f.write("N/A\n")
        else:    
            for key in tech_details.keys():
                f.write(key + " : " + tech_details[key] + "\n")
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
            for k in key_struct.keys():
                if k == "LongTailKeyword":
                    f.write("LongTailKeyword="+key_struct[k]+"\n")
                else:
                    f.write(k+"="+key_struct[k]+"\n")
        new_line(f,2)
        
    if key_struct != None:
    # Create template
        modify_html_template(asin, key_struct["LongTailKeyword"])
       

def new_line(f, numlines=1):
    f.write("\n"*numlines)       
        
def find_details(html):
    print("Finding product details")
    res = {} 
    try:
        detail_html = html.find(id="prodDetails")
        if detail_html == None:
            detail_html = html.find(id="detail-bullets")
            if detail_html == None:
                print("No details found")
                return None
            for li in detail_html.ul.find_all("li"):
                res[li.b.extract().getText()] = li.getText()
        else:
            for tr in detail_html.table.find_all("tr"):
                th = tr.th.getText().strip()
                if th.replace(" ","").lower() == "customerreviews":
                    res[th] = tr.td.br.getText().strip()
                else:
                    res[th] = tr.td.getText().strip()
                
            
    except Exception as e:
        print_exception()
    return res
        
def find_tech_details(html):
    print("Finding product technical details")
    res = {} 
    try:
        detail_html = html.find(id="technicalSpecifications_feature_div")
        if detail_html == None:
            print("No details found")
            return None
        for table in detail_html.find_all("table"):
            for row in table.find_all("tr"):
                res[row.th.getText()] = row.td.getText()
        return res            
    except Exception as e:
        print_exception()
    return res

            
def find_product_name(html):
    print("Finding product name")
    try:
        return html.find(id="productTitle").getText().strip()
    except Exception as e:
        print_exception("Exception while trying to get product name")
        return None
            
def find_brand(html):
    print("Finding brand")
    try:
        return html.find(id="brand").getText().strip()
    except Exception as e:
        print_exception("Exception while trying to get product brand ")
        return None
            
def find_bullets(html):
    print("Finding feature bullets")
    bullets_id = "feature-bullets"
    if html.find(id=bullets_id) == None:
        bullets_id = bullets_id+"-btf"
        if html.find(id=bullets_id)  == None:
            print("No bullets were found")
            return None
    try:
        bullets = [bullet.getText().strip() for bullet in html.find(id=bullets_id).find_all("li") if (bullet.attrs == {} or "replacementPartsFitmentBullet" not in bullet.attrs['id'])]
        return bullets
    except Exception as e:
        print_exception("Exception while trying to parse feature bullets ")
        return None

def find_description(html):
    print("Checking for product description")
    prod__iframe = [framescript.getText() for framescript in html.find_all("script") if re.search(r"var iframeContent",framescript.getText())]
    product_html = None
    if len(prod__iframe) == 0:
        print("Product Description iFrame was not found!")
        return None
    else:
        obj = re.search(r"var iframeContent\s*=\s(.*?);",prod__iframe[0])
        if obj:
            try:
                product_html = bs(parse.unquote(obj.group(1)), "html.parser")
                return product_html.find(class_="productDescriptionWrapper").getText().replace("\n", "").strip()
            except Exception as e:
                print_exception("Exception when trying to parse product description ")
                return None
        else:
            return None
    
def find_price(html):
    print("Finding item price")
    try:
        tr = html.find("div", id="price").find("table").find("tr") # First element
        if "price" in tr.find("td").getText().lower():
            price = float(tr.find_all("td")[1].span.getText().strip().replace("\n","").replace("$",""))
            return round(price + price*0.17,2)
            
    except Exception as e:
        print_exception("Exception when trying to parse price ")
        return None   

    

def parse_url_for_images(html):
    #data = None
    #with open("test1.txt","r", encoding="UTF-8") as f:
    #    data = f.read().replace("\n","")
    print("Searching for Javascript segment that has image urls")  
    obj = None
    for script in html.find_all("script"):
        obj = re.search(r"P.when\(\'A\'\).register\(\"ImageBlockATF.*?colorImages.*?initial[\'\"]*?.*?(\[\{.*?\]\}).*?colorToAsin",script.getText().replace("\n",""))
        if obj != None:
            break
    if obj == None:
        print("Something went wrong. No such segment exists")
        return
    data = obj.group()
    obj = re.search(r"(\[\{.*\]\})",data)
    if obj == None:
        print("Something went wrong. No such segment exists")
        return 
    print("Found segment")
    i = re.sub(r"[\[\]\{\}]", "", obj.group(1))
    print("Splitting")
    lst  = [re.sub(r"[\'\"]","", item) for item in i.split("\",\"")]
    #if len(lst) == 0:
    #    print("something went wrong")
    images = {}
    print("Gathering images by type")
    for item in lst:
        item = item.replace("\"","").replace("'","")
        #print(item)
        obj = re.search(r"(.*)\:(http.*)", item)
        if obj != None:
            #print("For type " + obj.group(1) + " URL is " + obj.group(2))
   
            try:
                images[obj.group(1)] += [obj.group(2)]
            except KeyError:
                images[obj.group(1)] = [obj.group(2)]
    print("Done")
    return images
    
def print_exception(msg = "Exception"):
    (trace_type, trace_val, stacktrace) = sys.exc_info()
    print(msg)
    print("-"*50)
    traceback.print_exception(trace_type,trace_val, stacktrace,limit=2, file=sys.stdout)
    print("-"*50)    
    
def parse_asin_file():
    with open("asin.txt","r") as f:
        asin_list = [line for line in f.read().split("\n") if line != ""]
    return asin_list
        

def main():
    global USE_CACHE
    global AUTO_OPEN_EDITOR
    parser = optparse.OptionParser('usage%prog [--cache] [--auto-open-editor]')
    parser.add_option('-c', '--cache', dest='do_cache', action="store_true", help='cache html files')
    parser.add_option('-a', '--auto-open-editor', action="store_true", dest='auto_edit',help='automatically open editor')
    (options, args) = parser.parse_args()
    do_cache= options.do_cache
    auto_edit = options.auto_edit
    if do_cache:
        USE_CACHE = True
        print("CACHE flag is set")
    if auto_edit:
        AUTO_OPEN_EDITOR = True
        print("AUTO_OPEN flag is set")
    print("Starting with CACHE %s and AUTO_EDIT %s" % ( USE_CACHE, AUTO_OPEN_EDITOR))
    #test_threading()
    run()
    
if __name__ == '__main__':
    main()
    

        