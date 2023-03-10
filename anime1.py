import re
import os
import pathlib
from http.cookiejar import MozillaCookieJar
from fractions import Fraction
import sys
from fake_useragent import UserAgent
import shutil
import bs4 as bs
import requests
import traceback
# import re
import regex


import unicodedata

# https://stackoverflow.com/a/4703508
numeric_const_pattern = '[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?'
rx = regex.compile(numeric_const_pattern, re.VERBOSE)

ptn = r'\p{Han}+'

rx2 = regex.compile(r'\p{Han}+')

current_state = "" # "https://anime1.me/17173"
dict_urls = {}
last_selection = None

def print_nicely(arr2d_w_chinese_char):
    arr2d_w_chinese_char = [[unicodedata.normalize('NFKC', str(x)) for x in y] for y in arr2d_w_chinese_char]
    def get_length(str_in):
        return len(str(str_in)) + len(list("".join(rx2.findall(str(str_in)))))
    
    lengths = [0 for x in arr2d_w_chinese_char[0]]
    for elem in arr2d_w_chinese_char:
        lengths = [max(get_length(x), length) for x, length in zip(elem, lengths)]
    
    for elem in arr2d_w_chinese_char:
        for subelem, length in zip(elem, lengths):
            print(subelem, end="")
            print(" "*(length-get_length(subelem)), end="")
            print("", end="\t")
        print()

def parseCookieFile(cookiefile): # https://stackoverflow.com/a/54659484
    """Parse a cookies.txt file and return a dictionary of key value pairs
    compatible with requests."""

    cookies = {}
    with open (cookiefile, 'r') as fp:
        for line in fp:
            if not re.match(r'^\#', line):
                lineFields = line.strip().split('\t')
                if len(lineFields)>5:
                    cookies[lineFields[5]] = lineFields[6]
                    
    cstring = "; ".join([str(x)+"="+str(y) for x,y in cookies.items()]) # https://stackoverflow.com/a/30719818
    return cstring

def gen_UA_header():
    user_agent_string = UserAgent().random # https://stackoverflow.com/a/27652558
    headers = {'User-Agent': user_agent_string}
    return headers

def get_soup(url, headers):
    page = requests.get(url, headers=headers)   
    assert page.status_code == 200
    soup = bs.BeautifulSoup(page.text, 'lxml')
    return soup

def make_selection(dict_urls):
    global last_selection
    presscode = 1
    
    presscode_lookup_keys = {}
    maxlength = max(len(str(k)) for k in dict_urls)
    print(max([len(str(k)) for k in dict_urls if k.replace('.','',1).isdigit()]+[1]), len(str(len(dict_urls))), 1+len(str(len(list(k for k in dict_urls if not k.replace('.','',1).isdigit())))))
    maxkeylength = max(max([len(str(k)) for k in dict_urls if k.replace('.','',1).isdigit()]+[1]), len(str(len(dict_urls))), 1+len(str(len(list(k for k in dict_urls if not k.replace('.','',1).isdigit())))))
    for k,v in dict_urls.items():
        if k.replace('.','',1).isdigit():
            presscode = k
        else:
            if float(presscode) > 0:
                # not yet enter negative land
                presscode = -1
            else:
                presscode -= 1
        
        presscode_lookup_keys[str(presscode)] = k
        print("[{}] => {}: {}".format(str(presscode).rjust(maxkeylength, " "), str(k).rjust(maxlength, " "),v[1]))
    if len(dict_urls) > 1:
        selection = input("[{}]: ".format("".rjust(maxkeylength, "?")))
        if selection in presscode_lookup_keys:
            last_selection = list(dict_urls.keys()).index(presscode_lookup_keys[selection])
            current_state = "https://anime1.me/{}".format(dict_urls[presscode_lookup_keys[selection]][0])
            return current_state
        else:
            last_selection = None
            print("Invalid selection")
            current_state = ""
            return current_state
    else:
        last_selection = list(dict_urls.keys()).index(list(dict_urls.keys())[0])
        current_state = "https://anime1.me/{}".format(dict_urls[list(dict_urls.keys())[0]][0])
        return current_state



