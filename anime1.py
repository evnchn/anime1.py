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

current_state = "" # "https://anime1.me/17173"
dict_urls = {}

while True:

    if "://" in current_state:

        if current_state.split("://", 1)[1].replace("anime1.me/","").isdigit(): # https://anime1.me/17173
        
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
                sys.exit()
                
        elif "category/" in current_state.split("://", 1)[1].replace("anime1.me/",""): # https://anime1.me/category/2021%e5%b9%b4%e6%98%a5%e5%ad%a3/86-%e4%b8%8d%e5%ad%98%e5%9c%a8%e7%9a%84%e6%88%b0%e5%8d%80
            
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
                
                
            dict_urls = dict(sorted(dict_urls.items(), key=lambda item: float(item[0]))) # https://stackoverflow.com/a/613218
            for k,v in dict_urls.items():
                print("{}: {}".format(str(k).rjust(5, " "),v[1]))
            selection = input()
            if selection in dict_urls:
                current_state = "https://anime1.me/{}".format(dict_urls[selection][0])
                continue
            else:
                print("Invalid selection")
            
    print("URL:", current_state)
    print(current_state)
    current_state = input("Please input URL: ")
