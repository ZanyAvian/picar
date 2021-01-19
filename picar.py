#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 22 10:59:38 2020

@author: samuel
"""

import pyglet
from time import sleep
#import time
from os import listdir
from os.path import isfile, isdir, join, splitext, exists, dirname, basename,\
                    abspath
import cv2
from gpiozero import DigitalInputDevice as gpioIn,\
                     DigitalOutputDevice as gpioOut
import pickle
import rpi_backlight
#from pyglet.window import key
#import numpy
#import sys
import subprocess

###############################################################################
#
# Initialization
#
###############################################################################

pyglet.options['audio'] = ('openal', 'pulse', 'directsound', 'silent')
backlight = rpi_backlight.Backlight()
state = 'musicControl'

### Folders and Files ###
base = '/home/pi/picar'
pic = join(base, 'pic/ProgrammerArtLol')
data = join(base, 'data.pkl')
video = join(base, 'video')
music = join(base, 'music')
musicFormats = ('.mp3','.wav','.ogg')
pictureFormats = ('.jpg', '.png', '.bmp')
camPort = "/dev/video0"

### GPIO ###
dispWidth = 800
dispHeight = 480
gpioRearPin = 26
gpioShutdownPin = 19
gpioPowerPin = 13
gpioAmpPin = 6
gpioRear = gpioIn(pin=gpioRearPin)
gpioShutdown = gpioIn(pin=gpioShutdownPin)
gpioPower = gpioOut(pin=gpioPowerPin, initial_value=True)
gpioAmp = gpioOut(pin=gpioAmpPin)

### Display ###
mainDisp = pyglet.window.Window(width=dispWidth, height=dispHeight,
                                fullscreen=True)
mainDisp.set_mouse_visible(visible=False)

fast = pyglet.image.load(join(pic, 'fast.png'))
menu = pyglet.image.load(join(pic, 'menu.png'))
right = pyglet.image.load(join(pic, 'next.png'))
left = pyglet.image.load(join(pic, 'previous.png'))
up = pyglet.image.load(join(pic, 'up.png'))
down = pyglet.image.load(join(pic, 'down.png'))
pause = pyglet.image.load(join(pic, 'pause.png'))
play = pyglet.image.load(join(pic, 'play.png'))
rewind = pyglet.image.load(join(pic, 'rewind.png'))
#stop = pyglet.image.load(join(pic, 'stop.png'))
#volume = pyglet.image.load(join(pic, 'volume.png'))
close = pyglet.image.load(join(pic, 'close.png'))

musicControl = pyglet.graphics.Batch()
musicSelect = pyglet.graphics.Batch()
primary = pyglet.graphics.OrderedGroup(0)
overlay = pyglet.graphics.OrderedGroup(1)

buttonMenu = pyglet.sprite.Sprite(menu, x=0, y=160*2,
                                  batch=musicControl, group=primary)
buttonRewind = pyglet.sprite.Sprite(rewind, x=160, y=0,
                                    batch=musicControl, group=primary)
buttonPlay = pyglet.sprite.Sprite(play, x=160*2, y=0, group=primary)
buttonPause = pyglet.sprite.Sprite(pause, x=160*2, y=0, group=primary)
buttonFastForward = pyglet.sprite.Sprite(fast, x=160*3, y=0,
                                         batch=musicControl, group=primary)
#iconVolume = pyglet.sprite.Sprite(volume, x=160*4, y=0, batch=musicControl, group=primary)
volumeBar = pyglet.shapes.Rectangle(160*4+75, 10, 10, 300,
                                    batch=musicControl, group=primary)
brightnessBar = pyglet.shapes.Rectangle(75, 10, 10, 300,
                                        batch=musicControl, group=primary)
buttonPrevious = pyglet.sprite.Sprite(left, x=160, y=160,
                                      batch=musicControl, group=primary)
buttonNext = pyglet.sprite.Sprite(right, x=160*3, y=160,
                                  batch=musicControl, group=primary)
buttonClose = pyglet.sprite.Sprite(close, x=160*4, y=160*2,
                                   batch=musicControl, group=primary)

buttonListDown = pyglet.sprite.Sprite(down, x=160*4, y=0,
                                      batch=musicSelect, group=primary)
buttonListUp = pyglet.sprite.Sprite(up, x=160*4, y=160,
                                    batch=musicSelect, group=primary)
buttonListClose = pyglet.sprite.Sprite(close, x=160*4, y=320,
                                       batch=musicSelect, group=primary)

### Music ###
def getSongsInFolder(folder):
    songList = []
    for f in listdir(folder):
        if splitext(f)[1] in musicFormats:
            songList.append(f)
    return songList

def readySong(play=True):
    global musicPlayer, songName, maxTime, songsInFolder, albumName
    global currentSongIndex, song
    musicPlayer.delete()
    musicPlayer = pyglet.media.Player()
    musicPlayer.pause()
    musicPlayer.volume = volume
    if musicFile:
        currentFolder = dirname(musicFile)
        songsInFolder = getSongsInFolder(currentFolder)
        albumName = basename(currentFolder)
        songName = splitext(basename(musicFile))[0]
        song = pyglet.media.load(musicFile)
        maxTime = song.duration
        currentSongIndex = songsInFolder.index(basename(musicFile))
        musicPlayer.queue(song)
        if play:
            gpioAmp.off()
            musicPlayer.play()
        temp = currentSongIndex + 1
        while temp < len(songsInFolder):
            t1 = pyglet.media.load(join(currentFolder, songsInFolder[temp]))
            musicPlayer.queue(t1)
            temp += 1
    else:
        currentFolder = music
        songsInFolder = getSongsInFolder(currentFolder)
        albumName = basename(currentFolder)
        songName = ''
        currentSongIndex = 0

def readyLabels(song=True):
    global albumLabel, songLabel, currentTimeLabel, maxTimeLabel
    global currentSongNumberLabel, maxSongNumberLabel
    if song:
        albumLabel.text = albumName
        songLabel.text = songName
        currentTimeLabel.text = '0'
        maxTimeLabel.text = str(maxTime)
        currentSongNumberLabel.text = str(currentSongIndex) + 1
        maxSongNumberLabel.text = str(len(songsInFolder))
    else:
        albumLabel.text = ''
        songLabel.text = ''
        currentTimeLabel.text = ''
        maxTimeLabel.text = ''
        currentSongNumberLabel.text = ''
        maxSongNumberLabel.text = ''

class musicInfo:
#    def __init__(self):
#        self.musicFile = None
#        self.musicTime = None
    def __init__(self, musicFile, musicTime, volume):
        self.musicFile = musicFile
        self.musicTime = musicTime
        self.volume = volume

topLevelFolders = [f for f in listdir(music) if not isfile(join(music, f))]
currentFolder = music
songsInFolder = []

if exists(data):
    with open(data, 'rb') as dataFile:
        info = pickle.load(data)
        try:
            musicFile = info.musicFile
            musicTime = info.musicTime
            volume = info.volume
            currentFolder = dirname(musicFile)
        except:
            currentFolder = music
            musicFile = None
            musicTime = 0
            volume = 0
else:
    musicFile = None
    musicTime = 0
    volume = 0

menuFolder = currentFolder

musicPlayer = pyglet.media.Player()
if musicFile:
    readySong(False)
    musicPlayer.seek(musicTime)
else:
    songName=''
    maxTime = 0
    songsInFolder = getSongsInFolder(currentFolder)
    albumName = basename(currentFolder)
    currentSongIndex = 0

menuAlbum = albumName
songsInMenuFolder = songsInFolder

musicPlayer.pause()
musicPlayer.volume = volume

albumLabel = pyglet.text.Label(text=albumName, font_name='Roboto Regular',
                               font_size=12, x=160, y=160*2 + 20,
                               width=160*3, align='center', batch=musicControl)
songLabel = pyglet.text.Label(text=songName, font_name='Roboto Regular',
                              font_size=12, x=160, y=160*2,
                              width=160*3, align='center', batch=musicControl)
currentTimeLabel = pyglet.text.Label(text=str(musicTime),
                                     font_name='Roboto Regular',
                                     font_size=12, x=320+10, y=160+10,
                                     width=60, align='right',
                                     batch=musicControl)
timeSlashLabel = pyglet.text.Label(text='/', font_name='Roboto Regular',
                                   font_size=12, x=320+70, y=160+10,
                                   width=20, align='center',
                                   batch=musicControl)
maxTimeLabel = pyglet.text.Label(text=str(maxTime), font_name='Roboto Regular',
                                 font_size=12, x=320+90, y=160+10,
                                 width=60, align='left', batch=musicControl)
currentSongNumberLabel = pyglet.text.Label(text=str(currentSongIndex + 1),
                                           font_name='Roboto Regular',
                                           font_size=12, x=320+10, y=160+50,
                                           width=60, align='right',
                                           batch=musicControl)
songSlashLabel = pyglet.text.Label(text='/', font_name='Roboto Regular',
                                   font_size=12, x=320+70, y=160+50,
                                   width=20, align='center',
                                   batch=musicControl)
maxSongNumberLabel = pyglet.text.Label(text=str(len(songsInFolder)),
                                       font_name='Roboto Regular',
                                       font_size=12, x=320+90, y=160+50,
                                       width=60, align='left',
                                       batch=musicControl)
brightnessKnob = pyglet.shapes.Circle(75, 10 + 3 * backlight.brightness, 10,
                                      batch=musicControl, group=overlay)
volumeKnob = pyglet.shapes.Circle(160*3+75, 10 + 300 * volume, 10,
                                  batch=musicControl, group=overlay)

songSelectLabelCurrent = pyglet.text.Label(font_name='Roboto Regular',
                                           font_size=30, x=10, y=480/2 - 15,
                                           width=160*4, batch=musicSelect)
songSelectLabelUp1 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 + 50,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelUp2 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 + 100,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelUp3 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 + 150,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelDown1 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 - 50,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelDown2 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 - 100,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelDown3 = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=20, x=10, y=480/2 - 15 - 150,
                              width=160*4, color=(200,200,200,255),
                              batch=musicSelect)
songSelectLabelTop = pyglet.text.Label(font_name='Roboto Regular',
                              font_size=15, x=10, y=480/2 + 200,
                              width=160*4, batch=musicSelect)

### Events ###
pImg = None
camera = None
slider = None

@mainDisp.event
def on_draw():
    global state, stateStore
    mainDisp.clear()
    if state == 'musicControl':
        musicControl.draw()
        if musicPlayer.playing:
            buttonPause.draw()
        else:
            buttonPlay.draw()
    elif state == 'musicSelect':
        musicSelect.draw()
    elif state == 'rearview':
        try:
            pImg.blit()
        except:
            pass
    else:
        stateStore = 'musicControl'
        state = 'musicControl'
        print('state = musicControl because something went wrong!')

def checkButton(x, y):
    if state == 'musicControl':
        if x < 160:
            if y < 160*2:
                return 'brightness'
            else:
                return 'menu'
        elif x < 160*2:
            if y < 160:
                return 'rewind'
            elif y < 160*2:
                return 'previous'
        elif x < 160*3:
            if y < 160:
                return 'playpause'
        elif x < 160*4:
            if y < 160:
                return 'forward'
            elif y < 160*2:
                return 'next'
        else:
            if y < 160*2:
                return 'volume'
            else:
                return 'close'
        return None
    elif state == 'musicSelect':
        if x < 160*4:
            return 'select'
        else:
            if y < 160:
                return 'down'
            elif y < 160 * 2:
                return 'up'
            else:
                return 'back'
    return None

def loadMenu(currentFolder=currentFolder, albumName=albumName):
    global state, stateStore
    stateStore = 'musicSelect'
    state = 'musicSelect'
    global songSelectLabelTop, songSelectLabelCurrent, songSelectLabelUp1
    global songSelectLabelUp2, songSelectLabelUp3, songSelectLabelDown1
    global songSelectLabelDown2, songSelectLabelDown3
    songSelectLabelTop.text = albumName
    songSelectLabelUp3.text = ''
    songSelectLabelUp2.text = ''
    songSelectLabelUp1.text = ''
    songSelectLabelCurrent = '..'
    allCurrentFolder = listdir(currentFolder)
    try:
        songSelectLabelDown1.text = allCurrentFolder[0]
    except:
        songSelectLabelDown1.text = ''
    try:
        songSelectLabelDown2.text = allCurrentFolder[1]
    except:
        songSelectLabelDown2.text = ''
    try:
        songSelectLabelDown3.text = allCurrentFolder[2]
    except:
        songSelectLabelDown3.text = ''

def loadSong(songToLoad):
    global musicFile, currentFolder, songsInFolder, albumName, songName, song
    global maxTime, currentSongIndex, albumLabel, songLabel, currentTimeLabel
    global maxTimeLabel, currentSongNumberLabel, maxSongNumberLabel
    if isinstance(songToLoad, int):
        try:
            songToLoad = join(currentFolder,
                              songsInFolder[currentSongIndex + songToLoad])
        except:
            if songToLoad < 0:
                try:
                    songToLoad = musicFile
                except:
                    return -1
            else:
                return -1
    musicFile = songToLoad
    readySong(musicPlayer.playing)
    readyLabels()

def seekSong(directionToSeek):
    musicPlayer.seek(musicPlayer.time + directionToSeek * 2)

def stopProgram(shutdown=True):
    musicPlayer.pause()
    gpioAmp.off()
    info = musicInfo(musicFile, musicPlayer.time, musicPlayer.volume)
    global data
    with open(data, 'wb') as dataFile:
        pickle.dump(info, dataFile)
    pyglet.app.exit()
    mainDisp.close()
    if shutdown:
        command = "/usr/bin/sudo /sbin/shutdown now"
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print(output)

def menuMove(directionToMove, currentFolder=currentFolder):
    global songSelectLabelTop, songSelectLabelCurrent, songSelectLabelUp1
    global songSelectLabelUp2, songSelectLabelUp3, songSelectLabelDown1
    global songSelectLabelDown2, songSelectLabelDown3
    if directionToMove > 0:
        if songSelectLabelDown1 != '':
            songSelectLabelUp3.text = songSelectLabelUp2.text
            songSelectLabelUp2.text = songSelectLabelUp1.text
            songSelectLabelUp1.text = songSelectLabelCurrent.text
            songSelectLabelCurrent.text = songSelectLabelDown1.text
            songSelectLabelDown1.text = songSelectLabelDown2.text
            songSelectLabelDown2.text = songSelectLabelDown3.text
            try:
                songSelectLabelDown3.text = listdir(currentFolder)\
                [listdir(currentFolder).index(songSelectLabelDown3.text) + 1]
            except:
                songSelectLabelDown3.text = ''
        else:
            pass
    else:
        if songSelectLabelUp1 != '':
            songSelectLabelDown3.text = songSelectLabelDown2.text
            songSelectLabelDown2.text = songSelectLabelDown1.text
            songSelectLabelDown1.text = songSelectLabelCurrent.text
            songSelectLabelCurrent.text = songSelectLabelUp1.text
            songSelectLabelUp1.text = songSelectLabelUp2.text
            songSelectLabelUp2.text = songSelectLabelUp3.text
            try:
                songSelectLabelUp3.text = listdir(currentFolder)\
                [listdir(currentFolder).index(songSelectLabelUp3.text) - 1]
            except:
                if songSelectLabelUp2.text == '' or songSelectLabelUp2 == '..':
                    songSelectLabelUp3.text = ''
                else:
                    songSelectLabelUp3.text = '..'
        else:
            pass

def loadControl():
    global state, stateStore
    global currentFolder, albumName, songsInFolder
    stateStore = 'musicControl'
    state = 'musicControl'
    try:
        currentFolder = dirname(musicFile)
        albumName = basename(currentFolder)
        songsInFolder = getSongsInFolder(currentFolder)
    except:
        pass

def select():
    global currentFolder, albumName, songsInFolder, musicFile, songName, song
    global maxTime, currentSongIndex, musicPlayer, nextSong, state, stateStore
    global menuFolder, menuAlbum, songsInMenuFolder
    selection = join(menuFolder, songSelectLabelCurrent.text)
    if isdir(selection):
        menuFolder = abspath(selection)
        menuAlbum = basename(menuFolder)
        songsInMenuFolder = getSongsInFolder(menuFolder)
        loadMenu(menuFolder, menuAlbum)
    elif splitext(selection)[1] in musicFormats:
        musicFile = selection
        readySong(True)
        readyLabels()
        stateStore = 'musicControl'
        state = 'musicControl'
    else:
        print("Cannot play file; ignoring input")

@mainDisp.event
def on_mouse_press(x, y, button, modifiers):
    global slider, state, musicPlayer, backlight, volume
    buttonPressed = checkButton(x, y)
    if buttonPressed == 'menu':
        loadMenu()
    elif buttonPressed == 'brightness':
        slider = 'brightness'
        backlight.brightness = (y - 10) / 3
        if backlight.brightness < 2:
            backlight.brightness = 2
        brightnessKnob.y = 10 + 3 * backlight.brightness
    elif buttonPressed == 'volume':
        slider = 'volume'
        musicPlayer.volume = (y - 10) / 300
        volume = musicPlayer.volume
        volumeKnob.y = y
    elif buttonPressed == 'previous':
        loadSong(-1)
    elif buttonPressed == 'next':
        loadSong(1)
    elif buttonPressed == 'forward':
        slider = 1
    elif buttonPressed == 'rewind':
        slider = -1
    elif buttonPressed == 'playpause':
        if musicPlayer.playing():
            musicPlayer.pause()
            gpioAmp.off()
        else:
            gpioAmp.on()
            sleep(0.2)
            musicPlayer.play()
    elif buttonPressed == 'close':
        stopProgram(False)
    elif buttonPressed == 'up':
        menuMove(-1)
    elif buttonPressed == 'down':
        menuMove(1)
    elif buttonPressed == 'back':
        loadControl()
    elif buttonPressed == 'select':
        select()
    else:
        pass

@mainDisp.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    global backlight, slider
    if slider == 'brightness':
        backlight.brightness = (y - 10) / 3
        brightnessKnob.y = 10 + 3 * backlight.brightness
    elif slider == 'volume':
        musicPlayer.volume = (y - 10) / 300
        volumeKnob.y = y

@mainDisp.event
def on_mouse_release(x, y, button, modifiers):
    global slider
    slider = None

@musicPlayer.event
def on_eos():
    #end of current song
    pass

@musicPlayer.event
def on_player_eos():
    global musicFile
    gpioAmp.off()
    #playlist empty
    musicFile = None
    readySong(False)
    readyLabels(False)

@musicPlayer.event
def on_player_next_source():
    global musicFile
    #a new source has started playback
    musicFile = join(currentFolder, songsInFolder[currentSongIndex + 1])
    readySong()
    readyLabels()

def startCamera():
    global playRemember, camera, stateStore, state
    playRemember = musicPlayer.playing
    musicPlayer.pause()
    camera = cv2.VideoCapture(camPort)
    pyglet.clock.schedule(camUpdates)
    stateStore = state
    state = 'rearview'

def endCamera():
    global state, stateStore
    pyglet.clock.unschedule(camUpdates)
    if playRemember:
        musicPlayer.play()
    camera.release()
    state = stateStore

def shut():
    stopProgram()

def periodicUpdates(dt):
    global musicPlayer
    if isinstance(slider, int):
        seekSong(slider)
    currentTimeLabel.text = musicPlayer.time

pyglet.clock.schedule_interval(periodicUpdates, 0.5)

def camUpdates(dt):
    global pImg
    retval,img = camera.read()
    sy,sx,number_of_channels = img.shape
    number_of_bytes = sy*sx*number_of_channels
    img = img.ravel()
    image_texture = (pyglet.gl.GLubyte * number_of_bytes)(*img.astype('uint8'))
    #my webcam happens to produce BGR; you may need 'RGB', 'RGBA', etc. instead
    pImg = pyglet.image.ImageData(sx,sy,'BGR',image_texture,
                                  pitch=sx*number_of_channels)

### Finalization ###

gpioRear.when_activated = startCamera
gpioRear.when_deactivated = endCamera
gpioShutdown.when_deactivated = shut
pyglet.app.run()