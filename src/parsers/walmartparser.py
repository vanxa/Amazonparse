import re
import os
import optparse
import parsers.static as static

USE_CACHE = False
AUTO_OPEN_EDITOR = False
USE_DYNAMIC_TITLE = False
PRODUCT_LIST_FILENAME = "walmart.txt"
UPC_FILENAME = "UPC_walmart.txt"
WALMART_URL_ROOT = "https://www.walmart.com/ip/"


info_struct = {}

def process_product(product):
    global info_struct
    print("Processing " + product)
    try:
        html = static.save_product_page(WALMART_URL_ROOT, product, USE_CACHE)
        
        if html != None:
            print("Getting product information")
            done = parse_url_for_info(html,product)
            if not done:
                print("There was an exception raised. Exiting")
                return False
            
            if AUTO_OPEN_EDITOR:
                static.open_editor(os.path.join(os.getcwd(),product,static.TEMP_TXT))
            else:
                input("The info file has been created in %s . Press any key to continue with image download, once you're done editing the data" % product+"/"+ static.TEMP_TXT)
            
            print("Getting images from HTML")
            images = parse_url_for_images(html)
            if images == None:
                print("Something went wrong for product " + product)
                return False
            
            print("Parsing keyword data from file")
            keywords,keywords_nomixed = static.parse_keywords(product+"/"+ static.TEMP_TXT)
            if keywords == None or keywords_nomixed == None:
                raise Exception("No keywords provided")

            info_struct = static.update_and_copy_info(product, keywords = keywords_nomixed, dyn_title = USE_DYNAMIC_TITLE)        
            static.get_images(product, images, keywords)           
            static.modify_html_template(product, info_struct, keywords_nomixed["LongTailKeyword"])
            return True
        else:
            print("Skipping processing")
            return True
    except Exception as e:
        static.print_exception("Exception while processing product "+ product)
        return False


def run():
    print("Starting Walmart Parser.")
    product_list = static.parse_product_file(PRODUCT_LIST_FILENAME)
    for product in product_list:
        process_product(product.strip())
    input("Parser has finished")
    print("Goodbye!")
        
############################################# PRODUCT DETAILS ##################################################


def parse_url_for_info(html, product = "."):
    global info_struct
    try:
        info_struct['bullets'] = find_bullets(html)
        info_struct['descr'] = find_description(html)
        info_struct['product'] = find_product_name(html)
        info_struct['brand'] = find_brand(html)
        info_struct['details'] = find_details(html)
#         info_struct['tech_details'] = find_tech_details(html)
        info_struct['price'] = find_price(html)
        info_struct['UPC'] = static.find_upc_from_file(product, UPC_FILENAME)
        static.write_to_file(product+"/"+static.TEMP_TXT, info_struct)                      
        return True
    except Exception as e:
        static.print_exception()
        return False
        
 
    
def find_details(html):
    print("Finding product details")
    res = [] 
    try:
        ellipsis = html.find("div", "about-item-complete").find("section","js-product-specs").find("table")
        
#         if detail_html == None:
#             detail_html = html.find(id="detail-bullets")
#             if detail_html == None:
#                 print("No details found")
#                 return None
#             for li in detail_html.ul.find_all("li"):
#                 res[li.b.extract().getText()] = li.getText()
#         else:
        for tr in ellipsis.tbody.find_all("tr"):
            tds = tr.find_all("td")
            th = tds[0].getText().strip().replace(":","")
            res.append(th +":" + tds[1].getText().strip())
                
            
    except Exception as e:
        static.print_exception()
    res.sort()
    return res
        
def find_tech_details(html):
#     print("Finding product technical details")
#     res = {} 
#     try:
#         detail_html = html.find(id="technicalSpecifications_feature_div")
#         if detail_html == None:
#             print("No details found")
#             return None
#         for table in detail_html.find_all("table"):
#             for row in table.find_all("tr"):
#                 res[row.th.getText()] = row.td.getText()
#         return res            
#     except Exception as e:
#         static.print_exception()
#     return res
    return None

            