while True:
    if dict_urls:
        print("SELECTION: s:select again")
    if isinstance(last_selection, int):
        print("PLAYBACK: ", end="")
        
        commas = ""
        
        if last_selection-1 >= 0:
            print(commas, end="")
            commas = ", "
            print("<:previous", end="")
        
        print(commas, end="")
        commas = ", "
        print(".:replay", end="")
        
        if last_selection+1 < len(dict_urls):
            print(commas, end="")
            commas = ", "
            print(">:next", end="")
    print()
    current_state = input("q:search, c[]:category, v[]:video, or URL >> ")

    try:
        while True:

            if "://" in current_state and current_state.split("://", 1)[1].replace("anime1.me/","").isdigit(): # https://anime1.me/17173
            
                headers = gen_UA_header()
                soup = get_soup(current_state, headers)
                json_content = requests.utils.unquote(soup.select("article")[0].select("video")[0]["data-apireq"])
                
                data = {'d':json_content}
                print(data)
                try:
                    os.remove("cookies.txt")
                except:
                    pass
                cookiesFile = str(pathlib.Path(__file__).parent.absolute() / "cookies.txt")  # Places "cookies.txt" next to the script file.
                cj = MozillaCookieJar(cookiesFile) # https://stackoverflow.com/a/62112043
                
                with requests.Session() as s:
                    s.cookies = cj
                    
                    resp = s.post('https://v.anime1.me/api', data=data, headers=headers)
                    
                    resp_json = resp.json()
                    
                    print(resp_json["s"][0]["src"])
                    
                    video_url = r"https:"+resp_json["s"][0]["src"]
                    
                    if "m3u8" in video_url:
                        response = s.get(r"https:"+resp_json["s"][0]["src"])
                        with open("out.m3u8", "wb") as f:
                            f.write(response.content)
                    
                    cj.save(ignore_discard=True, ignore_expires=True)
                    
                    print('mpv --demuxer-lavf-o=headers="Cookie: {}" --cookies --cookies-file=cookies.txt {}'.format(parseCookieFile("cookies.txt"), video_url))
                    print(parseCookieFile("cookies.txt"))
                    os.system('mpv --demuxer-lavf-o=headers="Cookie: {}" --cookies --cookies-file=cookies.txt {}'.format(parseCookieFile("cookies.txt"), video_url))
                    current_state = ""
                    continue
                    
            elif "://" in current_state and "category/" in current_state.split("://", 1)[1].replace("anime1.me/",""): # https://anime1.me/category/2021%e5%b9%b4%e6%98%a5%e5%ad%a3/86-%e4%b8%8d%e5%ad%98%e5%9c%a8%e7%9a%84%e6%88%b0%e5%8d%80
                
                if "page" in current_state.split("://", 1)[1].replace("anime1.me/",""): # ....../page/2
                    current_state = current_state.split("/page",1)[0]
                    #continue
                
                print("Category URL:", current_state)
                
                page_id = 1
                dict_urls = {}
                
                while True:
                    headers = gen_UA_header()
                    soup = get_soup(current_state+"/page/{}".format(page_id), headers)
                    
                    articles = soup.select("article")
                    
                    for article in articles:
                        title = article.select(".entry-title")[0].get_text()
                        
                        title_num = title.split("[")[-1].split("]")[0]
                        
                        title_num = title_num.lstrip('0')
                        
                        if not title_num:
                            title_num = "0"
                        
                        id_url = article["id"]
                        
                        id_url_num = id_url.split("-")[-1]
                        
                        dict_urls[title_num] = (id_url_num, title)
                        
                    if not soup.select(".nav-previous"): # cannot go back
                        break
                    page_id += 1
                    
                    
                # dict_urls = dict(sorted(dict_urls.items(), key=lambda item: float(item[0]))) # https://stackoverflow.com/a/613218
                
                dict_urls = dict(reversed(dict_urls.items()))
                
                
                dict_urls_numberonly = {k:v for k,v in dict_urls.items() if k.replace('.','',1).isdigit()} #https://stackoverflow.com/a/38329481
                
                dict_urls_not_numberonly = {k:v for k,v in dict_urls.items() if not k.replace('.','',1).isdigit()}
                '''import pprint
                pprint.pprint(dict_urls_numberonly)
                pprint.pprint(dict_urls_not_numberonly)
                input()'''
                #assert len(dict_urls) == len(dict_urls_numberonly) + len(dict_urls_not_numberonly)
                
                dict_urls_contains_numbers = {k:v for k,v in dict_urls_not_numberonly.items() if any(char.isdigit() for char in k)} # https://stackoverflow.com/a/6649238
                
                dict_urls_not_contains_numbers = {k:v for k,v in dict_urls_not_numberonly.items() if not any(char.isdigit() for char in k)} # https://stackoverflow.com/a/6649238
                
                #assert len(dict_urls_not_numberonly) == len(dict_urls_contains_numbers) + len(dict_urls_not_contains_numbers)
                
                #dict_urls_numberonly
                #dict_urls_contains_numbers
                #dict_urls_not_contains_numbers
                
                #assert len(dict_urls) == len(dict_urls_numberonly) + len(dict_urls_contains_numbers) + len(dict_urls_not_contains_numbers)
                
                
                dict_urls_numberonly = dict(sorted(dict_urls_numberonly.items(), key=lambda item: float(item[0])))
                dict_urls_contains_numbers = dict(sorted(dict_urls_contains_numbers.items(), key=lambda item: float(rx.findall(item[0])[0])))
                
                '''import pprint
                pprint.pprint(dict_urls_numberonly)
                pprint.pprint(dict_urls_contains_numbers)
                pprint.pprint(dict_urls_not_contains_numbers)
                input()'''
                
                dict_urls = dict_urls_numberonly
                dict_urls.update(dict_urls_contains_numbers)
                dict_urls.update(dict_urls_not_contains_numbers)
                
                
                
                current_state = make_selection(dict_urls)
                continue
                

            elif "://" in current_state and current_state.split("://", 1)[1].replace(r"anime1.me/?cat=","").isdigit(): # https://anime1.me/?cat=1135
                r = requests.get(current_state)
                if not current_state == r.url:
                    current_state = r.url
                    continue
                else:
                    print("Not found")
                    current_state = ""
                    break
            elif current_state == "q":
                scrape_url = "https://sta.anicdn.com/homelist.min.js"
                content = requests.get(scrape_url)
                content.encoding="utf-8"
                content = content.text
                content="https:{}".format(content.split('''"url":"''')[-1].split('"')[0])
                r = requests.get(content)
                all_list = r.json()
                query_str = input("Enter to search: ")
                new_all_list = [x for x in all_list if query_str.lower() in x[1].lower()]
                if not new_all_list:
                    print("Not found")
                    current_state = ""
                    break
                print_nicely(new_all_list)
                current_state = ""
                print("Select category by c[] command, such as c{}".format(new_all_list[0][0]))
                break
                '''import pprint
                pprint.pprint(new_all_list)'''
            elif current_state == "s" and dict_urls:
                current_state = make_selection(dict_urls)
                continue
            elif current_state == ">" and dict_urls:
                last_selection += 1
                current_state = "https://anime1.me/{}".format(dict_urls[list(dict_urls.keys())[last_selection]][0])
                print(current_state)
                continue
            elif current_state == "<" and dict_urls:
                last_selection -= 1
                current_state = "https://anime1.me/{}".format(dict_urls[list(dict_urls.keys())[last_selection]][0])
                print(current_state)
                continue
            elif current_state.startswith("c") and current_state[1:].isdigit():
                current_state = r"https://anime1.me/?cat=" + current_state[1:]
                
                continue
            elif current_state.startswith("v") and current_state[1:].isdigit():
                current_state = r"https://anime1.me/" + current_state[1:]
                continue
            else:
                break
    except Exception as e:
        exception_text = traceback.format_exc()
        print(exception_text)
        print(e)
        continue
        
