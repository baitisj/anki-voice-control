# -*- coding: utf-8 -*-
# Copyright: Jeffrey Baitis <jeff@baitis.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.hooks import addHook
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction
import pygst
pygst.require('0.10')
import os, gst, sys

# This is REQUIRED for getting the pygst threading model going.
import gobject
gobject.threads_init()

# import the main window object (mw) from ankiqt
from aqt import mw
from aqt.utils import showInfo, tooltip
#from aqt import browser

""" Anki card reviewer voice control, using PocketSphynx"""
class VoiceControl(object):
  def __init__(self,mw):
    self.mw = mw
    self.initSphynx()
    self.init_gst()

  def initSphynx(self):
    addons = mw.pm.addonFolder()
    self.file_language_model = os.path.join(addons,'voice_control','anki.lm')
    self.file_dictionary     = os.path.join(addons,'voice_control','anki.dic')
    self.init_actions()

  def init_actions(self):
    """ These map all of the Sphynx 'sentences' to actions. """
    """ In order to generate an appropriate language model, """
    """ see http://www.speech.cs.cmu.edu/tools/lmtool-new.html """

    self.actions = {
      'AGAIN':        lambda: mw.reviewer._answerCard(self.mapWordToCardButton('AGAIN')),
      'ANSWER':       mw.reviewer._showAnswerHack,
      'BURY CARD':    mw.reviewer.onBuryCard,
      'BURY NOTE':    mw.reviewer.onBuryNote,
      'EASY':         lambda:mw.reviewer._answerCard(self.mapWordToCardButton('EASY')),
      'GOOD':         lambda:mw.reviewer._answerCard(self.mapWordToCardButton('GOOD')),
      'HARD':         lambda:mw.reviewer._answerCard(self.mapWordToCardButton('HARD')),
      'MARK':         mw.reviewer.onMark,
      'PAUSE':        self.pause,
      'RESUME':       self.resume,
      'STAR':         mw.reviewer.onMark,
      'SUSPEND CARD': mw.reviewer.onSuspendCard,
      'SUSPEND NOTE': mw.reviewer.onSuspend,
      'SYNCHRONIZE':  mw.onSync,
      'UNDO':         mw.onUndo
    }

  def mapWordToCardButton(self, command):
    """ Sends the correct answerCard action based on the number of buttons """
    """ displayed on the answer card. """
    cnt = self.mw.col.sched.answerButtons(self.card)
    if command == "AGAIN" return 1
    if cnt == 2:
      if command == "GOOD" return 2
    elif cnt == 3:
      if command == "GOOD" return 2
      if command == "EASY" return 3
    elif cnt == 3:
      if command == "HARD" return 2
      if command == "GOOD" return 3
      if command == "EASY" return 4

  def addMenuItem(self):
    """ Adds hook to the the appropriate menu """
    action = QAction("Start speech control", self)
    self.initSphynx = initSphynx
    #self.connect(action, SIGNAL("triggered()"), lambda s=self: initSphynx(self))
    #self.form.menuEdit.addAction(action)

  def startListen(self):
    """ Starts the speech pipeline """
    tooltip('Starting speech recognition.')
    self.pipeline.set_state(gst.STATE_PLAYING) 
  def stopListen(self):
    """ Completely disables the speech pipeline """
    tooltip('Stopping speech recognition.')
    self.pipeline.set_state(gst.STATE_PAUSED)
  def pause(self):
    self.responsive = False
    tooltip('Pausing speech recognition, say "RESUME" to continue')
  def resume(self):
    self.pipeline.set_state(gst.STATE_PLAYING) 
    self.responsive = True
    tooltip('Resuming speech recognition.')

  def init_gst(self):
      """Initialize the speech components"""
      print ">> init_gst\n"
      self.pipeline = gst.parse_launch('autoaudiosrc ! audioconvert ! audioresample '
                             + '! vader name=vad auto-threshold=true '
                             + '! pocketsphinx name=asr ! fakesink')
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
      self.responsive = True

  def asr_partial_result(self, asr, text, uttid):
      """Forward partial result signals on the bus to the main thread."""
      struct = gst.Structure('partial_result')
      struct.set_value('hyp', text)
      struct.set_value('uttid', uttid)
      asr.post_message(gst.message_new_application(asr, struct))

  def asr_result(self, asr, text, uttid):
      """Forward result signals on the bus to the main thread."""
      struct = gst.Structure('result')
      struct.set_value('hyp', text)
      struct.set_value('uttid', uttid)
      asr.post_message(gst.message_new_application(asr, struct))

  def application_message(self, bus, msg):
      """Receive application messages from the bus."""
      msgtype = msg.structure.get_name()
      if msgtype == 'result':
        self.final_result(msg.structure['hyp'], msg.structure['uttid'])

  def final_result(self, hyp, uttid):
      """Decide what to do with the heard words."""
      result = False
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

  def word_run(self, string):
      """Really do a command."""
      returnVal = False
      action = ''
      is_password = False
      words = string.split(' ')
      if self.responsive == False:
        if string == "RESUME":
          self.resume()
          returnVal = True
      elif string in self.actions:
        tooltip('heard "%s"' % string)
        action = self.actions[string]()
        returnVal = True
        return returnVal

# GLOBAL namespace
# HERE is where we start.
mw.voiceControl = VoiceControl(mw)
addHook('reviewer.showQuestion', mw.voice_control.startListen)
