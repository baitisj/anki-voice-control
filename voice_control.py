# -*- coding: utf-8 -*-
# Copyright: Jeffrey Baitis <jeff@baitis.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.hooks import addHook
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction
import pygst
pygst.require('0.10')
import os, gst, sys

# import the main window object (mw) from ankiqt
from aqt import mw
from aqt.utils import showInfo, tooltip
#from aqt import browser

""" Anki card reviewer voice control, using PocketSphynx"""
class VoiceControl(object):
  def __init__(self,mw):
    self.mw = mw
    self.initSphynx()

  def initSphynx(self):
    addons = mw.pm.addonFolder()
    self.file_language_model = os.path.join(addons,'3005.lm')
    self.file_dictionary     = os.path.join(addons,'3005.dic')
    self.init_actions()
    self.init_gst()
    self.responsive = True
    self.startListen()

  def init_actions(self):
    """ These map all of the Sphynx 'sentences' to actions. """
    """ In order to generate an appropriate language model, """
    """ see http://www.speech.cs.cmu.edu/tools/lmtool-new.html """
    '''
    self.actions = {
      'AGAIN':1,
      'HARD':2,
      'GOOD':3,
      'EASY':4,
      'UNDO': "undu",
      'MARK': "mark",
      'SUSPEND CARD' : "susp1",
      'SUSPEND NOTE' : "susp1",
      'BURY CARD' : "bury1",
      'BURY NOTE' : "bury2",
      'SYNCHRONIZE' : "susp1",
      'PAUSE':  "pause",
      'RESUME': "resume"
    }
    '''

    self.actions = [
      'AGAIN',
      'HARD',
      'GOOD',
      'EASY',
      'UNDO',
      'MARK',
      'SUSPEND CARD' ,
      'SUSPEND NOTE' ,
      'BURY CARD' ,
      'BURY NOTE' ,
      'SYNCHRONIZE' ,
      'PAUSE',
      'RESUME'
    ]

  def addMenuItem(self):
    """ Adds hook to the the appropriate menu """
    action = QAction("Start speech control", self)
    self.initSphynx = initSphynx
    #self.connect(action, SIGNAL("triggered()"), lambda s=self: initSphynx(self))
    #self.form.menuEdit.addAction(action)

  def startListen(self):
    """ Starts the speech pipeline """
    self.pipeline.set_state(gst.STATE_PLAYING) 
  def stopListen(self):
    """ Completely disables the speech pipeline """
    self.pipeline.set_state(gst.STATE_PAUSED)

  def init_gst(self):
      """Initialize the speech components"""
      print ">> init_gst\n"
      self.pipeline = gst.parse_launch('autoaudiosrc ! audioconvert ! audioresample '
				       + '! vader name=vad auto-threshold=true '
				       + '! pocketsphinx name=asr ! fakesink')
      #self.pipeline = gst.parse_launch('alsasrc ! audioconvert ! audioresample '
      asr = self.pipeline.get_by_name('asr')
      asr.set_property('lm', self.file_language_model)
      asr.set_property('dict', self.file_dictionary)
      asr.connect('partial_result', self.asr_partial_result)
      asr.connect('result', self.asr_result)
      asr.set_property('configured', True)
      bus = self.pipeline.get_bus()
      bus.add_signal_watch()
      bus.connect('message::application', self.application_message)
      self.pipeline.set_state(gst.STATE_PAUSED)

  def asr_partial_result(self, asr, text, uttid):
      """Forward partial result signals on the bus to the main thread."""
      print ">> asr_partial_result\n"
      struct = gst.Structure('partial_result')
      struct.set_value('hyp', text)
      struct.set_value('uttid', uttid)
      asr.post_message(gst.message_new_application(asr, struct))

  def asr_result(self, asr, text, uttid):
      """Forward result signals on the bus to the main thread."""
      print ">> asr_result\n"
      struct = gst.Structure('result')
      struct.set_value('hyp', text)
      struct.set_value('uttid', uttid)
      asr.post_message(gst.message_new_application(asr, struct))

  def application_message(self, bus, msg):
      """Receive application messages from the bus."""
      print ">> application_message\n"
      msgtype = msg.structure.get_name()
      if msgtype == 'result':
	  self.final_result(msg.structure['hyp'], msg.structure['uttid'])

  def final_result(self, hyp, uttid):
      """Decide what to do with the heard words."""
      print ">> final_result\n"
      result = False
      print 'heard "%s"' % hyp
      #tooltip('heard "%s"' % hyp)
      word_list = hyp.split()
      word_count = len(word_list)
      word_num = 0
      while word_num <= word_count - 1:
	  if word_num <= word_count - 2:
	      try_word = word_list[word_num] + " " + word_list[word_num + 1]
	  else:
	      try_word = word_list[word_num]
	  result = self.word_run(try_word)
	  if result == True:
	      word_num = word_num + 1
	  elif try_word != word_list[word_num]:
	      try_word = word_list[word_num]
	      result = self.word_run(try_word)
	  word_num = word_num + 1
      if result == True:
	  print "successfully handled %s\n" % hyp

  def word_run(self, string):
      """Really do a command."""
      print ">> word_run\n"
      returnVal = False
      action = ''
      is_password = False
      words = string.split(' ')
      if self.responsive == False:
	  if string == "RESUME":
	      self.responsive = True
	      returnVal = True
      elif string in self.actions:
	  action = self.actions[string]
	  returnVal = True
	  #action()
	  print action + '\n'
	  returnVal = True
      return returnVal

# GLOBAL namespace
# HERE is where we start.
mw.voiceControl = VoiceControl(mw)

# Unfortunately, because of the C callback structure, 
# I haven't been able to figure out how to shove all
# of these functions into a single class. So, I'm stuck
# with patching the mw object.
#mw.initSphynx = initSphynx
#mw.init_actions = init_actions
#mw.init_gst = init_gst
#mw.word_run = word_run
#mw.startListen = startListen
#mw.stopListen = startListen
#mw.final_result = final_result
#mw.asr_partial_result = asr_partial_result
#mw.asr_result = asr_result
#mw.application_message = application_message
#
#voiceInit(mw)
#addHook('reviewer.showQuestion', mw.voice_control.startListen)
#addHook('reviewer.showQuestion', mw.voice_control.startListen)

