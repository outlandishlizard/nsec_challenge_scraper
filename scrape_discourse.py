import requests
import sys
import json
from collections import defaultdict

import iso8601
import sqlite3


# cfg example
# {"discourse": {"username" : "your_username", "password":"your_password","url":"https://whatever.nsec"}
#}
#

def login_to_discourse(url,user,pw):
    #Does the full user login flow and returns a requests.Session with logged-in cookies.
    start_url   = url + 'session/passkey/challenge.json'
    csrf_url    = url + 'session/csrf'
    session_url = url + 'session'
    login_url   = url + 'login'

    s = requests.Session()
    s.headers.update({'Accept':'application/json'})
    start_response = s.get(start_url)
    csrf_response = s.get(csrf_url)
    token = csrf_response.json()['csrf']

    session_response = s.post(session_url,data={'login':user, 'password':pw,'second_factor_method':"1",'timezone':'America/New_York'}, headers={'X-CSRF-Token':token})
    login_response = s.post(login_url, data={'username':user,'password':pw,'redirect':url})
    return s



def list_category(session,category_name):
    cat_url = discourse_url+"/c/"+category_name+'.json'
    page = 0
    all_topics = []
    while 1:
        r = session.get(cat_url,params = {'page':str(page)})
        try:
            response = r.json()
            topics = response['topic_list']['topics']
            if topics == []:
                break
            all_topics += topics
        except Exception as e:
            print("Malformed response from discourse",r,response,page)
            break
        page +=1
    return all_topics
def list_topic(session, topic_id):
    ret = []
    r = session.get(discourse_url+"/t/"+str(topic_id)+'.json')
    try:
        response = r.json()
        posts = response['post_stream']['posts']
    except:
        print("Malformed response from discourse",r)
        return None
    for post in posts:
        p_id = post['id']
        updated = post['updated_at']
        ret.append((p_id,updated))
    return ret
def get_post(p_id):
    r = session.get(discourse_url+"/posts/"+str(p_id)+'.json')
    response = r.json()
    text = response['raw']
    dispname = response['name']
    username = response['username']
    updated = response['updated_at']
    return p_id,text,dispname,username,updated

def generate_diff(new):
    con = sqlite3.connect('./sync.db')

    con.execute("CREATE TABLE IF NOT EXISTS posts (topic_id, topic_title , post_id, post_text, displayname,username, updated);")

    in_db = con.execute("SELECT topic_id, post_id, updated from posts").fetchall()
    db_posts = defaultdict(dict)
    for t_id, post_id, updated in in_db:
        print(t_id,post_id,updated)
        db_posts[t_id][post_id] = updated
    diff = defaultdict(list)

    for topic in new:
        posts = new[topic]
        if not topic in db_posts:
            diff[topic] = posts
        else:
            for post in posts:
                post_id = post['post_id']
                post_updated = post['last_updated']
                if post_id in db_posts[topic]:
                    db_updated = db_posts[topic][post_id]
                    if  iso8601.parse_date(post_updated) > iso8601.parse_date(db_updated):
                        diff[topic].append(post)
                else:
                    diff[topic].append(post)

    for topic in diff:
        for post in diff[topic]:
            print("inserting",post['post_id'])
            con.execute("INSERT INTO posts values(?,?,?,?,?,?,?)", (topic,post['post_id'],post['topic_title'], post['post_text'], post['poster_displayname'], post['poster_username'],post['last_updated']))
    
    con.commit()
    return diff




if __name__=='__main__':
    cfg = json.loads(open(sys.argv[1]).read())
    if 'discourse' in cfg:
        discourse_url = cfg['discourse']['url']
        discourse_user = cfg['discourse']['username']
        discourse_pw = cfg['discourse']['password']
    else:
        print("No discourse config! This won't work without it!")
        sys.exit(1)

    session = login_to_discourse(discourse_url, discourse_user, discourse_pw)
    output = defaultdict(list)
    for topic in list_category(session,'staff'):
        t_id = topic['id']
        t_title = topic['title']
        for post in list_topic(session,topic['id']):
            p_id, post_text, dispname, username, updated = get_post(post[0])
            post_dict = {
                    "topic_id":str(t_id),
                    "topic_title":t_title,
                    "post_id":str(p_id),
                    "post_text": post_text,
                    "poster_displayname": dispname,
                    "poster_username": username,
                    "last_updated": updated
                    }
            output[t_id].append(post_dict)
    diff = generate_diff(output)
    out = json.dumps(diff)
    with open("./scraped_discourse.json",'w') as outfile:
        outfile.write(out)

