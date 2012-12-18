import gc
import os
import sys
import logging
import datetime
import dateutil.parser as parser
import ConfigParser
import MySQLdb

from twitter import *

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger('user')

logger.info( "Reading configurations..")
config = ConfigParser.ConfigParser()
file = config.read('config/twitter_config.cfg')

DB_HOST             = config.get('DB_Config', 'db_host')
DB_NAME             = config.get('DB_Config', 'db_name')
DB_USER             = config.get('DB_Config', 'db_user')
DB_PASS             = config.get('DB_Config', 'db_password')
CREDS_FILE          = config.get('Twitter_Config', 'twitter_creds')
TWITTER_USERNAME    = config.get('Twitter_Config', 'username')
CONSUMER_KEY        = config.get('Twitter_Config', 'consumer_key')
CONSUMER_SECRET     = config.get('Twitter_Config', 'consumer_secret')
TWITTER_CREDS       = os.path.expanduser(CREDS_FILE)

oauth_token, oauth_secret = read_token_file(TWITTER_CREDS)
oauth = OAuth( oauth_token, oauth_secret,CONSUMER_KEY,  CONSUMER_SECRET)


logger.info( "Trying to connect to" + DB_HOST +"...")
conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASS, db=DB_NAME)
cursor = conn.cursor()
logger.info( "...done!")

tweet_fields_list = ['id', 'user_id', 'in_reply_to_status_id', 'in_reply_to_user_id', 'favorited', 'retweeted', 'retweet_count', 'lang', 'created_at']
tweet_fields = ', '.join(tweet_fields_list)
tweet_placeholders = ', '.join(['%s']*len(tweet_fields_list))
insert_tweets_sql = 'INSERT INTO tweet (' + tweet_fields + ') VALUES (' +  tweet_placeholders  + ')'

tweet_text_fields_list = ['tweet_id', 'user_id', 'text', 'geo_lat', 'geo_long', 'place_full_name', 'place_id']
tweet_text_fields = ', '.join(tweet_text_fields_list)
tweet_text_placeholders = ', '.join(['%s']*len(tweet_text_fields_list))
insert_tweets_texts_sql = 'INSERT INTO tweet_text (' + tweet_text_fields + ') VALUES (' + tweet_text_placeholders + ')'

tweet_url_fields_list = ['tweet_id', 'progressive', 'url']
tweet_url_fields = ', '.join(tweet_url_fields_list)
tweet_url_placeholders = ', '.join(['%s']*len(tweet_url_fields_list))
insert_tweets_urls_sql = 'INSERT INTO tweet_url (' + tweet_url_fields + ') VALUES ( ' + tweet_url_placeholders + ') ON DUPLICATE KEY UPDATE tweet_id=VALUES(tweet_id)'

tweet_hashtag_fields_list = ['tweet_id', 'user_id', 'hashtag_id']
tweet_hashtag_fields = ', '.join(tweet_hashtag_fields_list)
tweet_hashtag_placeholders = ', '.join(['%s']*len(tweet_hashtag_fields_list))
insert_tweets_hashtags_sql = 'INSERT INTO tweet_hashtag (' + tweet_hashtag_fields + ') VALUES (' + tweet_hashtag_placeholders + ')'

insert_hashtags_sql = 'INSERT INTO tweet_hashtag (hashtag) VALUES (%s) ON DUPLICATE KEY UPDATE hashtag=VALUES(hashtag)'

user_fields_list = ['id', 'screen_name', 'name', 'verified', 'protected', 'followers_count', 'friends_count', 'statuses_count', 'favourites_count', 'location', 'utc_offset', 'time_zone', 'geo_enabled', 'lang', 'description', 'url', 'created_at']
user_fields = ', '.join(user_fields_list)
user_placeholders = ', '.join(['%s']*len(user_fields_list))

insert_users_sql = 'INSERT INTO tweet (' + user_fields + ') VALUES (' + user_placeholders + ')'





logger.info( "Connecting to the stream...")
twitter_stream = TwitterStream(auth=oauth)
iterator = twitter_stream.statuses.sample()

# Use the stream
timer = datetime.datetime.now()

