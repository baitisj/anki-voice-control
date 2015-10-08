# anki-voice-control #
Module that uses [PocketSphynx](http://sourceforge.net/projects/cmusphinx/) to
allow simple voice commands when using Anki.

Control your review session using only your voice! This is great if you need
hands-free operation.

## Requirements ##

* gstreamer 
* pocketsphinx
... and python bindings for both.
In order to install the required software under Ubuntu:

`apt-get install python-pocketsphynx`
`apt-get install gstreamer0.10-pocketsphinx`

## Future Work ##
Currently, this module only works under Linux. Contributions
that allow for use in other platforms are welcomed.

## Vocabulary ##
Here's a list of the voice commands that are currently implemented.

Command | Description
----------------------
answer | shows the answer side of the card
again, easy, good, hard | corresponding button on the answer side of the card
mark, star | Toggles the marked status of the card
undo | Same as the undo key
pause, resume | Say "pause", and the voice recognition will be disabled until
you say "resume"
synchronize | synchronizes your collection.
bury card, bury note, suspend card, suspend note" | management of cards

## Thanks ##
Special thanks to  worden.e...@gmail.com, author of
[sphinxkeys](https://code.google.com/p/sphinxkeys/), on which this project is
based.

