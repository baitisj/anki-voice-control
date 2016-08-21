# -*- coding: utf-8 -*-
# Copyright: Jeffrey Baitis <jeff@baitis.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.hooks import addHook
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction
from aqt.qt import *
# import the main window object (mw) from ankiqt
from aqt import mw
from aqt.utils import showText

import os
import threading

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

# This is REQUIRED for getting the pygst threading model going.
GObject.threads_init()
Gst.init(None)

""" Anki card reviewer voice control, using PocketSphynx"""
class VoiceControl(object):

  def __init__(self,mw):
    self.mw = mw
    self.initSphynx()
    self.init_gst()
    self.diag = None
    self.label = None
    self.anki_state = 'N'

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
      'AGAIN':        lambda:self.mapWordToCardButton('AGAIN'),
      'ANSWER':       self.showAnswer,
      'BURY CARD':    mw.reviewer.onBuryCard,
      'BURY NOTE':    mw.reviewer.onBuryNote,
      'EASY':         lambda:self.mapWordToCardButton('EASY'),
      'GOOD':         lambda:self.mapWordToCardButton('GOOD'),
      'HARD':         lambda:self.mapWordToCardButton('HARD'),
      'MARK':         mw.reviewer.onMark,
      'PAUSE':        self.pause,
      'RESUME':       self.resume,
      'STAR':         mw.reviewer.onMark,
      'SUSPEND CARD': mw.reviewer.onSuspendCard,
      'SUSPEND NOTE': mw.reviewer.onSuspend,
      'SYNCHRONIZE':  mw.onSync,
      'UNDO':         mw.onUndo
    }

  def showAnswer(self):
    if self.anki_state == 'Q': mw.reviewer._showAnswerHack()

  def mapWordToCardButton(self, command):
    """ Sends the correct answerCard action based on the number of buttons """
    """ displayed on the answer card. """
    cnt = mw.col.sched.answerButtons(mw.reviewer.card)
    c = lambda x:mw.reviewer._answerCard(x)
    if self.anki_state != 'A': return
    if command == "AGAIN": c(1)
    elif cnt == 2:
      if command == "GOOD": c(2)
    elif cnt == 3:
      if command == "GOOD": c(2)
      if command == "EASY": c(3)
    elif cnt == 4:
      if command == "HARD": c(2)
      if command == "GOOD": c(3)
      if command == "EASY": c(4)

  def addMenuItem(self):
    """ Adds hook to the the appropriate menu """
    QAction("Start speech control", self)
    self.initSphynx = initSphynx

  def startListen(self):
    """ Starts the speech pipeline """
    if self.anki_state=='N':
      self.showStatus('Starting speech recognition.')
    self.pipeline.set_state(Gst.State.PLAYING)

  def stopListen(self):
    """ Completely disables the speech pipeline """
    self.showStatus('Stopping speech recognition.')
    self.pipeline.set_state(Gst.State.PAUSED)

  def pause(self):
    self.responsive = False
    self.diag, box = showText('Pausing speech recognition, say "RESUME" to continue', run=False)
    def onReject(self):
      self.diag = None
    self.diag.connect(box, SIGNAL("rejected()"), lambda:onReject(self))
    self.diag.show()

  def resume(self):
    self.pipeline.set_state(Gst.State.PLAYING)
    if self.diag:
      self.diag.reject()
      self.diag = None
    self.responsive = True

  def init_gst(self):
      """Initialize the speech components"""
      self.pipeline = Gst.parse_launch(
        'autoaudiosrc ! audioconvert ! audioresample ! ' +
        'pocketsphinx name=asr ! fakesink')

      asr = self.pipeline.get_by_name('asr')
      asr.set_property('lm', self.file_language_model)
      asr.set_property('dict', self.file_dictionary)
      asr.set_property('configured', True)

      bus = self.pipeline.get_bus()
      bus.add_signal_watch()
      bus.connect('message::element', self.element_message)
      self.pipeline.set_state(Gst.State.PAUSED)
      self.responsive = True

  def element_message(self, bus, msg):
      """Receive element messages from the bus."""
      msgtype = msg.get_structure().get_name()
      if msgtype != 'pocketsphinx':
          return
      if msg.get_structure().get_value('final'):
        self.final_result(msg.get_structure().get_value('hypothesis'),
                          msg.get_structure().get_value('confidence'))

  def final_result(self, hyp, confidence):
      """Decide what to do with the heard words"""
      words = hyp.split()
      actions = []
      i = 0
      # make list of supported user's commands
      while i < len(words):
        # first of all check combination of two words
        if i < len(words) - 1:
          action = words[i] + " " + words[i + 1]
          if self.is_valid_action(action):
            actions.append(action)
            i += 2
            continue
        # if combination is not correct then check individual word
        if self.is_valid_action(words[i]):
          actions.append(words[i])
        i += 1
      # execute commands
      for action in actions:
        self.run_action(action)

  def is_valid_action(self, string):
    """Check what plugin support command"""
    return string in self.actions

  def run_action(self, string):
      """Execute command if it's valid and plugin in appropriate state"""
      self.showStatus('heard "%s"' % string, 750)
      if self.responsive or not self.responsive and string == "RESUME":
        self.actions[string]()

  def questionState(self):
    self.startListen()
    self.anki_state='Q'

  def answerState(self):
    self.anki_state='A'

  def showStatus(self, msg, period=1000):
    if self.label:
      self.label.closeLabel()
    aw = mw.app.activeWindow()
    self.label = VoiceStatus(msg, aw, period)
    self.label.move(aw.mapToGlobal(QPoint(0, -100 + aw.height())))
    self.label.show()

class VoiceStatus(QLabel):

  def __init__(self, msg, window, period):

    self.timer = mw.progress.timer(period, self.closeLabel, False)
    # method closeLabel can be invoked from multiple places
    self.closeLock = threading.Lock()

    QLabel.__init__(self, msg, window)
    self.setFrameStyle(QFrame.Panel)
    self.setLineWidth(2)
    self.setWindowFlags(Qt.ToolTip)
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#feffc4"))
    p.setColor(QPalette.WindowText, QColor("#000000"))
    self.setPalette(p)

  def mousePressEvent(self, evt):
    evt.accept()
    self.hide()

  def closeLabel(self):
    with self.closeLock:
      if not self.timer:
        # label already closed
        return
      self.timer.stop()
      self.timer = None
      self.hide()
      try:
        self.deleteLater()
      except:
        # Already deleted
        pass

# GLOBAL namespace
# HERE is where we start.
mw.voiceControl = VoiceControl(mw)
addHook('showQuestion', mw.voiceControl.questionState)
addHook('showAnswer',   mw.voiceControl.answerState)
