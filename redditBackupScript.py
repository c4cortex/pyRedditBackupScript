import praw
from praw.models import Submission
import requests
from datetime import datetime
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import redditAccessData

print('##############################')

#####################################################
class redditBackup():
    def __init__(self, backuppath = None):
        self.savepath = backuppath
        if self.savepath == None:
            root = tk.Tk()
            root.withdraw()
            self.savepath = filedialog.askdirectory(title = 'Select a backup directory')
        if self.savepath != '/':
            self.savepath += '/'
        
        Path(self.savepath).mkdir(parents=True, exist_ok=True)
        self.failureDictList = []
    ##
    def isImage(self, url):
        ''' check if the url leads to an image '''
        if '.jpg' in url or '.jpeg' in url or '.png' in url or ('.gif' in url and '.gifv' not in url):
            return True
        else:
            return False
    ##
    def isMP4Video(self, url):
        ''' check if the url leads to a mp4 video '''
        if '.gifv' in url or 'gfycat.com' in url or 'redgifs.com' in url:
            return True
        else:
            return False
    ##
    def extractMP4Link(self, url):
        ''' find the .mp4 link in the html of the url. If it finds no mp4 or too many, it will return an empty string '''
        page = requests.get(url)
        htmlstr = str(page.content)
        splittedStrs = htmlstr.split('"')
        results = []
        for s in splittedStrs:
            if '.mp4' in s and '\\' not in s and 'mobile' not in s and 'http' in s:
                if s not in results:
                    results.append(s)
        if len(results) == 0:
            pageNotFound = False
            for s in splittedStrs:
                if 'Page not found' in s:
                    pageNotFound = True
            if pageNotFound:
                self.failureDictList.append({'url': url, 'code': 'page not found, probably deleted'})
            else:
                self.failureDictList.append({'url': url, 'code': 'no mp4 found'})
            return ''
        elif len(results) > 1:
            self.failureDictList.append({'url': url, 'code': 'too many mp4 videos found'})
            return ''
        else:
            return results[0]
    ##
    def extractFileURLsFromRedditGalleries(self, url):
        ''' Special function only for reddit galleries, as they contain several images '''
        # their server replies with an error if no header is provided, so I just make one up
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0'}
        page = requests.get(url, headers = headers)
        htmlstr = str(page.content)
        splittedStrs = htmlstr.split('"')
        results = []
        for s in splittedStrs:
            # in the best case, the direct link appears in the server's response
            if ('.gif' in s or '.jpg' in s or '.png' in s or 'jpeg' in s) and 'i.redd.it' in s:
                if s not in results:
                    results.append(s)
            #sometimes only the preview images are linked; then I have to build the exact link myself
            if ('.gif' in s or '.jpg' in s or '.png' in s or 'jpeg' in s) and 'preview.redd.it' in s:
                temp = s.split('?')[0]
                temp = temp.replace('preview', 'i')
                if temp not in results:
                    results.append(temp)
        if len(results) == 0:
            self.failureDictList.append({'url': url, 'code': 'filename extraction failed: unknown format'})
        return results
    ##
    def extractFilename(self, url):
        ''' extract the filename from the url. The downloaded file is saved under this name '''
        filename = ''
        if self.isImage(url):
            filename = url.split('/')[-1]
        elif self.isMP4Video(url):
            vidlink = self.extractMP4Link(url)
            filename = vidlink.split('/')[-1]
        elif '/comments/' not in url:
            # only add to the list when its not a comment
            self.failureDictList.append({'url': url, 'code': 'filename extraction failed: unknown format'})
        return filename
    ##
    def cleanSavedList(self, urllist):
        '''
        Take the raw url list of saved items and try to clean it up a bit, e.g. removing unnecessary parts of the url and removing items that have already been downloaded
        '''
        alreadySaved = os.listdir(self.savepath)
        cleanedList = []
        for url in urllist:
            #special case for imgur when the link doesnt link the image directly
            if 'imgur' in url and '.' not in url[-7:] and '?' not in url[-7:]:
                url = url.split('//')[0] + '//i.' + url.split('//')[1] + '.jpg'
            
            #stuff after ? usually doesnt matter
            if '?' in url and 'pornhub' not in url: #pornhub has the viewkey behind the ?
                url = url.split('?')[0]
            
            #special case for reddit galleries. these might contain several images and thus filenames
            if '/gallery/' in url:
                directUrls = self.extractFileURLsFromRedditGalleries(url)
                for entry in directUrls:
                    filename = self.extractFilename(entry)
                    if filename == '':
                        pass # I ignore saved comments or failed filename extractions
                    elif filename not in alreadySaved: # dont download stuff again, that just takes forever
                        cleanedList.append(entry)
            else: #default case
                filename = self.extractFilename(url)
                if '/comments/' in url or filename == '':
                    pass # I ignore saved comments or failed filename extractions
                elif filename not in alreadySaved: # dont download stuff again, that just takes forever
                    cleanedList.append(url)
        return cleanedList
    ##
    def getSavedSubmissionList(self):
        ''' Get a list of all saved submissions. Reddit's limit is 1000 submissions; also, some of them might have already been deleted '''
        reddit = praw.Reddit(client_id=redditAccessData._clientID, client_secret=redditAccessData._clientSecret, user_agent=redditAccessData._userAgent, username = redditAccessData._username, password = redditAccessData._password)
        
        savedOnReddit = reddit.user.me().saved(limit=1000)
        urlList = []
        for submission in savedOnReddit:
            if isinstance(submission, Submission):
                urlList.append(submission.url)
        
        initialLength = len(urlList)
        urlList = self.cleanSavedList(urlList)
        finalLength = len(urlList)
        print('Total number of submissions considerd: '+str(initialLength))
        print('Total number of submissions trying to download newly: '+str(finalLength))
        self.urlList = urlList
        return urlList
    ##
    def downloadImage(self, url):
        ''' Download an image with a simple url directly leading to the image file '''
        filename = self.extractFilename(url)
        try:
            r = requests.get(url)
            with open(self.savepath + filename, 'wb') as outfile:
                outfile.write(r.content)
            return 0
        except:
            self.failureDictList.append({'url': url, 'code': 'unknown error when trying to download'})
            return -1
    ##
    def downloadMP4(self, url):
        ''' Download a mp4 video with a simple url directly leading to the video file '''
        vidlink = self.extractMP4Link(url)
        name = vidlink.split('/')[-1]
        print('downloading mp4: '+vidlink + ' ...')
        try:
            r=requests.get(vidlink)
            f=open(self.savepath+name,'wb');
            for chunk in r.iter_content(chunk_size=255): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
            print("Done")
            f.close()
            return 0
        except:
            self.failureDictList.append({'url': vidlink, 'code': 'unknown'})
            print('Failed!')
            return -1
    ##
    def downloadFiles(self, urllist):
        ''' download all files. different sources and different file types need different functions '''
        successCounter = 0
        failureCounter = 0
        ctr = 1
        for url in urllist:
            print('Downloading entry ', ctr, '/',len(urllist))
            print(url)
            ctr += 1
            if self.isImage(url):
                result = self.downloadImage(url)
                if result < 0:
                    failureCounter += 1
                else:
                    successCounter += 1
            elif self.isMP4Video(url):
                result = self.downloadMP4(url)
                if result < 0:
                    failureCounter += 1
                else:
                    successCounter += 1
                
        print('Total number of urls to download:', len(urllist),'; success:', successCounter,'; failure:', failureCounter)
    ##
    def saveFailuresToTextfile(self): 
        textfilename = 'backupfailures_' + datetime.now().strftime("%Y_%m_%d") +  '.txt'
        with open(self.savepath + textfilename, 'w') as f:
            f.write('Failed to download the media files from the following links:' + '\n')
            for entry in self.failureDictList:
                s = entry['url'] +' : ' + entry['code']
                f.write(s+'\n')
    ##
    def updateLocalBackup(self):
        ''' Update the local backup. Users actually only need to call this function '''
        urllist = self.getSavedSubmissionList()
        self.downloadFiles(urllist)
        self.saveFailuresToTextfile()
        print('Total failures: '+str(len(self.failureDictList)))
        print('A text file with all failed urls was saved in the saving folder.')
    
    

#########################
#When calling the script via the command line
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        rb = redditBackup(sys.argv[1])
        rb.updateLocalBackup()
    else:
        rb = redditBackup()
        rb.updateLocalBackup()

#Alternatively
#rb = redditBackup()
#rb.updateLocalBackup()