def find_product_name(html):
    print("Finding product name")
    try:
        return html.find("div","prod-title-section").find("h1","js-product-heading").getText().strip()
    except Exception as e:
        static.print_exception("Exception while trying to get product name")
        return None
            
def find_brand(html):
    print("Finding brand")
    try:
        return html.find("div","product-subhead").find("span",itemprop="brand").getText().strip()
    except Exception as e:
        static.print_exception("Exception while trying to get product brand ")
        return None
            
def find_bullets(html):
    print("Finding feature bullets")
    try:
        ellipsis = html.find("div", "about-item-complete").find("section","product-about").find(class_="js-ellipsis")
        bullets = [bullet.getText().strip() for bullet in ellipsis.find("ul").find_all("li")]
        return bullets
    except Exception as e:
#         static.print_exception("Exception while trying to parse feature bullets ")
        static.warn("No feature bullets were found")
        return None

def find_description(html): 
    print("Checking for product description")
    try:
        ellipsis = html.find("div", "about-item-complete").find("section","product-about").find(class_="js-ellipsis")
        ps = ellipsis.find_all("p")
        descr = ""
        for p in ps:
            if not p.has_attr("class") or "product-description-disclaimer" not in p['class']:
                if p.getText() != "":
                    try:
                        descr += p.children.__next__().strip()+"\n"
                    except Exception:
                        pass
                #else:
                # Get only first <p> tag
                 #   descr += p.getText().strip()+"\n"
                #break
        return descr
    except Exception as e:
        static.print_exception("Exception when trying to parse product description ")
        return None
    
def find_price(html):
    print("Finding item price")
    try:
        pr = html.find("div", "js-product-price").find("div","js-price-display")
        price = float(pr.getText().strip().replace("$",""))
        return round(price + price*0.17,2)
            
    except Exception as e:
        static.print_exception("Exception when trying to parse price ")
        return None   

    

def parse_url_for_images(html):
    #data = None
    #with open("test1.txt","r", encoding="UTF-8") as f:
    #    data = f.read().replace("\n","")
    print("Searching for Javascript segment that has image urls")  
    try:
        script = [scr for scr in html.find_all("script") if "imageAssets" in scr.getText()][0]
        if script:
            lines = script.getText().split("\n")
            images = [l for l in lines if "imageAssets" in l][0].strip().split("imageAssets")[1]
            if "carePlans" in images:
                images = images.split("carePlans")[0]
            images = set(img.replace("?odnHeight","") for img in re.findall("https.*?\.jpeg",images))
            return {"hiRes": images}
    
        else:
            raise Exception("No images were found!")
    except Exception as e:
        static.print_exception("Could not parse images")
        return None    
    
    
def main():
    global USE_CACHE
    global AUTO_OPEN_EDITOR
    global USE_DYNAMIC_TITLE
    parser = optparse.OptionParser('usage%prog [--cache] [--auto-open-editor]')
    parser.add_option('-c', '--cache', dest='do_cache', action="store_true", help='cache html files')
    parser.add_option('-d', '--dyn-title', dest='dyn_title', action="store_true", help='generate title dynamically using user keywords')
    parser.add_option('-a', '--auto-open-editor', action="store_true", dest='auto_edit',help='automatically open editor')
    (options, args) = parser.parse_args()
    do_cache= options.do_cache
    auto_edit = options.auto_edit
    dyn_title = options.dyn_title
    if do_cache:
        USE_CACHE = True
        print("CACHE flag is set")
    if auto_edit:
        AUTO_OPEN_EDITOR = True
        print("AUTO_OPEN flag is set")
    if dyn_title:
        USE_DYNAMIC_TITLE = True
        print("USE_DYNAMIC_TITLE flag is set")
    print("Starting with CACHE %s and AUTO_OPEN %s and USE_DYNAMIC_TITLE %s" % ( USE_CACHE, AUTO_OPEN_EDITOR, USE_DYNAMIC_TITLE))
    #test_threading()
    run()
    
if __name__ == '__main__':
    main()