tweets              = []
tweet_record        = []
tweet_texts         = []
tweet_text_record   = []
urls                = []
hashtags            = []
inserted_hashtags   = {}
users               = {}


count = 0
for tweet in iterator:
    if 'text' in tweet  and  tweet['text'] != None and tweet['lang'] == 'en' :
        
        tweet_record = []
        tweet_text_record   = []
        
        for field in tweet_fields_list :
            if field == 'user_id' :
                tweet_record.append(tweet['user']['id'])
            elif field == 'created_at' :
                datetime = parser.parse(tweet['created_at'])
                datetime = datetime.isoformat(' ')[:-6]
                tweet_record.append(datetime)
            elif field in tweet :   
                if tweet[field] == None :
                    value = 0
                else :
                    value = tweet[field]                             
                tweet_record.append(value)
        tweets.append(tweet_record)
        
        for field in tweet_text_fields_list :
            if field == 'tweet_id' :
                tweet_text_record.append(tweet['id'])                            
            elif field == 'user_id' :
                tweet_text_record.append(tweet['user']['id'])
            elif field == 'text' :
                value = tweet['text'].trim()
                tweet_text_record.append(value)
            elif field == 'geo_lat' :
                if tweet['geo'] != None:
                    tweet_text_record.append(tweet['geo']['coordinates'][0])
                else :
                    tweet_text_record.append(0)
            elif field == 'geo_long' :
                if tweet['geo'] != None :
                    tweet_text_record.append(tweet['geo']['coordinates'][1])
                else :
                    tweet_text_record.append(0)            
            elif field == 'place_full_name' :
                if tweet['place'] != None :
                    tweet_text_record.append(tweet['place']['full_name'])
                else :
                    tweet_text_record.append('')                
            elif field == 'place_id' :
                # http://api.twitter.com/1/geo/id/6b9ed4869788d40e.json
                if tweet['place'] != None :
                    tweet_text_record.append(tweet['place']['id'])
                else :
                    tweet_text_record.append('')                
            elif field in tweet :
                if tweet[field] == None :
                    value = 0
                else :
                    value = tweet[field]                             
                tweet_text_record.append(value)            
        tweet_texts.append(tweet_text_record)
        
        
        user_record = []
        user_data = tweet['user']
        for field in user_fields_list :
            if field == 'created_at' :
                datetime = parser.parse(user_data['created_at'])
                datetime = datetime.isoformat(' ')[:-6]
                user_record.append(datetime)            
            elif field in user_data :
                if user_data[field] == None :
                    value = ''
                else :
                    value = user_data[field]                             
                user_record.append(value)            
        users[user_data['id']]=user_record


        count = count + 1        
        if len(tweet['entities']) >0 :
            if len(tweet['entities']['urls']) > 0  :
                url_count = 0
                for url in tweet['entities']['urls'] :
                    url_count = url_count + 1
                    urls.append(tweet['id'], url_count, url['expanded_url'])
                    
                    
            if len(tweet['entities']['hashtags']) > 0  :                
                for hash in tweet['entities']['hashtags'] :
                    hash_id = 0
                    if not hash['text'] in inserted_hashtags :
                        cursor.execute(insert_hashtags_sql, [hash['text']])
                        inserted_hashtags[hash['text']] = hash_id =  cursor.lastrowid                        
                    else :
                        hash_id = inserted_hashtags[hash['text']]
                    hashtags.append([tweet['id'], tweet['user']['id'], hash_id ])
                            
        if count > 5 :
            try:
                cursor.executemany(insert_tweets_sql, tweets)
                cursor.executemany(insert_tweets_texts_sql, tweet_texts)
                cursor.executemany(insert_tweets_urls_sql, urls)
                cursor.executemany(insert_tweets_hashtags_sql, hashtags)
                cursor.executemany(insert_users_sql, users.values())
            except Exception as e:
                print  cursor._last_executed
                print "An error occurred while exectuing the query:\n"
                print e            
            break
    #else :
    #    print "What's this!?"
    #    print tweet
    #    break
             
print "-------"
print count



#Todo Save to DB
#cursor.lastrowid